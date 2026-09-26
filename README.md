# 🎤 Banshee — Speech-to-Text Toolkit

[![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![faster-whisper](https://img.shields.io/badge/engine-faster--whisper-blueviolet?style=flat-square)](https://github.com/SYSTRAN/faster-whisper)

**Banshee** is a full-featured, offline speech-to-text toolkit powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2). It runs entirely on your machine — no API keys, no cloud, no data leaving your hardware.

> Unlike basic Whisper wrappers, Banshee provides a modular CLI with **live microphone recording**, **batch & single file transcription**, **multi-format export** (TXT, SRT, JSON, VTT), and **word-level timestamps** — all from one command.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌐 **Web GUI** | Beautiful, premium local web interface for easy drag-and-drop usage |
| 🎙️ **Live Recording** | Record from your microphone and transcribe in one step |
| 📂 **File Transcription** | Transcribe any audio/video file (mp3, wav, m4a, flac, mp4, mkv…) |
| 📦 **Batch Mode** | Transcribe every audio file in a directory at once |
| 📝 **Multi-Format Export** | Output as plain text, SRT subtitles, WebVTT, or structured JSON |
| ⏱️ **Word-Level Timestamps** | Precise per-word timing for subtitle generation |
| 🌍 **Language Detection** | Auto-detect or manually specify source language |
| 🚀 **CTranslate2 Engine** | 4× faster than OpenAI Whisper with lower memory footprint |
| 🧩 **Modular Architecture** | Clean separation: engine, recorder, exporter, web, CLI |

---

## 📋 Requirements

- **Python 3.9+**
- **FFmpeg** (for audio decoding)
- ~1–3 GB disk space (depending on model size)

---

## 🛠️ Install

### 1. Clone & install

```bash
git clone https://github.com/AbizarDholkawala/Banshee
cd Banshee
pip install -e .
```

### 2. Install FFmpeg

```bash
# Windows (winget)
winget install FFmpeg

# Windows (Chocolatey)
choco install ffmpeg

# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### 3. Verify

```bash
ffmpeg -version
banshee --help
```

---

## 🚀 Usage

### 🌐 Launch the Web GUI (Recommended)

Banshee includes a premium, beautifully designed local web interface. You can drag and drop files, record from your browser's microphone, adjust settings visually, and copy/download transcripts.

```bash
banshee web
```
*Opens a local server at `http://127.0.0.1:7860`*

---

### 💻 Command Line Interface

If you prefer the terminal, Banshee's CLI provides powerful options:

#### Transcribe a file

```bash
# Basic transcription (prints to stdout)
banshee transcribe audio.mp3

# Save as SRT subtitles
banshee transcribe interview.wav --format srt --output interview.srt

# Use a larger model for better accuracy
banshee transcribe lecture.m4a --model medium --format json --output lecture.json

# Specify language (skip auto-detection)
banshee transcribe spanish_audio.mp3 --language es
```

### Record from microphone & transcribe

```bash
# Record until you press Ctrl+C, then transcribe
banshee record --output recording.wav

# Record and immediately transcribe
banshee record --transcribe --format txt --output notes.txt
```

### Batch transcribe a directory

```bash
# Transcribe all audio files in a folder
banshee batch ./interviews/ --format srt --output-dir ./transcripts/
```

### List available models

```bash
banshee models
```

---

## 🧠 Models

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `tiny` | ~75 MB | ⚡⚡⚡⚡ | ★★ | Quick drafts, testing |
| `base` | ~150 MB | ⚡⚡⚡ | ★★★ | General use (default) |
| `small` | ~500 MB | ⚡⚡ | ★★★★ | Good balance |
| `medium` | ~1.5 GB | ⚡ | ★★★★★ | High accuracy |
| `large-v3` | ~3 GB | 🐢 | ★★★★★★ | Maximum accuracy |

---

## 📂 Project Structure

```text
banshee/
├── banshee/
│   ├── static/              # CSS, JS, and Favicon for Web GUI
│   ├── templates/           # HTML templates for Web GUI
│   ├── __init__.py          # Package init + version
│   ├── cli.py               # CLI entry point (argparse)
│   ├── engine.py            # Transcription engine (faster-whisper)
│   ├── exporter.py          # Multi-format export (TXT/SRT/VTT/JSON)
│   ├── recorder.py          # Microphone recording (sounddevice)
│   ├── utils.py             # Helpers (file discovery, validation)
│   └── web.py               # Flask application server
├── setup.py                 # Package configuration
├── requirements.txt         # Dependencies
└── README.md                # This file
```

---
