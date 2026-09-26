"""
Banshee CLI — command-line interface for the speech-to-text toolkit.

Subcommands:
    transcribe  — Transcribe a single audio/video file
    record      — Record from microphone (optionally transcribe)
    batch       — Transcribe all audio files in a directory
    models      — List available Whisper models
    devices     — List available audio input devices
    web         — Launch the graphical web interface
"""

from __future__ import annotations

import argparse
import os
import sys

from banshee import __version__, __app_name__
from banshee.engine import AVAILABLE_MODELS, TranscriptionEngine
from banshee.exporter import export, get_supported_formats
from banshee.recorder import MicrophoneRecorder, list_audio_devices
from banshee.utils import discover_audio_files, validate_audio_path, ensure_directory


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
    ____                   __             
   / __ ) ____ _ ____   ____ / /_   ___   ___
  / __  |/ __ `// __ \ / __ / __ \ / _ \ / _ \
 / /_/ // /_/ // / / /(__  ) / / //  __//  __/
/______/ \__,_//_/ /_//____/_/ /_/ \___/ \___/
        Offline Speech-to-Text Toolkit
"""


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_transcribe(args: argparse.Namespace) -> int:
    """Handle the 'transcribe' subcommand."""
    try:
        audio_path = validate_audio_path(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    try:
        engine = TranscriptionEngine(
            model_name=args.model,
            device=args.device,
            compute_type=args.compute_type,
        )
        result = engine.transcribe(
            str(audio_path),
            language=args.language,
            beam_size=args.beam_size,
        )
        export(result, fmt=args.format, output_path=args.output)
        return 0

    except Exception as e:
        print(f"❌ Transcription failed: {e}", file=sys.stderr)
        return 1


def cmd_record(args: argparse.Namespace) -> int:
    """Handle the 'record' subcommand."""
    output_path = args.output or "recording.wav"

    try:
        recorder = MicrophoneRecorder(
            sample_rate=args.sample_rate,
            channels=1,
        )
        saved_path = recorder.record(
            output_path,
            max_duration=args.max_duration,
        )
    except Exception as e:
        print(f"❌ Recording failed: {e}", file=sys.stderr)
        return 1

    # Optionally transcribe the recording immediately
    if args.transcribe:
        try:
            engine = TranscriptionEngine(
                model_name=args.model,
                device=args.device,
                compute_type=args.compute_type,
            )
            result = engine.transcribe(
                str(saved_path),
                language=args.language,
            )
            export(result, fmt=args.format, output_path=args.transcript_output)
        except Exception as e:
            print(f"❌ Transcription failed: {e}", file=sys.stderr)
            return 1

    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Handle the 'batch' subcommand."""
    try:
        files = discover_audio_files(args.directory)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if not files:
        print(f"⚠️  No audio files found in '{args.directory}'", file=sys.stderr)
        return 0

    print(f"📦 Found {len(files)} audio file(s) to transcribe.\n", file=sys.stderr)

    output_dir = None
    if args.output_dir:
        output_dir = ensure_directory(args.output_dir)

    engine = TranscriptionEngine(
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
    )

    errors = 0
    for i, filepath in enumerate(files, 1):
        print(
            f"\n{'─' * 60}\n"
            f"[{i}/{len(files)}] {filepath}",
            file=sys.stderr,
        )
        try:
            result = engine.transcribe(
                filepath,
                language=args.language,
            )
            out_path = None
            if output_dir:
                from pathlib import Path
                stem = Path(filepath).stem
                ext = args.format if args.format != "txt" else "txt"
                out_path = str(output_dir / f"{stem}.{ext}")

            export(result, fmt=args.format, output_path=out_path)

        except Exception as e:
            print(f"❌ Failed: {e}", file=sys.stderr)
            errors += 1

    print(
        f"\n{'═' * 60}\n"
        f"📊 Batch complete: {len(files) - errors} succeeded, "
        f"{errors} failed.\n",
        file=sys.stderr,
    )
    return 1 if errors else 0


def cmd_models(args: argparse.Namespace) -> int:
    """Handle the 'models' subcommand."""
    print("\n🧠 Available Whisper models:\n")
    print(f"  {'Model':<12} {'Size':<12} {'Description'}")
    print(f"  {'─' * 12} {'─' * 12} {'─' * 40}")
    for name, info in AVAILABLE_MODELS.items():
        print(f"  {name:<12} {info['size']:<12} {info['description']}")
    print()
    return 0


def cmd_devices(args: argparse.Namespace) -> int:
    """Handle the 'devices' subcommand."""
    list_audio_devices()
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    """Handle the 'web' subcommand — launch the graphical UI."""
    from banshee.web import run_server
    run_server(host=args.host, port=args.port, debug=args.debug)
    return 0


# ---------------------------------------------------------------------------
# Shared argument helpers
# ---------------------------------------------------------------------------

def _add_model_args(parser: argparse.ArgumentParser) -> None:
    """Add model-related arguments to a parser."""
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=list(AVAILABLE_MODELS.keys()),
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Compute device (default: auto)",
    )
    parser.add_argument(
        "--compute-type",
        default="default",
        help="CTranslate2 compute type (default, float16, int8, etc.)",
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        help="Language code (e.g. 'en', 'es'). Auto-detect if omitted.",
    )


def _add_format_args(parser: argparse.ArgumentParser) -> None:
    """Add format/output arguments to a parser."""
    parser.add_argument(
        "--format", "-f",
        default="txt",
        choices=get_supported_formats(),
        help="Output format (default: txt)",
    )


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the complete argument parser."""
    parser = argparse.ArgumentParser(
        prog=__app_name__,
        description="🎤 Banshee — Offline speech-to-text toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Run 'banshee <command> --help' for details.",
    )

    # --- transcribe ---
    p_transcribe = subparsers.add_parser(
        "transcribe",
        help="Transcribe a single audio/video file",
        description="Transcribe one audio or video file to text.",
    )
    p_transcribe.add_argument(
        "file",
        help="Path to audio/video file",
    )
    p_transcribe.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (prints to stdout if omitted)",
    )
    p_transcribe.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam search width (default: 5)",
    )
    _add_model_args(p_transcribe)
    _add_format_args(p_transcribe)
    p_transcribe.set_defaults(func=cmd_transcribe)

    # --- record ---
    p_record = subparsers.add_parser(
        "record",
        help="Record from microphone (optionally transcribe)",
        description="Record audio from the system microphone.",
    )
    p_record.add_argument(
        "--output", "-o",
        default=None,
        help="WAV output path (default: recording.wav)",
    )
    p_record.add_argument(
        "--max-duration",
        type=float,
        default=None,
        help="Max recording duration in seconds",
    )
    p_record.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Sample rate in Hz (default: 16000)",
    )
    p_record.add_argument(
        "--transcribe", "-t",
        action="store_true",
        help="Immediately transcribe after recording",
    )
    p_record.add_argument(
        "--transcript-output",
        default=None,
        help="Transcript output file path (stdout if omitted)",
    )
    _add_model_args(p_record)
    _add_format_args(p_record)
    p_record.set_defaults(func=cmd_record)

    # --- batch ---
    p_batch = subparsers.add_parser(
        "batch",
        help="Transcribe all audio files in a directory",
        description="Batch-transcribe every supported file in a directory.",
    )
    p_batch.add_argument(
        "directory",
        help="Directory containing audio/video files",
    )
    p_batch.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output files (stdout if omitted)",
    )
    _add_model_args(p_batch)
    _add_format_args(p_batch)
    p_batch.set_defaults(func=cmd_batch)

    # --- models ---
    p_models = subparsers.add_parser(
        "models",
        help="List available Whisper models",
    )
    p_models.set_defaults(func=cmd_models)

    # --- devices ---
    p_devices = subparsers.add_parser(
        "devices",
        help="List available audio input devices",
    )
    p_devices.set_defaults(func=cmd_devices)

    # --- web ---
    p_web = subparsers.add_parser(
        "web",
        help="Launch the graphical web interface",
        description="Start a local web server with a beautiful GUI for transcription.",
    )
    p_web.add_argument(
        "--port", "-p",
        type=int,
        default=7860,
        help="Port to serve on (default: 7860)",
    )
    p_web.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    p_web.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode (auto-reload on code changes)",
    )
    p_web.set_defaults(func=cmd_web)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        print(BANNER)
        parser.print_help()
        sys.exit(0)

    try:
        exit_code = args.func(args)
        sys.exit(exit_code)
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Process terminated.", file=sys.stderr)
        os._exit(0)


if __name__ == "__main__":
    main()
