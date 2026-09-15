"""Groq provider.

Reads GROQ_API_KEY and GROQ_MODEL. Same startup validation as Gemini: the
configured model id is checked against what the key can reach, and a wrong id
falls through with the available ids logged rather than failing a request.
"""

from __future__ import annotations

import json
import os
from typing import Iterator

import httpx

from agents.providers.base import ProviderStatus

API_ROOT = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
TIMEOUT_SECONDS = 30


class GroqProvider:
    name = "groq"

    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    # -- validation ---------------------------------------------------------

    def validate(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(self.name, False, self.model, "no GROQ_API_KEY set")

        try:
            ids = self._list_models()
        except Exception as exc:
            return ProviderStatus(
                self.name, False, self.model, f"could not list models: {exc}"
            )

        if not ids:
            return ProviderStatus(
                self.name, False, self.model, "the key reached no usable models"
            )

        if self.model not in ids:
            return ProviderStatus(
                self.name,
                False,
                self.model,
                f"GROQ_MODEL {self.model!r} is not a model this key can reach",
                available_models=ids,
            )

        return ProviderStatus(self.name, True, self.model, "key and model validated")

    def _list_models(self) -> list[str]:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{API_ROOT}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
        return [model["id"] for model in payload.get("data", [])]

    # -- generation ---------------------------------------------------------

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 600,
            "stream": True,
        }

        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            with client.stream(
                "POST",
                f"{API_ROOT}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[len("data:") :].strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    text = self._text_from(chunk)
                    if text:
                        yield text

    @staticmethod
    def _text_from(raw: str) -> str:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return ""
        choices = payload.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("delta", {}).get("content", "") or ""
