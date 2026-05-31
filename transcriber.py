import io
import re
import logging
import time
from groq import Groq

# Strip inline chain-of-thought some reasoning models emit in `content`.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

log = logging.getLogger("VoiceToText")

CLEANUP_PROMPT = """あなたは日本語の音声認識結果を校正する編集者です。音声認識は同音異義語の漢字をよく取り違えます。文脈から話者が本当に言いたかった表記に直すのが、あなたの最優先の仕事です。

【最優先：誤変換の修正】
- 文脈に合わない同音異義語・誤変換の漢字を、文脈に合う正しい漢字に必ず直す
  例: 「文章を成形する」→「文章を整形する」、「機械があれば」→「機会があれば」、「自身がある」→「自信がある」、「以外と」→「意外と」、「保障する」↔「保証する」
- 送り仮名・変換ミスも自然な表記に直す（例: 確認して下さい→確認してください）
- これは意味を変える行為ではなく、話者が意図した本来の意味を復元する作業です

【整形】
- 句読点（。、）を適切に付ける
- フィラー（えー・あの・うーん 等）を除去する
- 明らかな言い直し・重複を除去する
- 音声コマンドを変換: 「かっこ」→（ 「かっことじ」→） 「かぎかっこ」→「 「かぎかっことじ」→」 「すみかっこ」→【 「すみかっことじ」→】 「エンター」→改行 「まる」→。 「てん」→、

【禁止】
- 新しい文・情報・解釈を追加しない。質問には答えない
- 固有名詞・専門用語など正しい表記が判断できないものは変えない
- 出力は校正後の本文のみ（説明・前置き・引用符は不要）
- 入力が空・無意味・無音由来（例:「ご視聴ありがとうございました」のみ）なら、何も出力しない（空文字）"""

# Whisper segment-level hallucination filters (used with verbose_json).
# compression_ratio is the standard repetition/hallucination signal.
_COMPRESSION_RATIO_MAX = 2.4
_NO_SPEECH_PROB_MAX = 0.85
_AVG_LOGPROB_MIN = -1.0
# Whisper prompt is a vocabulary/style bias (max ~224 tokens). Keep it short;
# Japanese is ~1.5-2 tokens/char so cap conservatively and put key terms first.
_WHISPER_PROMPT_MAX_CHARS = 120


