from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from .features import FrameVector, frame_to_vector, is_useful_frame
from .ocr import extract_text
from .outputs import (
    prepare_output_dir,
    write_embeddings,
    write_keyframes,
    write_segments_jsonl,
    write_timeline_markdown,
    write_video_json,
)
from .profiles import get_profile
from .selection import build_segments, farthest_point_select
from .video import VideoMetadata, iter_sample_timestamps, probe_video


@dataclass
class AnalysisResult:
    output_dir: Path
    metadata: VideoMetadata
    frame_count: int
    segment_count: int
    keyframe_count: int
    artifacts: dict[str, str]


def collect_vectors(video_path: Path, timestamps: list[float]) -> list[FrameVector]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    vectors: list[FrameVector] = []
    previous: FrameVector | None = None
    try:
        for source_index, timestamp in enumerate(timestamps):
            capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp) * 1000.0)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            vector = frame_to_vector(source_index, timestamp, frame, previous)
            previous = vector
            if is_useful_frame(vector):
                vectors.append(vector)
    finally:
        capture.release()

    return vectors


def resolve_output_dir(input_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return Path.cwd() / f"{input_path.stem}.video_to_llm"


def run_analysis(
    input_path: Path,
    output_dir: Path | None,
    detail: str,
    keyframes: int | None = None,
    sample_interval: float | None = None,
    min_gap: float | None = None,
    ocr_mode: str = "none",
    save_embeddings: bool = True,
    include_segment_keyframes: bool = True,
) -> AnalysisResult:
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    profile = get_profile(detail)
    interval = sample_interval or profile.sample_interval
    target_keyframes = keyframes or profile.target_keyframes
    minimum_gap = min_gap if min_gap is not None else max(profile.min_segment_seconds, interval)

    metadata = probe_video(input_path)
    timestamps = iter_sample_timestamps(metadata.duration, interval)
    vectors = collect_vectors(input_path, timestamps)
    if not vectors:
        raise RuntimeError("No useful frames were sampled from the input video")

    segments = build_segments(vectors, profile.min_segment_seconds, profile.boundary_percentile)
    selected_vector_indexes = farthest_point_select(vectors, target_keyframes, minimum_gap)

    source_index_to_vector_index = {vector.source_index: index for index, vector in enumerate(vectors)}
    if include_segment_keyframes:
        for segment in segments:
            vector_index = source_index_to_vector_index.get(segment.representative_source_index)
            if vector_index is not None and vector_index not in selected_vector_indexes:
                selected_vector_indexes.append(vector_index)
    selected_vector_indexes = sorted(set(selected_vector_indexes), key=lambda index: vectors[index].timestamp)

    out = resolve_output_dir(input_path, output_dir)
    prepare_output_dir(out)
    source_to_file = write_keyframes(out, vectors, selected_vector_indexes)

    for segment in segments:
        segment.keyframe_file = source_to_file.get(segment.representative_source_index)
        if ocr_mode != "none" and segment.keyframe_file:
            segment.ocr_text = extract_text(out / segment.keyframe_file, ocr_mode)

    artifacts: dict[str, str] = {}
    if save_embeddings:
        artifacts["embeddings"] = write_embeddings(out, vectors)
    artifacts["segments_jsonl"] = write_segments_jsonl(out, segments)
    artifacts["timeline_markdown"] = write_timeline_markdown(out, metadata, detail, segments)
    artifacts["video_json"] = "video.json"
    selected_source_indexes = {vectors[index].source_index for index in selected_vector_indexes}
    write_video_json(
        out,
        metadata,
        detail,
        vectors,
        selected_source_indexes,
        segments,
        artifacts,
    )

    return AnalysisResult(
        output_dir=out,
        metadata=metadata,
        frame_count=len(vectors),
        segment_count=len(segments),
        keyframe_count=len(selected_vector_indexes),
        artifacts=artifacts,
    )
