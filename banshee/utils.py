"""
Utility helpers for file discovery, validation, and formatting.
"""

import os
from pathlib import Path
from typing import List

# Audio/video extensions that faster-whisper (via FFmpeg) can decode
SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac",  # audio
    ".mp4", ".mkv", ".avi", ".mov", ".webm",                   # video
}


def is_audio_file(filepath: str) -> bool:
    """Check if a file has a supported audio/video extension."""
    return Path(filepath).suffix.lower() in SUPPORTED_EXTENSIONS


def discover_audio_files(directory: str) -> List[str]:
    """
    Recursively find all supported audio/video files in a directory.

    Returns a sorted list of absolute paths.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    found = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            full_path = os.path.join(root, fname)
            if is_audio_file(full_path):
                found.append(full_path)

    return sorted(found)


def validate_audio_path(filepath: str) -> Path:
    """
    Validate that an audio file exists and has a supported extension.

    Returns:
        Resolved Path object.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If extension is not supported.
    """
    path = Path(filepath).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not is_audio_file(str(path)):
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type '{path.suffix}'. "
            f"Supported: {supported}"
        )

    return path


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to HH:MM:SS.mmm timestamp string.

    Example:
        >>> format_timestamp(3723.456)
        '01:02:03.456'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_timestamp_srt(seconds: float) -> str:
    """
    Convert seconds to SRT-style timestamp (comma separator for millis).

    Example:
        >>> format_timestamp_srt(3723.456)
        '01:02:03,456'
    """
    return format_timestamp(seconds).replace(".", ",")


def ensure_directory(path: str) -> Path:
    """Create directory (and parents) if it doesn't exist. Returns the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def human_readable_size(size_bytes: int) -> str:
    """Convert byte count to human-readable string (e.g. '1.5 GB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
