import io
import logging
import time
import httpx
from groq import Groq

log = logging.getLogger("VoiceToText")

CLEANUP_PROMPT = """音声書き起こしテキストの整形のみを行ってください。

【絶対厳守ルール】
- 入力テキストの意味を変えない
- 新しい文や言葉を絶対に追加しない
- 質問への回答や解釈を絶対に書かない
- 修正後のテキストのみを出力する（説明・注釈・コメント一切不要）

【整形ルール】
- 句読点（。、）を適切に追加する
- 音声コマンドを変換: 「かっこ」→（、「かっことじ」→）、「かぎかっこ」→「、「かぎかっことじ」→」、「すみかっこ」→【、「すみかっことじ」→】、「エンター」→改行、「改行」→改行、「まる」→。、「てん」→、
- 「えー」「あの」「うーん」などのフィラーを除去する
- 明らかな言い直し・繰り返しを除去する
- 自然な書き言葉に整える"""


class Transcriber:
    def __init__(self, api_key: str, gemini_api_key: str = "",
                 llm_provider: str = "groq",
                 groq_llm_model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.gemini_api_key = gemini_api_key
        self.llm_provider = llm_provider
        self.groq_llm_model = groq_llm_model
        self._groq = Groq(api_key=api_key)
        self._http = httpx.Client(http2=True, timeout=15.0) if gemini_api_key else None

    def transcribe(self, wav_data: bytes, use_cleanup: bool = False) -> str:
        if not wav_data:
            return ""

        # Step 1: Fast transcription via Groq Whisper (~0.3s)
        t0 = time.perf_counter()
        raw_text = self._groq_transcribe(wav_data)
        t1 = time.perf_counter()
        log.info(f"Groq: {t1 - t0:.1f}s -> {raw_text}")

        if not raw_text:
            return ""

        # Step 2: LLM cleanup (punctuation, formatting)
        if use_cleanup:
            if self.llm_provider == "gemini" and self.gemini_api_key:
                try:
                    cleaned = self._gemini_cleanup(raw_text)
                    t2 = time.perf_counter()
                    log.info(f"Gemini cleanup: {t2 - t1:.1f}s -> {cleaned}")
                    if cleaned:
                        return cleaned
                except Exception as e:
                    log.warning(f"Gemini cleanup failed, using raw: {e}")
            else:
                try:
                    cleaned = self._groq_cleanup(raw_text)
                    t2 = time.perf_counter()
                    log.info(f"Groq LLM cleanup: {t2 - t1:.1f}s -> {cleaned}")
                    if cleaned:
                        return cleaned
                except Exception as e:
                    log.warning(f"Groq LLM cleanup failed, using raw: {e}")

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

    def _groq_cleanup(self, text: str) -> str:
        try:
            # Limit max_tokens to ~1.5x input length to prevent repetition
            input_token_estimate = len(text) * 2  # rough: 1 Japanese char ~ 2 tokens
            max_out = max(64, min(input_token_estimate * 2, 512))

            response = self._groq.chat.completions.create(
                model=self.groq_llm_model,
                messages=[
                    {"role": "system", "content": CLEANUP_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_tokens=max_out,
                frequency_penalty=1.0,
            )
            result = response.choices[0].message.content
            if not result:
                return text
            result = result.strip()
            # Safety: if output is much longer than input, likely hallucination
            if len(result) > len(text) * 3:
                log.warning(f"Groq LLM output too long ({len(result)} vs {len(text)}), using raw")
                return text
            return result
        except Exception as e:
            log.warning(f"Groq LLM cleanup failed, using raw: {e}")
            return text

    def _gemini_cleanup(self, text: str) -> str:
        if not text or not self.gemini_api_key:
            return text

        body = {
            "contents": [{"parts": [{"text": CLEANUP_PROMPT + "\n\n" + text}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 2048,
            },
        }

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        resp = self._http.post(url, params={"key": self.gemini_api_key}, json=body)
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

    def update_gemini_key(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        if gemini_api_key and not self._http:
            self._http = httpx.Client(http2=True, timeout=15.0)
        elif not gemini_api_key and self._http:
            self.close()
            self._http = None

    def close(self):
        """Explicitly close the HTTP client to release connection pool."""
        if self._http:
            try:
                self._http.close()
            except Exception:
                pass
            self._http = None

    def __del__(self):
        self.close()
