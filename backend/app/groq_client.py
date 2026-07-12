import json
import time

from groq import Groq, RateLimitError

from .settings import settings


class Translator:
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required.")
        self.client = Groq(api_key=settings.groq_api_key, max_retries=0)
        self._last_request_at = 0.0

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = settings.groq_min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def _completion(self, messages: list[dict[str, str]]):
        delay = 2.0
        for attempt in range(6):
            self._wait_for_rate_limit()
            try:
                return self.client.chat.completions.create(
                    model=settings.groq_model,
                    temperature=0,
                    messages=messages,
                )
            except RateLimitError:
                if attempt == 5:
                    raise
                time.sleep(delay)
                delay = min(delay * 1.8, 30)
        raise RuntimeError("Groq completion failed.")

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        if not text.strip():
            return text

        source = "the detected source language" if source_language == "auto" else source_language
        response = self._completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a precise document translator. Translate only the supplied text "
                        "from {source} to {target}. Preserve meaning, tone, numbers, punctuation, "
                        "line intent, and technical terms. Return only the translated text."
                    ).format(source=source, target=target_language),
                },
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content.strip()

    def translate_lines(self, lines: list[str], source_language: str, target_language: str) -> list[str]:
        non_empty = [line for line in lines if line.strip()]
        if not non_empty:
            return lines

        source = "the detected source language" if source_language == "auto" else source_language
        response = self._completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a precise document translator. Translate this JSON array of text "
                        "lines from {source} to {target}. Preserve the array length and order. "
                        "Return only a valid JSON array of strings."
                    ).format(source=source, target=target_language),
                },
                {"role": "user", "content": json.dumps(lines, ensure_ascii=False)},
            ],
        )

        content = response.choices[0].message.content.strip()
        try:
            translated = json.loads(content)
        except json.JSONDecodeError:
            return [self.translate(line, source_language, target_language) for line in lines]

        if not isinstance(translated, list) or len(translated) != len(lines):
            return [self.translate(line, source_language, target_language) for line in lines]

        return [str(line) for line in translated]
