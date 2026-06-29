from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .features import FrameVector


@dataclass
class VideoSegment:
    segment_id: int
    start: float
    end: float
    representative_timestamp: float
    representative_source_index: int
    frame_count: int
    change_score: float
    avg_brightness: float
    avg_contrast: float
    avg_sharpness: float
    keyframe_file: str | None = None
    ocr_text: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(max(0.0, self.end - self.start), 3),
            "representative_timestamp": round(self.representative_timestamp, 3),
            "representative_source_index": self.representative_source_index,
            "frame_count": self.frame_count,
            "change_score": round(self.change_score, 6),
            "avg_brightness": round(self.avg_brightness, 3),
            "avg_contrast": round(self.avg_contrast, 3),
            "avg_sharpness": round(self.avg_sharpness, 3),
            "keyframe_file": self.keyframe_file,
            "ocr_text": self.ocr_text,
            "notes": self.notes,
        }


def farthest_point_select(vectors: list[FrameVector], count: int, min_gap: float) -> list[int]:
    if not vectors or count <= 0:
        return []
    features = np.stack([vector.feature for vector in vectors]).astype(np.float32)
    center = np.mean(features, axis=0, keepdims=True)
    first = int(np.argmax(np.linalg.norm(features - center, axis=1)))

    selected = [first]
    min_distances = np.linalg.norm(features - features[first], axis=1)

    while len(selected) < min(count, len(vectors)):
        mask = np.ones(len(vectors), dtype=bool)
        for selected_index in selected:
            selected_timestamp = vectors[selected_index].timestamp
            for candidate_index, candidate in enumerate(vectors):
                if abs(candidate.timestamp - selected_timestamp) < min_gap:
                    mask[candidate_index] = False
        mask[selected] = False

        if not np.any(mask):
            mask = np.ones(len(vectors), dtype=bool)
            mask[selected] = False
            if not np.any(mask):
                break

        scores = min_distances.copy()
        scores[~mask] = -1.0
        next_index = int(np.argmax(scores))
        selected.append(next_index)
        new_distances = np.linalg.norm(features - features[next_index], axis=1)
        min_distances = np.minimum(min_distances, new_distances)

    return sorted(selected, key=lambda index: vectors[index].timestamp)


def adaptive_boundary_threshold(vectors: list[FrameVector], percentile: float) -> float:
    distances = [vector.distance_from_previous for vector in vectors if vector.distance_from_previous is not None]
    if not distances:
        return float("inf")
    return float(np.percentile(np.array(distances, dtype=np.float32), percentile))


def build_segments(vectors: list[FrameVector], min_segment_seconds: float, boundary_percentile: float) -> list[VideoSegment]:
    if not vectors:
        return []

    threshold = adaptive_boundary_threshold(vectors, boundary_percentile)
    groups: list[list[FrameVector]] = []
    current: list[FrameVector] = [vectors[0]]

    for vector in vectors[1:]:
        elapsed = vector.timestamp - current[0].timestamp
        changed = vector.distance_from_previous is not None and vector.distance_from_previous >= threshold
        if changed and elapsed >= min_segment_seconds:
            groups.append(current)
            current = [vector]
        else:
            current.append(vector)

    if current:
        groups.append(current)

    segments: list[VideoSegment] = []
    for segment_id, group in enumerate(groups, start=1):
        distances = [vector.distance_from_previous or 0.0 for vector in group]
        sharpest = max(group, key=lambda vector: vector.sharpness)
        segments.append(
            VideoSegment(
                segment_id=segment_id,
                start=group[0].timestamp,
                end=group[-1].timestamp,
                representative_timestamp=sharpest.timestamp,
                representative_source_index=sharpest.source_index,
                frame_count=len(group),
                change_score=max(distances) if distances else 0.0,
                avg_brightness=sum(vector.brightness for vector in group) / len(group),
                avg_contrast=sum(vector.contrast for vector in group) / len(group),
                avg_sharpness=sum(vector.sharpness for vector in group) / len(group),
            )
        )
    return segments

