# video-to-context

Extract full context from video files: audio transcription + smart screenshots + visual description, all merged into a single rich VTT file.

## What It Does

Given any video file, the pipeline:

1. **Extracts audio** via ffmpeg (16kHz mono WAV)
2. **Transcribes** with WhisperX (large-v3, word-level timestamps via forced alignment)
3. **Picks smart screenshot timestamps** by detecting topic boundaries (gaps in speech) and ensuring even coverage across the video
4. **Extracts frames** via ffmpeg at those timestamps
5. **Hybrid OCR + visual description**:
   - **EasyOCR** extracts readable text (zero hallucination — best for documents, slides, clean text)
   - **Qwen3-VL-8B** (4-bit quantized) describes visual layout, UI elements, and game state (for stylized text that OCR can't read)
6. **Produces a rich VTT** with interleaved speech cues and `[VISUAL 📷]` context notes showing what's on screen

## Quick Start

```bash
# Activate the environment
source ~/.local/share/whisperx-pipeline/bin/activate

# Run on a video file (English)
video-to-context recording.mkv --language en

# For game recordings / stylized UIs (VLM-only, skip OCR)
video-to-context recording.mkv --language en --no-paddleocr

# For document recordings / presentations (OCR-only, skip VLM)
video-to-context recording.mkv --language en --no-vlm
```

Output goes to `<video_stem>/` next to the input file:

```
2026-05-30 14-38-29/
├── audio.wav              # Extracted audio (16kHz mono)
├── transcript.json        # Raw WhisperX output (word-level timestamps)
├── frames/                # Extracted screenshots (frame_001.jpg, etc.)
├── paddleocr_results.json # EasyOCR text extraction per frame
├── vlm_results.json       # VLM visual descriptions per frame
├── ocr_results.json       # Merged: OCR text + VLM description
└── output.vtt             # Final VTT with speech + visual context
```

## Requirements

### Hardware

| Component | Minimum        | Recommended                      |
| --------- | -------------- | -------------------------------- |
| GPU VRAM  | 8GB (3B model) | 16GB (8B model with 4-bit quant) |
| RAM       | 16GB           | 32GB                             |
| Disk      | 2GB free       | 5GB free (for model cache)       |

Tested on: **NVIDIA RTX 4070 Ti SUPER (16GB VRAM)**

### Software

The Python 3.11 venv is pre-built at `~/.local/share/whisperx-pipeline/`:

| Package        | Version     | Purpose                                            |
| -------------- | ----------- | -------------------------------------------------- |
| whisperx       | 3.8.6       | Audio transcription + word alignment               |
| faster-whisper | 1.2.1       | CTranslate2-backed Whisper inference               |
| transformers   | 4.57.6      | Qwen3-VL model loading                             |
| qwen-vl-utils  | 0.0.14      | Vision preprocessing for Qwen models               |
| bitsandbytes   | 0.49.2      | 4-bit quantization (NF4) for 8B model              |
| accelerate     | 1.13.0      | Device map / model offloading                      |
| easyocr        | 1.7.2       | Deterministic text extraction (zero hallucination) |
| torch          | 2.8.0+cu128 | CUDA backend                                       |

System tools: `ffmpeg` (required)

### First-time setup (if rebuilding)

```bash
# Create venv with Python 3.11 (WhisperX doesn't support 3.14 yet)
uv venv --python 3.11 ~/.local/share/whisperx-pipeline
source ~/.local/share/whisperx-pipeline/bin/activate

# Install all dependencies
uv pip install whisperx transformers accelerate qwen-vl-utils bitsandbytes Pillow easyocr

# Make the script executable
chmod +x ~/.local/bin/video-to-context
```

## Usage

### Basic

```bash
video-to-context my_video.mkv --language en
```

### All Options

```
video-to-context <input_video> [options]

Positional:
  input                   Input video file (mkv, mp4, avi, etc.)

Options:
  --output-dir DIR        Output directory (default: <input_stem>/ next to video)
  --whisper-model MODEL   WhisperX model: tiny, base, small, medium, large-v2, large-v3
                          (default: large-v3)
  --language CODE         Language code for alignment: en, es, fr, de, etc.
                          Omit for auto-detection (no word-level timestamps)
  --vlm-model MODEL       VLM model for visual description (default: Qwen/Qwen3-VL-8B-Instruct)
  --ocr-model MODEL       Alias for --vlm-model
  --max-screenshots N     Maximum screenshots (default: 15)
  --min-interval SECS     Minimum seconds between screenshots (default: 10)
  --compute-type TYPE     WhisperX compute: float16, int8, float32 (default: float16)
  --device DEVICE         cuda or cpu (default: cuda)
  --no-paddleocr          Skip EasyOCR text extraction (VLM only)
  --no-vlm                Skip VLM visual description (EasyOCR text only)
  --paddleocr-lang CODE   EasyOCR language code (default: en)

Skip flags (for re-running / resuming):
  --skip-transcribe       Use existing transcript.json
  --skip-ocr              Use existing ocr_results.json
  --skip-frames           Use existing frames/ directory
```

### Examples

```bash
# English video, 20 screenshots for dense content
video-to-context recording.mkv --language en --max-screenshots 20 --min-interval 5

# Game recording (VLM-only — OCR can't read stylized game fonts)
video-to-context recording.mkv --language en --no-paddleocr

# Document/presentation recording (OCR-only for clean text)
video-to-context recording.mkv --language en --no-vlm

# Use smaller Whisper model for faster (less accurate) transcription
video-to-context recording.mkv --whisper-model medium --language en

# Re-run only VLM (skip transcription + frame extraction + OCR)
video-to-context recording.mkv --language en --skip-transcribe --skip-frames

# CPU-only (very slow — not recommended)
video-to-context recording.mkv --device cpu --compute-type int8
```

## Output Format

### VTT File (`output.vtt`)

The VTT interleaves speech transcription and visual context:

```vtt
WEBVTT

NOTE
Video: recording
Generated by video-to-context pipeline

1
00:00:03.286 --> 00:00:06.288
This is ShatteredReachDevLog1.

2
00:00:06.368 --> 00:00:12.173
I'm going to be reviewing a live playtest.

15
00:01:22.632 --> 00:01:23.632
[VISUAL 📷 frame_001]
VISUAL LAYOUT:
1. This is a tactical combat interface from a space-based strategy game.
2. Major visual sections:
   - Left sidebar: Vertical panel with multiple horizontal bars.
   - Center area: Main view showing a hex grid with ship icons and targeting lines.
3. Visual elements:
   - Hexagonal grid overlaying space.
   - Red-outlined hexagons forming a path or formation.
   - Teal targeting lines between ships.
4. Apparent state: Active combat with ships engaged on the hex grid.
```

### Transcript JSON (`transcript.json`)

Raw WhisperX output with word-level timestamps when `--language` is set:

```json
{
  "segments": [
    {
      "start": 3.286,
      "end": 6.288,
      "text": " This is ShatteredReachDevLog1.",
      "words": [
        { "word": "This", "start": 3.29, "end": 3.61, "score": 0.95 },
        { "word": "is", "start": 3.61, "end": 3.89, "score": 0.98 }
      ]
    }
  ]
}
```

## Screenshot Selection Strategy

The pipeline uses a multi-strategy approach to pick meaningful timestamps:

1. **Topic boundaries**: Detects pauses in speech where the gap exceeds 2× the mean gap between segments. These often correspond to scene changes or topic shifts.

2. **Even coverage**: Divides the video into N equal chunks and picks a frame from each, ensuring no long stretch goes undocumented.

3. **Start/end anchors**: Always includes the first spoken segment.

4. **De-duplication**: Enforces a minimum interval (default 10s) between screenshots to avoid clustering.

## OCR Model Quality Notes

### The Hybrid Approach

Traditional OCR engines (EasyOCR, PaddleOCR, Tesseract) **read** text — they detect character shapes and match them. This gives near-zero hallucination but requires clean, recognizable fonts. Vision-Language Models (VLMs) **generate** text descriptions — they understand layout and context but can hallucinate text that isn't there.

The hybrid approach combines both:

- **EasyOCR** extracts text it can confidently read (great for documents, slides, clean UIs)
- **Qwen3-VL** describes what it sees visually (layout, UI elements, game state, diagrams)

### Qwen3-VL-8B-Instruct (4-bit NF4) — **Current default, recommended**

- Fits in 16GB VRAM with 4-bit quantization (~5-6GB actual)
- **Significantly better than Qwen2.5-VL-7B** — no text hallucination when told to focus on layout only
- Correctly identifies: "tactical combat interface", "hexagonal grid", "left sidebar with horizontal bars", "Windows taskbar"
- Understands PC/mobile GUIs natively (visual agent training)
- Expanded OCR: 32 languages, robust in low light/blur/tilt

### EasyOCR — For clean text only

- Near-zero hallucination — reads actual characters
- Works great for: documents, slides, subtitles, clean web pages
- **Fails completely on stylized game UI fonts** — found 0/16 text regions on test video
- Use `--no-vlm` for pure OCR when you know the content is documents

### When to use what

| Content type                   | Recommended flags           |
| ------------------------------ | --------------------------- |
| Game recordings / stylized UI  | `--no-paddleocr` (VLM only) |
| Documents / slides / web pages | `--no-vlm` (OCR only)       |
| Mixed content (default)        | both (hybrid)               |

### Model comparison (same test video)

| Model                    | Output quality                                         | Hallucination                                                  |
| ------------------------ | ------------------------------------------------------ | -------------------------------------------------------------- |
| Qwen2.5-VL-3B (bfloat16) | "Title Bar: Starbound", "Sword: 100"                   | **Severe** — invented game names, fake stats                   |
| Qwen2.5-VL-7B (4-bit)    | "Current Target:", "Turn 6 / 998"                      | **Moderate** — real text but garbled/repetitive on 8/16 frames |
| **Qwen3-VL-8B (4-bit)**  | "Tactical combat interface, hex grid, left sidebar..." | **None** — layout-focused, no fake text                        |

## Resume / Incremental Re-run

The pipeline is designed for resumability:

- **Transcript**: If `transcript.json` exists, transcription is skipped
- **Frames**: If `frames/` directory exists with files, extraction is skipped
- **EasyOCR**: If `paddleocr_results.json` exists, OCR is skipped
- **VLM**: Results are saved incrementally after each frame. If the process crashes, re-running picks up from where it left off
- **Skip flags**: `--skip-transcribe`, `--skip-frames`, `--skip-ocr` to explicitly skip steps

```bash
# After a crash, just re-run the same command — it will resume
video-to-context recording.mkv --language en

# Or skip specific steps
video-to-context recording.mkv --language en --skip-transcribe --skip-frames
```

## Known Issues & Workarounds

| Issue                             | Cause                                              | Workaround                                                                  |
| --------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------- |
| EasyOCR finds no text on game UIs | Stylized/pixel fonts not in training data          | Use `--no-paddleocr` for game recordings                                    |
| CUDA assertion error during VLM   | Numerical instability with float16                 | Pipeline auto-detects bfloat16 + 4-bit quant                                |
| OOM with 8B model                 | Other GPU processes consuming VRAM                 | Close browser/games first, or use `--vlm-model Qwen/Qwen2.5-VL-3B-Instruct` |
| PaddleOCR v3.6 API breaks         | Incompatible with PaddlePaddle GPU                 | Pipeline uses EasyOCR instead                                               |
| WhisperX alignment fails          | Language not supported or auto-detect picked wrong | Specify `--language` explicitly                                             |
| Python 3.14 incompatibility       | WhisperX requires <3.14                            | The venv uses Python 3.11 via `uv`                                          |

## Performance

On the test video (13.5 min, 1280×720 MKV, RTX 4070 Ti SUPER):

| Step                   | Time         | Notes                                           |
| ---------------------- | ------------ | ----------------------------------------------- |
| Audio extraction       | ~3s          | ffmpeg                                          |
| WhisperX transcription | ~30s         | large-v3, float16, batch=16                     |
| WhisperX alignment     | ~15s         | wav2vec2 base, English                          |
| Frame extraction       | ~5s          | 16 frames                                       |
| EasyOCR                | ~20s         | 16 frames (0 results on game UI)                |
| Qwen3-VL-8B (4-bit)    | ~60s         | ~4s per frame                                   |
| VTT generation         | <1s          |                                                 |
| **Total**              | **~2.5 min** | First run; subsequent runs skip completed steps |

## File Locations

| What                    | Path                                |
| ----------------------- | ----------------------------------- |
| Pipeline script         | `~/.local/bin/video-to-context`     |
| Python venv             | `~/.local/share/whisperx-pipeline/` |
| HuggingFace model cache | `~/.cache/huggingface/`             |
| EasyOCR model cache     | `~/.EasyOCR/`                       |
