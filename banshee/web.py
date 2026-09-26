"""
Banshee Web UI — Flask-based graphical interface for speech-to-text.

Serves a single-page app on localhost with API endpoints for transcription.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request, send_file

from banshee.engine import AVAILABLE_MODELS, TranscriptionEngine
from banshee.exporter import FORMATS

# ---------------------------------------------------------------------------
# Flask app setup
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).parent
_TEMPLATE_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"

app = Flask(
    __name__,
    template_folder=str(_TEMPLATE_DIR),
    static_folder=str(_STATIC_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB upload limit

# Store for active engine (lazy-loaded, cached per model name)
_engines: dict[str, TranscriptionEngine] = {}


def _get_engine(model_name: str, device: str = "auto") -> TranscriptionEngine:
    """Get or create a cached engine for the given model."""
    key = f"{model_name}:{device}"
    if key not in _engines:
        _engines[key] = TranscriptionEngine(model_name=model_name, device=device)
    return _engines[key]


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main web UI."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes — API
# ---------------------------------------------------------------------------

@app.route("/api/models", methods=["GET"])
def api_models():
    """Return available Whisper models."""
    return jsonify(AVAILABLE_MODELS)


@app.route("/api/formats", methods=["GET"])
def api_formats():
    """Return available export formats."""
    return jsonify(list(FORMATS.keys()))


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """
    Transcribe an uploaded audio/video file.

    Form data:
        file:         The audio/video file (multipart)
        model:        Whisper model name (default: "base")
        language:     Language code or "" for auto-detect
        format:       Output format (txt, srt, vtt, json)
        beam_size:    Beam search width (default: 5)
        device:       Compute device (auto, cpu, cuda)
    """
    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Read settings
    model_name = request.form.get("model", "base")
    language = request.form.get("language", "").strip() or None
    output_format = request.form.get("format", "txt")
    beam_size = int(request.form.get("beam_size", "5"))
    device = request.form.get("device", "auto")

    # Save uploaded file to temp
    suffix = Path(uploaded.filename).suffix
    temp_dir = Path(tempfile.gettempdir()) / "banshee_uploads"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}{suffix}"

    try:
        uploaded.save(str(temp_path))

        # Transcribe
        engine = _get_engine(model_name, device)
        result = engine.transcribe(
            str(temp_path),
            language=language,
            beam_size=beam_size,
        )

        # Build response
        segments_data = []
        for seg in result.segments:
            seg_data = {
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
            segments_data.append(seg_data)

        # Generate formatted output
        import io
        from banshee.exporter import FORMATS as _FMT

        buf = io.StringIO()
        _FMT[output_format](result, buf)
        formatted_output = buf.getvalue()

        response = {
            "success": True,
            "metadata": {
                "language": result.language,
                "language_probability": round(result.language_probability, 4),
                "duration": round(result.duration, 2),
                "processing_time": round(result.processing_time, 2),
                "speed_ratio": round(result.speed_ratio, 1),
                "model": result.model_name,
                "filename": uploaded.filename,
            },
            "full_text": result.full_text,
            "segments": segments_data,
            "formatted_output": formatted_output,
            "format": output_format,
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


# ---------------------------------------------------------------------------
# Launch helper
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 7860, debug: bool = False):
    """Start the Flask development server."""
    print(f"\n🎤 Banshee Web UI starting...", file=sys.stderr)
    print(f"🌐 Open http://{host}:{port} in your browser (Press Ctrl+C to stop)\n", file=sys.stderr)
    try:
        app.run(host=host, port=port, debug=debug)
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Banshee Web UI stopped.", file=sys.stderr)
        os._exit(0)

