from __future__ import annotations

import numpy as np

from video_to_llm.features import build_feature, frame_to_vector
from video_to_llm.selection import build_segments, farthest_point_select


def test_feature_vector_is_normalized() -> None:
    frame = np.zeros((90, 160, 3), dtype=np.uint8)
    frame[:, :80] = (255, 0, 0)
    frame[:, 80:] = (0, 255, 0)

    feature, brightness, contrast, sharpness = build_feature(frame)

    assert feature.ndim == 1
    assert abs(float(np.linalg.norm(feature)) - 1.0) < 1e-5
    assert brightness > 0
    assert contrast > 0
    assert sharpness >= 0


def test_selection_and_segments() -> None:
    frames = []
    for index in range(8):
        frame = np.full((90, 160, 3), index * 25, dtype=np.uint8)
        if index >= 4:
            frame[:, :40] = (0, 255, 0)
        previous = frames[-1] if frames else None
        frames.append(frame_to_vector(index, float(index), frame, previous))

    selected = farthest_point_select(frames, count=3, min_gap=1.0)
    segments = build_segments(frames, min_segment_seconds=1.0, boundary_percentile=70.0)

    assert len(selected) == 3
    assert selected == sorted(selected)
    assert len(segments) >= 1
    assert segments[0].segment_id == 1

