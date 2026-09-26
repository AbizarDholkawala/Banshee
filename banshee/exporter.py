"""
Multi-format exporter for transcription results.

Supports: TXT, SRT, VTT (WebVTT), JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, TextIO

from banshee.engine import TranscriptionResult
from banshee.utils import format_timestamp, format_timestamp_srt


# ---------------------------------------------------------------------------
# Format writers
# ---------------------------------------------------------------------------

def _write_txt(result: TranscriptionResult, fp: TextIO) -> None:
    """Write plain text (one segment per line)."""
    for seg in result.segments:
        fp.write(seg.text.strip() + "\n")


def _write_srt(result: TranscriptionResult, fp: TextIO) -> None:
    """
    Write SRT subtitle format.

    Example output:
        1
        00:00:00,000 --> 00:00:03,500
        Hello, this is a test.

        2
        00:00:03,500 --> 00:00:07,200
        This is the second line.
    """
    for seg in result.segments:
        fp.write(f"{seg.id}\n")
        fp.write(
            f"{format_timestamp_srt(seg.start)} --> "
            f"{format_timestamp_srt(seg.end)}\n"
        )
        fp.write(seg.text.strip() + "\n")
        fp.write("\n")


def _write_vtt(result: TranscriptionResult, fp: TextIO) -> None:
    """
    Write WebVTT subtitle format.

    Example output:
        WEBVTT

        00:00:00.000 --> 00:00:03.500
        Hello, this is a test.

        00:00:03.500 --> 00:00:07.200
        This is the second line.
    """
    fp.write("WEBVTT\n\n")
    for seg in result.segments:
        fp.write(
            f"{format_timestamp(seg.start)} --> "
            f"{format_timestamp(seg.end)}\n"
        )
        fp.write(seg.text.strip() + "\n")
        fp.write("\n")


def _write_json(result: TranscriptionResult, fp: TextIO) -> None:
    """
    Write structured JSON with full metadata.

    Includes: metadata, segments with word-level timestamps.
    """
    output = {
        "metadata": {
            "language": result.language,
            "language_probability": round(result.language_probability, 4),
            "duration_seconds": round(result.duration, 3),
            "processing_time_seconds": round(result.processing_time, 3),
            "speed_ratio": round(result.speed_ratio, 2),
            "model": result.model_name,
        },
        "full_text": result.full_text,
        "segments": [
            {
                "id": seg.id,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": [
                    {
                        "word": w.word,
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "confidence": round(w.probability, 4),
                    }
                    for w in seg.words
                ],
            }
            for seg in result.segments
        ],
    }
    json.dump(output, fp, indent=2, ensure_ascii=False)
    fp.write("\n")


# ---------------------------------------------------------------------------
# Format registry
# ---------------------------------------------------------------------------

FORMATS = {
    "txt": _write_txt,
    "srt": _write_srt,
    "vtt": _write_vtt,
    "json": _write_json,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export(
    result: TranscriptionResult,
    fmt: str = "txt",
    output_path: Optional[str] = None,
) -> None:
    """
    Export a TranscriptionResult to the given format.

    Args:
        result: The transcription result to export.
        fmt: Output format — "txt", "srt", "vtt", or "json".
        output_path: File path to write to. If None, writes to stdout.

    Raises:
        ValueError: If the format is not supported.
    """
    fmt = fmt.lower().strip()
    if fmt not in FORMATS:
        supported = ", ".join(FORMATS.keys())
        raise ValueError(f"Unknown format '{fmt}'. Supported: {supported}")

    writer = FORMATS[fmt]

    if output_path:
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fp:
            writer(result, fp)
        print(f"📄 Saved → {path}", file=sys.stderr)
    else:
        writer(result, sys.stdout)


def get_supported_formats() -> list[str]:
    """Return list of supported export format names."""
    return list(FORMATS.keys())