class Transcriber:
    def __init__(self, api_key: str,
                 groq_llm_model: str = "openai/gpt-oss-20b",
                 stt_model: str = "whisper-large-v3-turbo",
                 vocabulary: str = ""):
        self.api_key = api_key
        self.groq_llm_model = groq_llm_model
        self.stt_model = stt_model or "whisper-large-v3-turbo"
        self.vocabulary = vocabulary or ""
        self._groq = Groq(api_key=api_key)

    def _build_whisper_prompt(self) -> str:
        """Build a short vocabulary-bias prompt from the user's custom words.

        Whisper treats `prompt` as a style/vocabulary hint (not an instruction),
        so we just surface the user's frequent terms/proper nouns. Capped to
        ~224 tokens; we keep the most important terms (listed first) and trim.
        """
        vocab = (self.vocabulary or "").strip()
        if not vocab:
            return ""
        # Collapse whitespace/newlines so the cap counts real characters.
        vocab = " ".join(vocab.split())
        if len(vocab) > _WHISPER_PROMPT_MAX_CHARS:
            vocab = vocab[:_WHISPER_PROMPT_MAX_CHARS]
        return vocab

    def transcribe(self, wav_data: bytes, use_cleanup: bool = False, on_phase=None) -> str:
        """Transcribe WAV bytes to text.

        on_phase(name) is an optional callback invoked with "stt" before
        transcription and "cleanup" before the optional LLM formatting pass,
        so the UI can show "書き起こし中…" / "整形中…" labels.
        """
        if not wav_data:
            return ""

        if on_phase:
            try:
                on_phase("stt")
            except Exception:
                pass

        # Step 1: Fast transcription via Groq Whisper (~0.3s)
        t0 = time.perf_counter()
        raw_text = self._groq_transcribe(wav_data)
        t1 = time.perf_counter()
        log.info(f"Groq: {t1 - t0:.1f}s -> {raw_text}")

        if not raw_text:
            return ""

        # Skip LLM cleanup for trivially short output — nothing to format and
        # it only invites the model to hallucinate filler.
        if use_cleanup and len(raw_text.strip()) <= 2:
            log.info("Output too short, skipping LLM cleanup.")
            return raw_text

        # Step 2: LLM cleanup / 校正 (kanji correction + punctuation) — Groq only
        if use_cleanup:
            if on_phase:
                try:
                    on_phase("cleanup")
                except Exception:
                    pass
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
        prompt = self._build_whisper_prompt()

        kwargs = dict(
            model=self.stt_model,
            language="ja",
            temperature=0.0,
        )
        if prompt:
            kwargs["prompt"] = prompt

        # Preferred path: verbose_json lets us drop hallucinated / no-speech
        # segments (the "ご視聴ありがとうございました" problem) before joining.
        try:
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "recording.wav"
            result = self._groq.audio.transcriptions.create(
                file=audio_file,
                response_format="verbose_json",
                **kwargs,
            )
            return self._extract_clean_text(result)
        except Exception as e:
            log.warning(f"verbose_json transcribe failed ({e}); falling back to text")

        # Fallback: plain text (older SDK/model without segment metadata).
        audio_file = io.BytesIO(wav_data)
        audio_file.name = "recording.wav"
        result = self._groq.audio.transcriptions.create(
            file=audio_file,
            response_format="text",
            **kwargs,
        )
        if isinstance(result, str):
            return result.strip()
        return (getattr(result, "text", "") or "").strip()

    @staticmethod
    def _seg_get(seg, key, default=None):
        if isinstance(seg, dict):
            return seg.get(key, default)
        return getattr(seg, key, default)

    def _extract_clean_text(self, result) -> str:
        """Join verbose_json segments, dropping hallucinated/no-speech ones."""
        segments = self._seg_get(result, "segments", None)
        full_text = self._seg_get(result, "text", None)

        if not segments:
            return (full_text or "").strip()

        kept = []
        for seg in segments:
            text = self._seg_get(seg, "text", "") or ""
            comp = self._seg_get(seg, "compression_ratio", 0.0) or 0.0
            nsp = self._seg_get(seg, "no_speech_prob", 0.0) or 0.0
            alp = self._seg_get(seg, "avg_logprob", 0.0) or 0.0

            # Repetition/looping hallucination.
            if comp and comp > _COMPRESSION_RATIO_MAX:
                log.info(f"Drop repetitive segment (cr={comp:.2f}): {text!r}")
                continue
            # No speech AND low confidence — conservative AND to avoid over-trim.
            if nsp and alp and nsp > _NO_SPEECH_PROB_MAX and alp < _AVG_LOGPROB_MIN:
                log.info(f"Drop no-speech segment (nsp={nsp:.2f}, alp={alp:.2f}): {text!r}")
                continue
            kept.append(text)

        cleaned = "".join(kept).strip()
        # If every segment was dropped, the recording was (near-)silent/garbage:
        # returning "" is intended (better than pasting a hallucination).
        return cleaned

    def _groq_cleanup(self, text: str) -> str:
        if not text or not text.strip():
            return text
        model = self.groq_llm_model or ""
        # Reasoning models (gpt-oss, qwen3) emit chain-of-thought; gpt-oss puts
        # it in a separate field (content stays clean), but they still consume
        # output tokens — so give them headroom or max_tokens truncates the
        # actual answer to nothing. Non-reasoning models (llama) need far less.
        is_reasoning = ("gpt-oss" in model) or ("qwen3" in model)
        try:
            if is_reasoning:
                max_out = min(len(text) * 3 + 512, 1024)
            else:
                max_out = max(64, min(len(text) * 4, 512))

            kwargs = dict(
                model=model,
                messages=[
                    {"role": "system", "content": CLEANUP_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_tokens=max_out,
                frequency_penalty=1.0,
            )
            # Keep gpt-oss reasoning minimal: fast, and reasoning is returned in
            # a separate field so `content` is just the cleaned text.
            if "gpt-oss" in model:
                kwargs["reasoning_effort"] = "low"

            response = self._groq.chat.completions.create(**kwargs)
            result = response.choices[0].message.content
            if not result:
                return text
            # Some reasoning models inline <think>…</think> in content — strip it.
            result = _THINK_RE.sub("", result).strip()
            if not result:
                return text
            # Safety: a cleanup pass should never balloon the text (the +20
            # tolerance lets short inputs gain punctuation without false alarms).
            if len(result) > len(text) * 3 + 20:
                log.warning(f"Groq LLM output too long ({len(result)} vs {len(text)}), using raw")
                return text
            return result
        except Exception as e:
            log.warning(f"Groq LLM cleanup failed, using raw: {e}")
            return text

    def update_api_key(self, api_key: str):
        self.api_key = api_key
        self._groq = Groq(api_key=api_key)

    def close(self):
        """No external HTTP clients to release (Groq-only)."""
        pass

    def __del__(self):
        pass
