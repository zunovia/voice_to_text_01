import io
import wave
import threading
import logging
import numpy as np
import sounddevice as sd

log = logging.getLogger("VoiceToText")

# Lazy-load Silero VAD to avoid slow startup
_vad_model = None


def _get_vad_model():
    global _vad_model
    if _vad_model is None:
        try:
            import torch
            torch.set_num_threads(1)
            from silero_vad import load_silero_vad
            _vad_model = load_silero_vad()
            log.info("Silero VAD loaded successfully")
        except Exception as e:
            log.warning(f"Silero VAD not available, skipping VAD: {e}")
    return _vad_model


def trim_silence(wav_data: bytes, sample_rate: int = 16000) -> bytes:
    """Remove silence from WAV using Silero VAD. Returns trimmed WAV bytes."""
    model = _get_vad_model()
    if model is None:
        return wav_data

    try:
        import torch
        from silero_vad import get_speech_timestamps, collect_chunks

        # Parse WAV to numpy
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
            audio_np = np.frombuffer(raw, dtype=np.int16)

        # Convert to float32 tensor for Silero
        audio_tensor = torch.from_numpy(audio_np.astype(np.float32) / 32768.0)

        # Get speech timestamps
        speech_timestamps = get_speech_timestamps(
            audio_tensor, model,
            sampling_rate=sample_rate,
            threshold=0.3,
            min_speech_duration_ms=100,
            min_silence_duration_ms=300,
        )

        if not speech_timestamps:
            log.info("VAD: No speech detected")
            return b""

        # Collect speech chunks with small padding
        speech_audio = collect_chunks(speech_timestamps, audio_tensor)

        # Convert back to int16 WAV
        speech_int16 = (speech_audio.numpy() * 32768.0).clip(-32768, 32767).astype(np.int16)

        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(speech_int16.tobytes())

        trimmed_size = len(out_buf.getvalue())
        original_size = len(wav_data)
        reduction = (1 - trimmed_size / original_size) * 100 if original_size > 0 else 0
        log.info(f"VAD: {original_size} -> {trimmed_size} bytes ({reduction:.0f}% reduction)")

        return out_buf.getvalue()

    except Exception as e:
        log.warning(f"VAD processing failed, using original audio: {e}")
        return wav_data


class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1, dtype="int16"):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
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

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()

    def stop(self) -> bytes:
        with self._lock:
            if not self._recording:
                return b""
            self._recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            wav_data = self._build_wav()
            if wav_data:
                # Apply VAD to trim silence
                wav_data = trim_silence(wav_data, self.sample_rate)
            return wav_data

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
