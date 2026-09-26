"""
Microphone recorder using sounddevice + soundfile.

Records audio from the default input device until the user presses Ctrl+C.
"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


class MicrophoneRecorder:
    """
    Records audio from the system microphone.

    Usage:
        recorder = MicrophoneRecorder(sample_rate=16000)
        recorder.record("output.wav")   # blocks until Ctrl+C
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
    ):
        """
        Args:
            sample_rate: Audio sample rate in Hz. 16000 is standard for speech.
            channels: Number of audio channels (1 = mono, recommended).
            dtype: Sample data type.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._stop_event = threading.Event()

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            print(f"⚠️  Audio status: {status}", file=sys.stderr)
        self._frames.append(indata.copy())

    def record(
        self,
        output_path: str,
        max_duration: Optional[float] = None,
    ) -> Path:
        """
        Record audio from the default microphone and save to a WAV file.

        Blocks until the user presses Ctrl+C or max_duration is reached.

        Args:
            output_path: Path where the WAV file will be saved.
            max_duration: Maximum recording duration in seconds (None = unlimited).

        Returns:
            Path to the saved audio file.
        """
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        self._frames = []
        self._stop_event.clear()
        self._recording = True

        import time

        print(
            f"🎙️  Recording (rate={self.sample_rate}Hz, "
            f"channels={self.channels}) — press Ctrl+C to stop",
            file=sys.stderr,
        )

        start_time = time.time()
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
            ):
                while not self._stop_event.is_set():
                    if max_duration and (time.time() - start_time) >= max_duration:
                        print(f"\n⏱️  Max duration ({max_duration}s) reached.", file=sys.stderr)
                        break
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n🛑 Stopping recording...", file=sys.stderr)
        except sd.PortAudioError as e:
            print(
                f"❌ Microphone error: {e}\n"
                "   Make sure a microphone is connected and accessible.",
                file=sys.stderr,
            )
            raise
        finally:
            self._recording = False

        if not self._frames:
            print("⚠️  No audio captured.", file=sys.stderr)
            return output

        # Concatenate all captured frames and write to file
        audio_data = np.concatenate(self._frames, axis=0)
        duration = len(audio_data) / self.sample_rate

        sf.write(str(output), audio_data, self.sample_rate)

        print(
            f"💾 Saved {duration:.1f}s of audio → {output}",
            file=sys.stderr,
        )

        return output


def list_audio_devices() -> None:
    """Print available audio input devices."""
    print("\n🔌 Available audio input devices:\n")
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            marker = " ← default" if idx == sd.default.device[0] else ""
            print(
                f"  [{idx}] {dev['name']}  "
                f"(inputs={dev['max_input_channels']}, "
                f"rate={dev['default_samplerate']:.0f}Hz)"
                f"{marker}"
            )
    print()
