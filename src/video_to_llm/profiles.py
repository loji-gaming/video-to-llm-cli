from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetailProfile:
    name: str
    sample_interval: float
    min_segment_seconds: float
    target_keyframes: int
    boundary_percentile: float


DETAIL_PROFILES: dict[str, DetailProfile] = {
    "low": DetailProfile(
        name="low",
        sample_interval=5.0,
        min_segment_seconds=12.0,
        target_keyframes=12,
        boundary_percentile=92.0,
    ),
    "medium": DetailProfile(
        name="medium",
        sample_interval=2.0,
        min_segment_seconds=7.0,
        target_keyframes=24,
        boundary_percentile=88.0,
    ),
    "high": DetailProfile(
        name="high",
        sample_interval=1.0,
        min_segment_seconds=4.0,
        target_keyframes=48,
        boundary_percentile=82.0,
    ),
    "exhaustive": DetailProfile(
        name="exhaustive",
        sample_interval=0.5,
        min_segment_seconds=2.0,
        target_keyframes=96,
        boundary_percentile=75.0,
    ),
}


def get_profile(name: str) -> DetailProfile:
    try:
        return DETAIL_PROFILES[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(DETAIL_PROFILES))
        raise ValueError(f"Unknown detail profile {name!r}; expected one of: {allowed}") from exc

