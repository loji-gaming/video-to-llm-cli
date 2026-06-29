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
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, help="Show package version."),
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
