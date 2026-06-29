from __future__ import annotations

import numpy as np

from video_to_llm.events import detect_visual_events, write_events
from video_to_llm.features import frame_to_vector


def test_detect_visual_events_finds_burst() -> None:
    vectors = []
    for index in range(20):
        frame = np.full((90, 160, 3), 20, dtype=np.uint8)
        if 8 <= index <= 11:
            frame[:, :80] = (255, 255, 255)
        previous = vectors[-1] if vectors else None
        vectors.append(frame_to_vector(index, index * 0.1, frame, previous))

    events = detect_visual_events(
        vectors,
        duration=2.0,
        window_seconds=0.5,
        threshold_percentile=90,
        min_distance=0.05,
        max_events=4,
    )

    assert events
    assert events[0].event_type == "visual_burst"
    assert 0.5 <= events[0].peak <= 1.3
    assert events[0].frame_count > 0


def test_write_events_creates_jsonl_and_contact_sheet(tmp_path) -> None:
    vectors = []
    for index in range(8):
        frame = np.full((90, 160, 3), index * 20, dtype=np.uint8)
        previous = vectors[-1] if vectors else None
        vectors.append(frame_to_vector(index, index * 0.1, frame, previous))

    events = detect_visual_events(
        vectors,
        duration=0.8,
        window_seconds=0.4,
        threshold_percentile=50,
        min_distance=0.01,
        max_events=1,
    )
    source_video = tmp_path / "missing.mp4"
    relative = write_events(tmp_path, source_video, vectors, events, max_frames_per_event=4, write_clips=False)

    assert relative == "events.jsonl"
    assert (tmp_path / "events.jsonl").exists()
    assert list((tmp_path / "events").glob("event_*/event.json"))
    assert list((tmp_path / "events").glob("event_*/contact_sheet.jpg"))

