import io
import wave
import threading
import logging
import numpy as np
import sounddevice as sd

log = logging.getLogger("VoiceToText")

# A recording is treated as "empty" when its peak short-window RMS stays below
# this normalized level (0..1, same scale as _audio_callback's `level`).
# Tuneable via config ("silence_threshold").
SILENCE_RMS_THRESHOLD = 0.010


def is_silent(wav_data: bytes, threshold: float = SILENCE_RMS_THRESHOLD) -> bool:
    """True if the clip contains no speech (peak windowed RMS below threshold)."""
    if not wav_data:
        return True
    try:
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        if not raw:
            return True
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size == 0:
            return True
        # Peak RMS over 0.1s windows, so a brief utterance buried in mostly
        # silence still registers as speech and is kept.
        win = 1600
        n = (audio.size // win) * win
        if n == 0:
            peak_rms = float(np.sqrt(np.mean(audio ** 2)))
        else:
            frames = audio[:n].reshape(-1, win)
            peak_rms = float(np.sqrt(np.mean(frames ** 2, axis=1)).max())
        return peak_rms < threshold
    except Exception as e:
        log.warning(f"is_silent check failed, assuming non-silent: {e}")
        return False


def trim_silence(wav_data: bytes, sample_rate: int = 16000,
                 threshold: float = SILENCE_RMS_THRESHOLD) -> bytes:
    """Lightweight successor to the old Silero-VAD trim (torch removed).

    Groq Whisper bills a 10s minimum and internally pads short clips, so
    client-side silence *trimming* saves neither cost nor latency. The only
    real value of the old VAD was dropping fully-silent recordings, which
    otherwise make Whisper hallucinate boilerplate (e.g. the infamous
    "ご視聴ありがとうございました"). So we keep the audio intact and merely
    return b"" for silent clips — no torch, no model download, ~0 ms.
    """
    if not wav_data:
        return b""
    if is_silent(wav_data, threshold):
        log.info("Recording detected as silent (RMS gate), skipping.")
        return b""
    return wav_data


class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1, dtype="int16",
                 silence_threshold=SILENCE_RMS_THRESHOLD):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.silence_threshold = silence_threshold
        self._frames = []
        self._recording = False
        self._stream = None
        self._lock = threading.Lock()
        self._level_callback = None

    def set_level_callback(self, callback):
        """Set callback for real-time audio level: callback(level, waveform)"""
        self._level_callback = callback

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _ensure_stream(self):
        """Open the input stream once and keep it warm.

        Opening a fresh sd.InputStream costs ~300-400 ms; doing it on every
        key press is the bulk of the 'lag before it turns on'. We open once
        and gate capture with self._recording (see _audio_callback), so every
        subsequent start() is instant.
        """
        if self._stream is None:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()

    def arm(self):
        """Pre-open the mic so the FIRST recording is instant too. Never raises."""
        with self._lock:
            try:
                self._ensure_stream()
            except Exception as e:
                log.warning(f"Mic pre-arm failed: {e}")

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._frames = []
            try:
                self._ensure_stream()  # instant if already warm
            except Exception as e:
                log.error(f"Failed to open mic stream: {e}")
                return
            self._recording = True

    def stop(self) -> bytes:
        with self._lock:
            if not self._recording:
                return b""
            self._recording = False
            # Keep the stream OPEN (warm) so the next start() has zero latency.
            wav_data = self._build_wav()
            if wav_data:
                # Drop fully-silent recordings (lightweight RMS gate, no torch)
                wav_data = trim_silence(wav_data, self.sample_rate, self.silence_threshold)
            return wav_data

    def close(self):
        """Fully release the warm mic stream (call on app shutdown)."""
        with self._lock:
            self._recording = False
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            self._frames.append(indata.copy())
            if self._level_callback:
                audio = indata[:, 0].astype(np.float32)
                rms = np.sqrt(np.mean(audio ** 2)) / 32768.0
                level = min(1.0, rms * 5.0)
                step = max(1, len(audio) // 40)
                waveform = (audio[::step] / 32768.0).tolist()
                try:
                    self._level_callback(level, waveform)
                except Exception:
                    pass

    def _build_wav(self) -> bytes:
        if not self._frames:
            return b""
        audio_data = np.concatenate(self._frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        return buf.getvalue()

    def get_duration(self) -> float:
        if not self._frames:
            return 0.0
        total_frames = sum(f.shape[0] for f in self._frames)
        return total_frames / self.sample_rate
