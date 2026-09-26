"""
Transcription engine built on faster-whisper (CTranslate2).

Provides a high-level TranscriptionEngine class that wraps model loading,
transcription, and result structuring.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

from faster_whisper import WhisperModel


# ---------------------------------------------------------------------------
# Data classes for structured results
# ---------------------------------------------------------------------------

@dataclass
class WordTiming:
    """A single word with its start/end timestamps."""
    word: str
    start: float
    end: float
    probability: float


@dataclass
class Segment:
    """A transcribed segment (typically one sentence or phrase)."""
    id: int
    start: float
    end: float
    text: str
    words: List[WordTiming] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    """Complete transcription output."""
    segments: List[Segment]
    language: str
    language_probability: float
    duration: float            # total audio duration in seconds
    processing_time: float     # wall-clock time for transcription
    model_name: str

    @property
    def full_text(self) -> str:
        """Join all segment texts into one continuous string."""
        return " ".join(seg.text.strip() for seg in self.segments)

    @property
    def speed_ratio(self) -> float:
        """How many times faster than real-time (higher = better)."""
        if self.processing_time == 0:
            return float("inf")
        return self.duration / self.processing_time


# ---------------------------------------------------------------------------
# Available models
# ---------------------------------------------------------------------------

AVAILABLE_MODELS = {
    "tiny":      {"size": "~75 MB",   "description": "Fastest, lowest accuracy"},
    "base":      {"size": "~150 MB",  "description": "Good balance for quick jobs"},
    "small":     {"size": "~500 MB",  "description": "Solid accuracy, moderate speed"},
    "medium":    {"size": "~1.5 GB",  "description": "High accuracy, slower"},
    "large-v3":  {"size": "~3 GB",    "description": "Maximum accuracy"},
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class TranscriptionEngine:
    """
    High-level transcription engine wrapping faster-whisper.

    Usage:
        engine = TranscriptionEngine(model_name="base")
        result = engine.transcribe("interview.mp3")
        print(result.full_text)
    """

    def __init__(
        self,
        model_name: str = "base",
        device: str = "auto",
        compute_type: str = "default",
    ):
        """
        Initialize the transcription engine.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large-v3).
            device: Compute device — "auto", "cpu", or "cuda".
            compute_type: Quantization type — "default", "float16", "int8", etc.
        """
        self.model_name = model_name

        if model_name not in AVAILABLE_MODELS:
            valid = ", ".join(AVAILABLE_MODELS.keys())
            raise ValueError(
                f"Unknown model '{model_name}'. Available: {valid}"
            )

        # Resolve "auto" device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        # Resolve "default" compute type
        if compute_type == "default":
            compute_type = "float16" if device == "cuda" else "int8"

        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def _load_model(self) -> WhisperModel:
        """Lazy-load the model on first use."""
        if self._model is None:
            print(
                f"⏳ Loading model '{self.model_name}' "
                f"(device={self.device}, compute={self.compute_type})...",
                file=sys.stderr,
            )
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            print("✅ Model loaded.", file=sys.stderr)
        return self._model

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to the audio/video file.
            language: ISO 639-1 language code (e.g. "en"). None = auto-detect.
            word_timestamps: Whether to compute word-level timestamps.
            beam_size: Beam search width (higher = more accurate, slower).
            vad_filter: Use Silero VAD to filter out silence (recommended).

        Returns:
            TranscriptionResult with segments, timings, and metadata.
        """
        model = self._load_model()

        print(f"🔊 Transcribing: {audio_path}", file=sys.stderr)
        wall_start = time.perf_counter()

        segments_gen, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
        )

        # Materialize generator into structured data
        segments: List[Segment] = []
        for idx, seg in enumerate(segments_gen):
            words = []
            if seg.words:
                words = [
                    WordTiming(
                        word=w.word.strip(),
                        start=w.start,
                        end=w.end,
                        probability=w.probability,
                    )
                    for w in seg.words
                ]

            segments.append(Segment(
                id=idx + 1,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=words,
            ))

        wall_end = time.perf_counter()
        processing_time = wall_end - wall_start

        result = TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            processing_time=processing_time,
            model_name=self.model_name,
        )

        print(
            f"✅ Done — {len(segments)} segments, "
            f"{result.duration:.1f}s audio in {processing_time:.1f}s "
            f"({result.speed_ratio:.1f}× real-time)",
            file=sys.stderr,
        )

        return result
