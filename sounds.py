"""Lightweight UI sound effects (Windows winsound, no extra dependencies).

Short tones are synthesized once with numpy into small WAV files under the app
data dir, then played asynchronously via winsound.PlaySound. Falls back to
winsound.MessageBeep, and is fully import-safe on any OS (winsound guarded).

States map to musical cues so the user can tell what happened without looking:
  start  rising  = now listening
  stop   falling = recording stopped
  done   bright  = text inserted successfully
  empty  low     = nothing was captured
"""
import os
import sys
import wave
import logging
import threading

import numpy as np

log = logging.getLogger("VoiceToText")

try:
    import winsound  # Windows only
except Exception:  # pragma: no cover - non-Windows / headless
    winsound = None

_enabled = True
_paths = {}          # name -> wav file path
_lock = threading.Lock()

SR = 16000
VOLUME = 0.22

# name -> list of (frequency_hz, duration_seconds) segments played in order
_DEFS = {
    "start": [(660, 0.07), (990, 0.09)],
    "stop": [(880, 0.07), (587, 0.09)],
    "done": [(988, 0.06), (1319, 0.10)],
    "empty": [(440, 0.10), (294, 0.12)],
}


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", os.path.expanduser("~")))
        d = os.path.join(base, "VoiceToText")
    else:
        d = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(d, exist_ok=True)
    return d


def _synth(segments):
    """Synthesize a short int16 mono signal with click-free fades."""
    parts = []
    fade = max(1, int(SR * 0.006))
    for freq, dur in segments:
        n = max(2 * fade, int(SR * dur))
        t = np.arange(n) / SR
        tone = np.sin(2 * np.pi * freq * t)
        env = np.ones(n)
        env[:fade] = np.linspace(0.0, 1.0, fade)
        env[-fade:] = np.linspace(1.0, 0.0, fade)
        parts.append(tone * env)
    sig = np.concatenate(parts) if parts else np.zeros(1)
    sig = (sig * VOLUME * 32767.0).clip(-32768, 32767).astype("<i2")
    return sig


def _ensure_files():
    with _lock:
        if _paths:
            return
        try:
            sounds_dir = os.path.join(_app_dir(), "sounds")
            os.makedirs(sounds_dir, exist_ok=True)
            for name, segs in _DEFS.items():
                path = os.path.join(sounds_dir, f"{name}.wav")
                if not os.path.exists(path):
                    data = _synth(segs)
                    with wave.open(path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(SR)
                        wf.writeframes(data.tobytes())
                _paths[name] = path
        except Exception as e:
            log.warning(f"Sound file generation failed: {e}")


def prewarm():
    """Generate the WAV files in the background so the first cue has no delay."""
    threading.Thread(target=_ensure_files, daemon=True).start()


def set_enabled(enabled: bool):
    global _enabled
    _enabled = bool(enabled)


def play(name: str):
    """Play a named sound asynchronously. Never raises."""
    if not _enabled or winsound is None:
        return
    try:
        _ensure_files()
        path = _paths.get(name)
        if path and os.path.exists(path):
            winsound.PlaySound(
                path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
            )
        else:
            winsound.MessageBeep(winsound.MB_OK)
    except Exception as e:
        log.warning(f"play sound '{name}' failed: {e}")
