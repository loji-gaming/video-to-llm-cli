from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .analysis import run_analysis
from .profiles import DETAIL_PROFILES
from .stream import stream_growing_file

OCR_MODES = {"none", "tesseract"}


app = typer.Typer(
    name="video-to-llm",
    help="Convert videos into structured timelines, vectors, OCR text, and representative frames for LLM workflows.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def llm_help_payload() -> dict:
    detail_profiles = {
        name: {
            "sample_interval_seconds": profile.sample_interval,
            "min_segment_seconds": profile.min_segment_seconds,
            "target_keyframes": profile.target_keyframes,
            "boundary_percentile": profile.boundary_percentile,
        }
        for name, profile in DETAIL_PROFILES.items()
    }
    return {
        "schema": "video-to-llm/help-v1",
        "program": "video-to-llm",
        "version": __version__,
        "purpose": "Convert video files or growing capture files into LLM-friendly timelines, representative frames, frame vectors, OCR text, and JSONL events.",
        "global_options": [
            {"flag": "--help", "alias": "-h", "description": "Show human-oriented CLI help."},
            {"flag": "--help-llm", "description": "Show this structured LLM-oriented help as JSON."},
            {"flag": "--version", "description": "Show package version."},
        ],
        "detail_profiles": detail_profiles,
        "commands": {
            "analyze": {
                "summary": "Analyze a complete video file and write LLM-friendly artifacts.",
                "usage": "video-to-llm analyze INPUT_VIDEO --detail medium --out ./context",
                "arguments": [{"name": "INPUT_VIDEO", "type": "path", "required": True}],
                "options": [
                    {"flag": "--out", "alias": "-o", "type": "path", "description": "Output directory."},
                    {"flag": "--detail", "type": "enum", "values": list(DETAIL_PROFILES), "default": "medium"},
                    {"flag": "--keyframes", "alias": "-k", "type": "int", "description": "Target number of diverse keyframes."},
                    {"flag": "--sample-interval", "type": "float", "description": "Override seconds between sampled frames."},
                    {"flag": "--min-gap", "type": "float", "description": "Minimum seconds between selected keyframes."},
                    {"flag": "--ocr", "type": "enum", "values": sorted(OCR_MODES), "default": "none"},
                    {"flag": "--no-embeddings", "type": "bool", "description": "Skip compressed frame feature vectors."},
                    {"flag": "--detect-events", "type": "bool", "description": "Detect high-change visual event windows and write event artifacts."},
                    {"flag": "--event-window", "type": "float", "default": 1.5, "description": "Seconds of context around each detected visual burst."},
                    {"flag": "--event-threshold-percentile", "type": "float", "default": 95.0},
                    {"flag": "--event-min-distance", "type": "float", "default": 0.2},
                    {"flag": "--event-merge-gap", "type": "float", "default": 0.35},
                    {"flag": "--max-events", "type": "int", "default": 24},
                    {"flag": "--event-max-frames", "type": "int", "default": 120},
                    {"flag": "--event-clips/--no-event-clips", "type": "bool", "default": True},
                    {"flag": "--stdout", "type": "bool", "description": "Emit compact JSON summary to stdout."},
                ],
                "outputs": [
                    "video.json",
                    "segments.jsonl",
                    "timeline.md",
                    "frames/*.jpg",
                    "embeddings/frame_features.npz",
                    "events.jsonl and events/event_*/ when --detect-events is used",
                ],
            },
            "frames": {
                "summary": "Extract a requested number of representative screenshots.",
                "usage": "video-to-llm frames INPUT_VIDEO --count 20 --out ./frames_context",
                "arguments": [{"name": "INPUT_VIDEO", "type": "path", "required": True}],
                "options": [
                    {"flag": "--out", "alias": "-o", "type": "path", "description": "Output directory."},
                    {"flag": "--count", "alias": "-n", "type": "int", "default": 20},
                    {"flag": "--detail", "type": "enum", "values": list(DETAIL_PROFILES), "default": "medium"},
                    {"flag": "--sample-interval", "type": "float", "description": "Override seconds between sampled frames."},
                    {"flag": "--min-gap", "type": "float", "description": "Minimum seconds between selected keyframes."},
                    {"flag": "--stdout", "type": "bool", "description": "Emit compact JSON summary to stdout."},
                ],
                "outputs": ["video.json", "segments.jsonl", "timeline.md", "frames/*.jpg", "embeddings/frame_features.npz"],
            },
            "stream": {
                "summary": "Experimentally watch a growing video file and emit JSONL frame events.",
                "usage": "video-to-llm stream CAPTURE_FILE --detail low --out ./stream_context --log ./stream_context/events.jsonl --state ./stream_context/state.json",
                "arguments": [{"name": "CAPTURE_FILE", "type": "path", "required": True}],
                "options": [
                    {"flag": "--out", "alias": "-o", "type": "path", "description": "Optional output directory for boundary keyframes."},
                    {"flag": "--detail", "type": "enum", "values": list(DETAIL_PROFILES), "default": "low"},
                    {"flag": "--sample-interval", "type": "float", "description": "Override seconds between observations."},
                    {"flag": "--poll", "type": "float", "default": 2.0},
                    {"flag": "--boundary-distance", "type": "float", "default": 0.35},
                    {"flag": "--safe-lag", "type": "float", "default": 1.0},
                    {"flag": "--log", "type": "path", "description": "Append JSONL events to this file."},
                    {"flag": "--state", "type": "path", "description": "Read/write resume state JSON."},
                    {"flag": "--stop-after", "type": "float", "description": "Stop after seconds; useful for tests or supervised runs."},
                    {"flag": "--stdout/--no-stdout", "type": "bool", "default": True},
                ],
                "event_schema": {
                    "type": "frame_observation",
                    "fields": [
                        "event_id",
                        "source",
                        "timestamp",
                        "available_duration",
                        "distance_from_previous",
                        "is_boundary",
                        "brightness",
                        "contrast",
                        "sharpness",
                        "keyframe_file",
                    ],
                },
            },
        },
        "recommended_llm_workflows": [
            "Use analyze for completed videos; read video.json and segments.jsonl first, then inspect referenced keyframes when visual evidence is needed.",
            "Use analyze --detect-events for VFX, combat, UI transitions, explosions, shield hits, or other brief high-change visual moments.",
            "Use frames when the task only needs a compact screenshot set.",
            "Use stream for capture files that are still being written; consume JSONL events from stdout or --log.",
        ],
    }


def help_llm_callback(value: bool) -> None:
    if value:
        typer.echo(json.dumps(llm_help_payload(), indent=2, ensure_ascii=False))
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, help="Show package version."),
    help_llm: bool = typer.Option(
        False,
        "--help-llm",
        callback=help_llm_callback,
        is_eager=True,
        help="Show structured LLM-oriented help as JSON.",
    ),
) -> None:
    return None


