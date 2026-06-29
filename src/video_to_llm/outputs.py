from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .features import FrameVector
from .selection import VideoSegment
from .video import VideoMetadata, encode_jpeg


def prepare_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "frames").mkdir(parents=True, exist_ok=True)
    (output_dir / "embeddings").mkdir(parents=True, exist_ok=True)


def timestamp_label(seconds: float) -> str:
    total = int(seconds)
    millis = int(round((seconds - total) * 1000))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours:02d}-{minutes:02d}-{secs:02d}-{millis:03d}"
    return f"{minutes:02d}-{secs:02d}-{millis:03d}"


def write_keyframes(
    output_dir: Path,
    vectors: list[FrameVector],
    selected_indexes: list[int],
    prefix: str = "keyframe",
) -> dict[int, str]:
    frame_dir = output_dir / "frames"
    index_to_file: dict[int, str] = {}
    for chronological_index, vector_index in enumerate(selected_indexes, start=1):
        vector = vectors[vector_index]
        filename = f"{prefix}_{chronological_index:04d}_{timestamp_label(vector.timestamp)}.jpg"
        encode_jpeg(frame_dir / filename, vector.frame_bgr)
        index_to_file[vector.source_index] = f"frames/{filename}"
    return index_to_file


def write_embeddings(output_dir: Path, vectors: list[FrameVector]) -> str:
    path = output_dir / "embeddings" / "frame_features.npz"
    features = np.stack([vector.feature for vector in vectors]).astype(np.float32)
    timestamps = np.array([vector.timestamp for vector in vectors], dtype=np.float32)
    source_indexes = np.array([vector.source_index for vector in vectors], dtype=np.int32)
    np.savez_compressed(path, features=features, timestamps=timestamps, source_indexes=source_indexes)
    return "embeddings/frame_features.npz"


def write_segments_jsonl(output_dir: Path, segments: list[VideoSegment]) -> str:
    path = output_dir / "segments.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for segment in segments:
            handle.write(json.dumps(segment.to_dict(), ensure_ascii=False) + "\n")
    return "segments.jsonl"


def write_video_json(
    output_dir: Path,
    metadata: VideoMetadata,
    detail: str,
    vectors: list[FrameVector],
    selected_source_indexes: set[int],
    segments: list[VideoSegment],
    artifacts: dict[str, str],
) -> str:
    path = output_dir / "video.json"
    payload = {
        "schema": "video-to-llm/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source": metadata.path,
        "detail": detail,
        "metadata": {
            "duration": round(metadata.duration, 3),
            "width": metadata.width,
            "height": metadata.height,
            "fps": round(metadata.fps, 3),
            "frame_count": metadata.frame_count,
            "codec": metadata.codec,
        },
        "artifacts": artifacts,
        "frames": [
            {
                **vector.to_public_dict(),
                "selected": vector.source_index in selected_source_indexes,
            }
            for vector in vectors
        ],
        "segments": [segment.to_dict() for segment in segments],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return "video.json"


def write_timeline_markdown(output_dir: Path, metadata: VideoMetadata, detail: str, segments: list[VideoSegment]) -> str:
    path = output_dir / "timeline.md"
    lines = [
        "# Video Timeline",
        "",
        f"- Source: `{metadata.path}`",
        f"- Duration: `{metadata.duration:.2f}s`",
        f"- Resolution: `{metadata.width}x{metadata.height}`",
        f"- Detail: `{detail}`",
        "",
        "## Segments",
        "",
    ]
    for segment in segments:
        lines.append(
            f"### Segment {segment.segment_id}: {segment.start:.2f}s to {segment.end:.2f}s"
        )
        lines.append("")
        lines.append(f"- Representative frame: `{segment.representative_timestamp:.2f}s`")
        if segment.keyframe_file:
            lines.append(f"- Keyframe: `{segment.keyframe_file}`")
        lines.append(f"- Frames sampled: `{segment.frame_count}`")
        lines.append(f"- Change score: `{segment.change_score:.4f}`")
        lines.append(
            f"- Visual stats: brightness `{segment.avg_brightness:.1f}`, contrast `{segment.avg_contrast:.1f}`, sharpness `{segment.avg_sharpness:.1f}`"
        )
        if segment.ocr_text:
            lines.append("")
            lines.append("OCR text:")
            lines.append("")
            lines.append("```text")
            lines.append(segment.ocr_text)
            lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return "timeline.md"

