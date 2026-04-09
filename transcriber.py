import io
import json
import logging
import time
import httpx
from groq import Groq

log = logging.getLogger("VoiceToText")

CLEANUP_PROMPT = """以下の音声書き起こしテキストを修正してください。

ルール:
- 句読点（。、）を正確に追加してください
- 「えー」「あの」「うーん」などのフィラーを除去してください
- 言い直しや繰り返しを除去してください
- 自然な書き言葉に整えてください
- 意味は変えないでください
- テキストのみを出力。説明や注釈は不要です

テキスト:
"""


class Transcriber:
    def __init__(self, api_key: str, gemini_api_key: str = ""):
        self.api_key = api_key
        self.gemini_api_key = gemini_api_key
        self._groq = Groq(api_key=api_key)
        self._http = httpx.Client(http2=True, timeout=15.0) if gemini_api_key else None

    def transcribe(self, wav_data: bytes) -> str:
        if not wav_data:
            return ""

        # Step 1: Fast transcription via Groq Whisper (~0.3s)
        t0 = time.perf_counter()
        raw_text = self._groq_transcribe(wav_data)
        t1 = time.perf_counter()
        log.info(f"Groq: {t1 - t0:.1f}s -> {raw_text}")

        if not raw_text:
            return ""

        # Step 2: Cleanup via Gemini (punctuation, formatting) (~1s)
        if self.gemini_api_key:
            try:
                cleaned = self._gemini_cleanup(raw_text)
                t2 = time.perf_counter()
                log.info(f"Gemini cleanup: {t2 - t1:.1f}s -> {cleaned}")
                if cleaned:
                    return cleaned
            except Exception as e:
                log.warning(f"Gemini cleanup failed, using raw: {e}")

        return raw_text

    def _groq_transcribe(self, wav_data: bytes) -> str:
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "recording.wav"

        result = self._groq.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            language="ja",
            response_format="text",
            temperature=0.0,
        )
        return result.strip() if result else ""

    def _gemini_cleanup(self, text: str) -> str:
        if not text or not self.gemini_api_key:
            return text

        body = {
            "contents": [{"parts": [{"text": CLEANUP_PROMPT + text}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 2048,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={self.gemini_api_key}"
        resp = self._http.post(url, json=body)
        resp.raise_for_status()

        candidates = resp.json().get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    return part["text"].strip()
        return text

    def update_api_key(self, api_key: str):
        self.api_key = api_key
        self._groq = Groq(api_key=api_key)

    def __del__(self):
        try:
            if self._http:
                self._http.close()
        except Exception:
            pass
