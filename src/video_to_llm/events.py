from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .features import FrameVector
from .outputs import timestamp_label
from .video import encode_jpeg


@dataclass
class VisualEvent:
    event_id: int
    event_type: str
    start: float
    end: float
    peak: float
    peak_source_index: int
    peak_distance: float
    threshold: float
    frame_count: int
    frames_dir: str | None = None
    contact_sheet: str | None = None
    clip_file: str | None = None
    sampled_frame_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(max(0.0, self.end - self.start), 3),
            "peak": round(self.peak, 3),
            "peak_source_index": self.peak_source_index,
            "peak_distance": round(self.peak_distance, 6),
            "threshold": round(self.threshold, 6),
            "frame_count": self.frame_count,
            "frames_dir": self.frames_dir,
            "contact_sheet": self.contact_sheet,
            "clip_file": self.clip_file,
            "sampled_frame_files": self.sampled_frame_files,
            "notes": self.notes,
        }


def detect_visual_events(
    vectors: list[FrameVector],
    duration: float,
    window_seconds: float = 1.5,
    threshold_percentile: float = 95.0,
    min_distance: float = 0.2,
    merge_gap_seconds: float = 0.35,
    max_events: int = 24,
) -> list[VisualEvent]:
    distances = np.array(
        [vector.distance_from_previous or 0.0 for vector in vectors],
        dtype=np.float32,
    )
    nonzero_distances = distances[distances > 0]
    if len(vectors) < 2 or nonzero_distances.size == 0:
        return []

    percentile_threshold = float(np.percentile(nonzero_distances, threshold_percentile))
    threshold = max(percentile_threshold, min_distance)
    spike_indexes = [index for index, distance in enumerate(distances) if distance >= threshold]
    if not spike_indexes:
        return []

    spike_groups: list[list[int]] = []
    for index in spike_indexes:
        if not spike_groups:
            spike_groups.append([index])
            continue
        previous_timestamp = vectors[spike_groups[-1][-1]].timestamp
        if vectors[index].timestamp - previous_timestamp > merge_gap_seconds:
            spike_groups.append([index])
        else:
            spike_groups[-1].append(index)

    events: list[VisualEvent] = []
    half_window = max(0.0, window_seconds) / 2.0
    for spike_group in spike_groups:
        start = max(0.0, vectors[spike_group[0]].timestamp - half_window)
        end = min(duration, vectors[spike_group[-1]].timestamp + half_window)
        window_indexes = [index for index, vector in enumerate(vectors) if start <= vector.timestamp <= end]
        if not window_indexes:
            continue
        peak_index = max(window_indexes, key=lambda index: distances[index])
        peak_vector = vectors[peak_index]
        events.append(
            VisualEvent(
                event_id=0,
                event_type="visual_burst",
                start=start,
                end=end,
                peak=peak_vector.timestamp,
                peak_source_index=peak_vector.source_index,
                peak_distance=float(distances[peak_index]),
                threshold=threshold,
                frame_count=len(window_indexes),
            )
        )

    events.sort(key=lambda event: event.peak_distance, reverse=True)
    events = events[:max_events]
    events.sort(key=lambda event: event.start)
    for event_id, event in enumerate(events, start=1):
        event.event_id = event_id
    return events


def event_folder_name(event: VisualEvent) -> str:
    return (
        f"event_{event.event_id:04d}_{event.event_type}_"
        f"{timestamp_label(event.start)}_{timestamp_label(event.end)}"
    )


def sampled_vectors_for_event(vectors: list[FrameVector], event: VisualEvent, max_frames: int) -> list[FrameVector]:
    candidates = [vector for vector in vectors if event.start <= vector.timestamp <= event.end]
    if max_frames <= 0 or len(candidates) <= max_frames:
        return candidates
    indexes = np.linspace(0, len(candidates) - 1, num=max_frames)
    selected_indexes = sorted({int(round(index)) for index in indexes})
    return [candidates[index] for index in selected_indexes]


def write_event_contact_sheet(event_dir: Path, frame_files: list[Path]) -> Path | None:
    if not frame_files:
        return None

    columns = 5 if len(frame_files) <= 40 else 7
    thumb_width = 240 if columns == 5 else 180
    thumb_height = int(thumb_width * 9 / 16)
    label_height = 30 if columns == 5 else 24
    rows = math.ceil(len(frame_files) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 11 if columns == 5 else 10)
    except OSError:
        font = ImageFont.load_default()

    for index, frame_file in enumerate(frame_files):
        image = Image.open(frame_file).convert("RGB")
        image.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        sheet.paste(image, (x + (thumb_width - image.width) // 2, y))
        draw.text((x + 4, y + thumb_height + 3), frame_file.name, fill=(20, 20, 20), font=font)

    out = event_dir / "contact_sheet.jpg"
    sheet.save(out, quality=92, optimize=True)
    return out


def write_event_clip(source_video: Path, event: VisualEvent, event_dir: Path) -> Path | None:
    clip_path = event_dir / "clip.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{event.start:.3f}",
        "-to",
        f"{event.end:.3f}",
        "-i",
        str(source_video),
        "-c",
        "copy",
        str(clip_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and clip_path.exists():
        return clip_path

    # Fall back to a short re-encode when stream-copy cannot cut this container.
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{event.start:.3f}",
        "-to",
        f"{event.end:.3f}",
        "-i",
        str(source_video),
        "-an",
        "-pix_fmt",
        "yuv420p",
        str(clip_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and clip_path.exists():
        return clip_path
    return None


def write_events(
    output_dir: Path,
    source_video: Path,
    vectors: list[FrameVector],
    events: list[VisualEvent],
    max_frames_per_event: int = 120,
    write_clips: bool = True,
) -> str:
    events_dir = output_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    for event in events:
        folder = event_folder_name(event)
        event_dir = events_dir / folder
        frames_dir = event_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        event_vectors = sampled_vectors_for_event(vectors, event, max_frames_per_event)
        frame_files: list[Path] = []
        for index, vector in enumerate(event_vectors, start=1):
            frame_file = frames_dir / f"frame_{index:04d}_{timestamp_label(vector.timestamp)}.jpg"
            encode_jpeg(frame_file, vector.frame_bgr)
            frame_files.append(frame_file)

        contact_sheet = write_event_contact_sheet(event_dir, frame_files)
        clip_file = write_event_clip(source_video, event, event_dir) if write_clips else None

        event.frames_dir = str(frames_dir.relative_to(output_dir))
        event.contact_sheet = str(contact_sheet.relative_to(output_dir)) if contact_sheet else None
        event.clip_file = str(clip_file.relative_to(output_dir)) if clip_file else None
        event.sampled_frame_files = [str(path.relative_to(output_dir)) for path in frame_files]
        if len(event_vectors) < event.frame_count:
            event.notes.append(
                f"Saved {len(event_vectors)} sampled frames out of {event.frame_count} event frames; increase --event-max-frames for denser evidence."
            )

        (event_dir / "event.json").write_text(
            json.dumps(event.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    events_jsonl = output_dir / "events.jsonl"
    with events_jsonl.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
    return "events.jsonl"
