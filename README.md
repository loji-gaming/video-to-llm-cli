# video-to-llm-cli

Turn videos into structured data that an LLM can consume quickly: visual segments,
representative keyframes, OCR text, per-frame vectors, and JSON/Markdown timeline
artifacts.

This is designed for development workflows where an assistant needs to understand
game footage, screen recordings, tutorials, UI states, or files that are still
being written by a capture process.

## Status

Version 0.2 is a practical local-first pipeline:

- Samples a video according to `--detail`
- Builds a compact vector for each sampled frame
- Collapses visually similar stretches into timeline segments
- Selects diverse keyframes with Euclidean farthest-point selection
- Detects high-change visual event windows and writes event evidence on request
- Writes structured artifacts for LLM ingestion
- Optionally runs local Tesseract OCR on keyframes
- Experimentally watches a growing video file and emits JSONL events

The default embedding is deterministic and lightweight: low-resolution visual
structure, HSV color histogram, perceptual DCT hash, brightness, and contrast.
This keeps the tool fast and installable on normal dev machines. A learned
ranker or CLIP/SigLIP/DINO embedding backend belongs in v2 once there is a
small labeled dataset of "best representative frame" examples.

## Install

```bash
pipx install git+https://github.com/loji-gaming/video-to-llm-cli.git
```

For local development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

System dependency:

```bash
ffmpeg
ffprobe
```

Optional OCR dependency:

```bash
tesseract
```

## Quick Start

```bash
video-to-llm --help
video-to-llm --help-llm
video-to-llm analyze recording.mp4 --detail medium --out ./recording_context
video-to-llm analyze recording.mp4 --detail high --detect-events --out ./recording_context_events
```

Artifacts:

```text
recording_context/
  video.json
  segments.jsonl
  timeline.md
  frames/
    keyframe_0001_00-02-500.jpg
    ...
  embeddings/
    frame_features.npz
  events.jsonl
  events/
    event_0001_visual_burst_...
      event.json
      clip.mp4
      contact_sheet.jpg
      frames/
```

## Commands

### Help

Human help:

```bash
video-to-llm --help
video-to-llm -h
video-to-llm analyze --help
```

Structured help for LLM/tool agents:

```bash
video-to-llm --help-llm
```

This prints JSON with command names, options, output artifacts, stream event
fields, and recommended LLM workflows.

### Analyze

```bash
video-to-llm analyze input.mp4 --detail medium --out ./context
```

Useful options:

```bash
--detail low|medium|high|exhaustive
--keyframes 40
--sample-interval 1.0
--min-gap 4
--ocr tesseract
--detect-events
--event-window 1.5
--event-threshold-percentile 95
--event-min-distance 0.2
--event-merge-gap 0.35
--event-max-frames 120
--stdout
--no-embeddings
```

### Detect Visual Events

Use event detection for short, important changes such as VFX impacts,
explosions, shield hits, UI transitions, cuts, menu opens, or other moments that
need frame-by-frame evidence.

```bash
video-to-llm analyze input.mp4 \
  --detail exhaustive \
  --sample-interval 0.02 \
  --detect-events \
  --event-window 1.5 \
  --event-max-frames 120 \
  --out ./context_events
```

Event outputs:

```text
context_events/
  events.jsonl
  events/
    event_0001_visual_burst_00-05-750_00-07-150/
      event.json
      clip.mp4
      contact_sheet.jpg
      frames/
        frame_0001_00-05-750.jpg
        ...
```

Use `events.jsonl` first, then inspect the event contact sheet and clip for
visual evidence. Increase `--event-max-frames` when an event needs denser
frame-by-frame review.

### Extract Representative Frames

```bash
video-to-llm frames input.mp4 --count 20 --out ./frames_context
```

This uses the same vector pipeline as `analyze`, but is tuned for screenshot
selection.

### Stream a Growing File

```bash
video-to-llm stream capture.mkv \
  --detail low \
  --out ./stream_context \
  --log ./stream_context/events.jsonl \
  --state ./stream_context/state.json
```

The stream mode polls a video file that may still be growing, processes new
timestamps, and emits JSONL `frame_observation` events to stdout by default.
When a visual boundary is detected, it can write a keyframe image.

This is intentionally marked experimental. It works best with containers that
remain readable while being written, such as many MKV or fragmented MP4 capture
workflows. Low-latency game-window capture, RTSP, OBS pipes, controller loops,
and bidirectional agent control are v2 scope.

## Detail Profiles

| Detail | Sample interval | Purpose |
| --- | ---: | --- |
| `low` | 5.0s | Fast overview, streaming, long videos |
| `medium` | 2.0s | Default balance |
| `high` | 1.0s | Dense UI/gameplay changes |
| `exhaustive` | 0.5s | Heavy local analysis |

You can override the interval directly:

```bash
video-to-llm analyze input.mp4 --detail high --sample-interval 0.25
```

## LLM Consumption Strategy

Do not send every frame image to an LLM. Most frames in video are redundant,
and image calls are slow and expensive.

Recommended flow:

1. Use vectors to segment the whole video.
2. Use `--detect-events` to isolate brief high-change moments.
3. Use OCR on keyframes or text-changing frames.
4. Send `video.json`, `segments.jsonl`, `events.jsonl`, and selected keyframes/contact sheets to the LLM.
5. Ask follow-up questions by retrieving relevant segments, events, and nearby frames.

For UI-heavy or document-heavy video, OCR should be enabled. For game state and
visual scenes, selected keyframes should still be available because text-only
conversion can lose important state.

## Output Schema

`video.json` contains:

- Source metadata
- Detail profile
- Artifact paths
- One record per sampled frame
- One record per visual segment
- Keyframe file references
- Event references when `--detect-events` is enabled
- OCR text when enabled

`segments.jsonl` is optimized for streaming into logs, vector stores, and LLM
retrieval pipelines.

`embeddings/frame_features.npz` contains:

- `features`: frame feature matrix
- `timestamps`: timestamp per feature
- `source_indexes`: sampled-frame indexes

## Roadmap

v1:

- Local deterministic vectors
- Segment JSON/Markdown output
- Representative keyframes
- Optional Tesseract OCR
- Experimental growing-file stream mode

v2:

- Pluggable CLIP/SigLIP/DINOv2 embeddings
- Small learned keyframe ranker
- OCR model plugins for open vision-language OCR models
- Real-time capture backends
- Agent control loop helpers for games and apps
- Local retrieval server over the generated timeline
