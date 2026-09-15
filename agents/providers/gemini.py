"""Gemini provider.

Reads GEMINI_API_KEY and GEMINI_MODEL. Validation lists the models the key
can actually reach and checks the configured id against them, so a typo in
GEMINI_MODEL is caught at startup with the available ids printed, not in
front of an audience mid-answer.
"""

from __future__ import annotations

import json
import os
import time
from typing import Iterator

import httpx

from agents.providers.base import ProviderStatus

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-flash-latest"
TIMEOUT_SECONDS = 30


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    # -- validation ---------------------------------------------------------

    def validate(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(self.name, False, self.model, "no GEMINI_API_KEY set")

        try:
            ids = self._list_models()
        except Exception as exc:  # network, auth, anything
            return ProviderStatus(
                self.name, False, self.model, f"could not list models: {exc}"
            )

        if not ids:
            return ProviderStatus(
                self.name, False, self.model, "the key reached no usable models"
            )

        if self._normalise(self.model) not in {self._normalise(i) for i in ids}:
            return ProviderStatus(
                self.name,
                False,
                self.model,
                f"GEMINI_MODEL {self.model!r} is not a model this key can reach",
                available_models=ids,
            )

        # Being listed is not the same as being callable: Gemini still lists
        # models that answer "no longer available to new users" on the first
        # request. One tiny generation proves the id actually works, which is
        # the whole point of validating at startup rather than mid-question.
        reachable, detail = self._probe()
        if not reachable:
            return ProviderStatus(
                self.name,
                False,
                self.model,
                f"GEMINI_MODEL {self.model!r} is listed but not callable: {detail}",
                available_models=ids,
            )

        return ProviderStatus(self.name, True, self.model, "key and model validated")

    def _probe(self) -> tuple[bool, str]:
        """One minimal generation, to prove the model id is really usable."""
        url = f"{API_ROOT}/models/{self._normalise(self.model)}:generateContent"
        body = {
            "contents": [{"role": "user", "parts": [{"text": "OK"}]}],
            "generationConfig": {"maxOutputTokens": 1},
        }
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                response = client.post(url, params={"key": self.api_key}, json=body)
        except Exception as exc:
            return False, type(exc).__name__
        if response.status_code == 200:
            return True, "reachable"

        # A busy or rate-limited model is a real model id having a bad
        # minute. Demoting the provider for the life of the process over a
        # transient 429 or 503 would be the wrong call; the per-question
        # fallback already serves the template if the request fails again.
        if response.status_code in (408, 429) or response.status_code >= 500:
            return True, f"reachable but busy (HTTP {response.status_code})"

        try:
            message = response.json().get("error", {}).get("message", "")
        except Exception:
            message = response.text[:120]
        return False, f"HTTP {response.status_code}: {message[:120]}"

    @staticmethod
    def _normalise(model_id: str) -> str:
        return model_id.split("/")[-1].strip()

    def _list_models(self) -> list[str]:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{API_ROOT}/models", params={"key": self.api_key}
            )
            response.raise_for_status()
            payload = response.json()
        return [
            model["name"]
            for model in payload.get("models", [])
            if "generateContent" in model.get("supportedGenerationMethods", [])
        ]

    # -- generation ---------------------------------------------------------

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """Stream the narration, retrying once on a transient capacity error.

        Gemini's shared-capacity models return 503 often enough that a single
        retry is the difference between a live answer and a template one. Any
        other error propagates immediately to the narrator, which serves the
        template rather than showing the audience a stack trace.
        """
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                yield from self._stream_once(system, prompt)
                return
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status not in (408, 429) and status < 500:
                    raise
                last_error = exc
                if attempt == 0:
                    time.sleep(1.5)
        if last_error:
            raise last_error

    def _stream_once(self, system: str, prompt: str) -> Iterator[str]:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1200,
                # Narration needs no deliberation, and a thinking model will
                # otherwise spend the whole budget on thoughts and return no
                # prose at all.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        url = f"{API_ROOT}/models/{self._normalise(self.model)}:streamGenerateContent"

        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            with client.stream(
                "POST",
                url,
                params={"key": self.api_key, "alt": "sse"},
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
        parts = (
            payload.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        return "".join(part.get("text", "") for part in parts)
