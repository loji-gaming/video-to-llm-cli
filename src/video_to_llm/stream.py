from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TextIO

from .features import FrameVector, frame_to_vector, is_useful_frame
from .outputs import prepare_output_dir, timestamp_label
from .profiles import get_profile
from .video import encode_jpeg, iter_sample_timestamps, probe_video, read_frame


@dataclass
class StreamState:
    last_timestamp: float = 0.0
    last_event_id: int = 0


def load_state(path: Path | None) -> StreamState:
    if path is None or not path.exists():
        return StreamState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return StreamState(
        last_timestamp=float(data.get("last_timestamp", 0.0)),
        last_event_id=int(data.get("last_event_id", 0)),
    )


def save_state(path: Path | None, state: StreamState) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")


def emit_event(event: dict, stdout: bool, log_handle: TextIO | None) -> None:
    line = json.dumps(event, ensure_ascii=False)
    if stdout:
        print(line, flush=True)
    if log_handle is not None:
        log_handle.write(line + "\n")
        log_handle.flush()


def stream_growing_file(
    input_path: Path,
    detail: str,
    output_dir: Path | None = None,
    stdout: bool = True,
    log_path: Path | None = None,
    state_path: Path | None = None,
    poll_seconds: float = 2.0,
    sample_interval: float | None = None,
    boundary_distance: float = 0.35,
    safe_lag_seconds: float = 1.0,
    stop_after_seconds: float | None = None,
) -> None:
    profile = get_profile(detail)
    interval = sample_interval or profile.sample_interval
    state = load_state(state_path)
    previous_vector: FrameVector | None = None

    if output_dir is not None:
        prepare_output_dir(output_dir)

    log_handle: TextIO | None = None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")

    started = time.monotonic()
    try:
        while True:
            if stop_after_seconds is not None and time.monotonic() - started >= stop_after_seconds:
                break

            try:
                metadata = probe_video(input_path)
            except Exception as exc:
                emit_event(
                    {
                        "type": "stream_waiting",
                        "reason": "probe_failed",
                        "message": str(exc),
                        "source": str(input_path),
                    },
                    stdout,
                    log_handle,
                )
                time.sleep(poll_seconds)
                continue

            available_until = max(0.0, metadata.duration - safe_lag_seconds)
            start_at = state.last_timestamp + interval
            timestamps = iter_sample_timestamps(available_until, interval, start_at=start_at)

            if not timestamps:
                time.sleep(poll_seconds)
                continue

            for timestamp in timestamps:
                frame = read_frame(input_path, timestamp)
                if frame is None:
                    continue

                vector = frame_to_vector(state.last_event_id + 1, timestamp, frame, previous_vector)
                previous_vector = vector
                if not is_useful_frame(vector):
                    state.last_timestamp = timestamp
                    save_state(state_path, state)
                    continue

                distance = vector.distance_from_previous or 0.0
                is_boundary = vector.distance_from_previous is None or distance >= boundary_distance
                keyframe_file = None
                if output_dir is not None and is_boundary:
                    filename = f"stream_{state.last_event_id + 1:06d}_{timestamp_label(timestamp)}.jpg"
                    encode_jpeg(output_dir / "frames" / filename, frame)
                    keyframe_file = f"frames/{filename}"

                state.last_event_id += 1
                state.last_timestamp = timestamp
                event = {
                    "type": "frame_observation",
                    "schema": "video-to-llm/stream-v1",
                    "event_id": state.last_event_id,
                    "source": str(input_path),
                    "timestamp": round(timestamp, 3),
                    "available_duration": round(metadata.duration, 3),
                    "distance_from_previous": round(distance, 6),
                    "is_boundary": is_boundary,
                    "brightness": round(vector.brightness, 3),
                    "contrast": round(vector.contrast, 3),
                    "sharpness": round(vector.sharpness, 3),
                    "keyframe_file": keyframe_file,
                }
                emit_event(event, stdout, log_handle)
                save_state(state_path, state)
    except KeyboardInterrupt:
        emit_event(
            {
                "type": "stream_stopped",
                "source": str(input_path),
                "last_timestamp": round(state.last_timestamp, 3),
                "last_event_id": state.last_event_id,
            },
            stdout,
            log_handle,
        )
    finally:
        if log_handle is not None:
            log_handle.close()
        save_state(state_path, state)
        if not stdout:
            print(
                f"stream stopped at {state.last_timestamp:.2f}s ({state.last_event_id} events)",
                file=sys.stderr,
            )