def detail_option(default: str = "medium") -> str:
    return typer.Option(default, "--detail", help=f"Detail profile: {', '.join(DETAIL_PROFILES)}")


def validate_options(detail: str, ocr: str | None = None) -> None:
    if detail not in DETAIL_PROFILES:
        allowed = ", ".join(DETAIL_PROFILES)
        raise typer.BadParameter(f"unknown detail profile {detail!r}; expected one of: {allowed}")
    if ocr is not None and ocr not in OCR_MODES:
        allowed = ", ".join(sorted(OCR_MODES))
        raise typer.BadParameter(f"unknown OCR mode {ocr!r}; expected one of: {allowed}")


@app.command()
def analyze(
    input_video: Path = typer.Argument(..., exists=True, readable=True, help="Input video file."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory."),
    detail: str = detail_option("medium"),
    keyframes: Optional[int] = typer.Option(None, "--keyframes", "-k", help="Target number of diverse keyframes."),
    sample_interval: Optional[float] = typer.Option(None, "--sample-interval", help="Override seconds between sampled frames."),
    min_gap: Optional[float] = typer.Option(None, "--min-gap", help="Minimum seconds between selected keyframes."),
    ocr: str = typer.Option("none", "--ocr", help="OCR mode: none or tesseract."),
    no_embeddings: bool = typer.Option(False, "--no-embeddings", help="Do not write compressed frame feature vectors."),
    detect_events: bool = typer.Option(False, "--detect-events", help="Detect high-change visual event windows and write event artifacts."),
    event_window: float = typer.Option(1.5, "--event-window", help="Seconds of context around each detected visual burst."),
    event_threshold_percentile: float = typer.Option(95.0, "--event-threshold-percentile", help="Frame-distance percentile for event detection."),
    event_min_distance: float = typer.Option(0.2, "--event-min-distance", help="Minimum frame-vector distance required for event detection."),
    event_merge_gap: float = typer.Option(0.35, "--event-merge-gap", help="Maximum seconds between visual spikes before starting a separate event."),
    max_events: int = typer.Option(24, "--max-events", help="Maximum detected events to write."),
    event_max_frames: int = typer.Option(120, "--event-max-frames", help="Maximum sampled frames to save per event."),
    event_clips: bool = typer.Option(True, "--event-clips/--no-event-clips", help="Write short MP4 clips for detected events."),
    stdout: bool = typer.Option(False, "--stdout", help="Emit a compact JSON result to stdout."),
) -> None:
    """Analyze a complete video file and write LLM-friendly artifacts."""
    validate_options(detail, ocr)
    result = run_analysis(
        input_path=input_video,
        output_dir=out,
        detail=detail,
        keyframes=keyframes,
        sample_interval=sample_interval,
        min_gap=min_gap,
        ocr_mode=ocr,
        save_embeddings=not no_embeddings,
        include_segment_keyframes=True,
        detect_events=detect_events,
        event_window_seconds=event_window,
        event_threshold_percentile=event_threshold_percentile,
        event_min_distance=event_min_distance,
        event_merge_gap_seconds=event_merge_gap,
        max_events=max_events,
        event_max_frames=event_max_frames,
        event_clips=event_clips,
    )
    payload = {
        "output_dir": str(result.output_dir),
        "duration": round(result.metadata.duration, 3),
        "frames_sampled": result.frame_count,
        "segments": result.segment_count,
        "keyframes": result.keyframe_count,
        "artifacts": result.artifacts,
    }
    if stdout:
        typer.echo(json.dumps(payload, ensure_ascii=False))
    else:
        typer.echo(f"Wrote analysis to {result.output_dir}", err=True)
        typer.echo(
            f"Sampled {result.frame_count} frames, built {result.segment_count} segments, wrote {result.keyframe_count} keyframes",
            err=True,
        )


@app.command()
def frames(
    input_video: Path = typer.Argument(..., exists=True, readable=True, help="Input video file."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output directory."),
    count: int = typer.Option(20, "--count", "-n", help="Target number of diverse frame screenshots."),
    detail: str = detail_option("medium"),
    sample_interval: Optional[float] = typer.Option(None, "--sample-interval", help="Override seconds between sampled frames."),
    min_gap: Optional[float] = typer.Option(None, "--min-gap", help="Minimum seconds between selected keyframes."),
    stdout: bool = typer.Option(False, "--stdout", help="Emit a compact JSON result to stdout."),
) -> None:
    """Extract diverse representative screenshots using the same analyzer."""
    validate_options(detail)
    result = run_analysis(
        input_path=input_video,
        output_dir=out,
        detail=detail,
        keyframes=count,
        sample_interval=sample_interval,
        min_gap=min_gap,
        ocr_mode="none",
        save_embeddings=True,
        include_segment_keyframes=False,
    )
    payload = {
        "output_dir": str(result.output_dir),
        "duration": round(result.metadata.duration, 3),
        "frames_sampled": result.frame_count,
        "segments": result.segment_count,
        "keyframes": result.keyframe_count,
        "artifacts": result.artifacts,
    }
    if stdout:
        typer.echo(json.dumps(payload, ensure_ascii=False))
    else:
        typer.echo(f"Wrote frames to {result.output_dir / 'frames'}", err=True)
        typer.echo(
            f"Sampled {result.frame_count} frames and wrote {result.keyframe_count} keyframes",
            err=True,
        )


@app.command()
def stream(
    input_video: Path = typer.Argument(..., help="Video file that may still be growing."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Optional output directory for boundary keyframes."),
    detail: str = detail_option("low"),
    sample_interval: Optional[float] = typer.Option(None, "--sample-interval", help="Override seconds between observations."),
    poll_seconds: float = typer.Option(2.0, "--poll", help="Seconds between file probes."),
    boundary_distance: float = typer.Option(0.35, "--boundary-distance", help="Vector distance needed to emit a boundary keyframe."),
    safe_lag_seconds: float = typer.Option(1.0, "--safe-lag", help="Seconds to stay behind the detected file duration."),
    log: Optional[Path] = typer.Option(None, "--log", help="Append JSONL events to this file."),
    state: Optional[Path] = typer.Option(None, "--state", help="Read/write resume state JSON."),
    stop_after: Optional[float] = typer.Option(None, "--stop-after", help="Stop after this many seconds; useful for tests."),
    stdout: bool = typer.Option(True, "--stdout/--no-stdout", help="Emit JSONL events to stdout."),
) -> None:
    """Experimentally watch a growing video file and emit JSONL frame events."""
    validate_options(detail)
    stream_growing_file(
        input_path=input_video,
        detail=detail,
        output_dir=out,
        stdout=stdout,
        log_path=log,
        state_path=state,
        poll_seconds=poll_seconds,
        sample_interval=sample_interval,
        boundary_distance=boundary_distance,
        safe_lag_seconds=safe_lag_seconds,
        stop_after_seconds=stop_after,
    )
