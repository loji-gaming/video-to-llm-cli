from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    frame_count: int | None
    codec: str | None


def _fraction_to_float(value: str | None) -> float:
    if not value:
        return 0.0
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return 0.0
    numerator, denominator = value.split("/", 1)
    try:
        denominator_value = float(denominator)
        if denominator_value == 0:
            return 0.0
        return float(numerator) / denominator_value
    except ValueError:
        return 0.0


def probe_video(path: Path) -> VideoMetadata:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,nb_frames,codec_name,duration",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    stream = streams[0] if streams else {}
    format_data = data.get("format") or {}

    duration = stream.get("duration") or format_data.get("duration") or 0
    frame_count_value = stream.get("nb_frames")
    try:
        frame_count = int(frame_count_value) if frame_count_value not in (None, "N/A") else None
    except ValueError:
        frame_count = None

    return VideoMetadata(
        path=str(path),
        duration=float(duration),
        width=int(stream.get("width") or 0),
        height=int(stream.get("height") or 0),
        fps=_fraction_to_float(stream.get("avg_frame_rate")),
        frame_count=frame_count,
        codec=stream.get("codec_name"),
    )


def iter_sample_timestamps(duration: float, interval: float, start_at: float = 0.0, end_at: float | None = None) -> list[float]:
    if duration <= 0:
        return []
    effective_end = min(duration, end_at) if end_at is not None else duration
    timestamps: list[float] = []
    timestamp = max(0.0, start_at)
    if timestamp == 0:
        timestamp = min(interval / 2.0, max(0.0, effective_end))
    while timestamp < effective_end:
        timestamps.append(timestamp)
        timestamp += interval
    return timestamps


def read_frame(path: Path, timestamp: float) -> np.ndarray | None:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return None
    try:
        capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp) * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            return None
        return frame
    finally:
        capture.release()


def encode_jpeg(path: Path, frame_bgr: np.ndarray, quality: int = 95) -> None:
    params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    ok = cv2.imwrite(str(path), frame_bgr, params)
    if not ok:
        raise RuntimeError(f"Failed to write frame image: {path}")

