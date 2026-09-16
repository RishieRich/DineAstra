"""Provider contract and resolution.

Resolution order is deliberate: Gemini if a key is present and its configured
model validates, then Groq on the same terms, then mock. Mock is not a
failure state -- it is the default, and the app is fully usable there.

Model validation happens once at startup (rule VIII): a configured model id
is checked against the ids the provider actually offers. A wrong id logs a
warning that lists what is available and falls through to the next provider
rather than failing a request later, in front of an audience.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Iterator, Protocol

logger = logging.getLogger("darpan.providers")


@dataclass
class ProviderStatus:
    name: str
    available: bool
    model: str | None = None
    detail: str = ""
    available_models: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available": self.available,
            "model": self.model,
            "detail": self.detail,
        }


class Provider(Protocol):
    """What the narrator needs from a model, and nothing more."""

    name: str
    model: str | None

    def validate(self) -> ProviderStatus:
        """Check key and model id. Never raises."""

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """Yield chunks of prose. Never raises past the narrator."""


def resolve_provider(force: str | None = None) -> tuple[Provider, ProviderStatus]:
    """Pick a provider at startup and say plainly which one and why."""
    from agents.providers.gemini import GeminiProvider
    from agents.providers.groq import GroqProvider
    from agents.providers.mock import MockProvider

    requested = (force or os.getenv("DARPAN_PROVIDER", "")).strip().lower()

    candidates: list[Provider] = []
    if requested == "mock":
        candidates = [MockProvider()]
    elif requested == "gemini":
        candidates = [GeminiProvider(), MockProvider()]
    elif requested == "groq":
        candidates = [GroqProvider(), MockProvider()]
    else:
        candidates = [GeminiProvider(), GroqProvider(), MockProvider()]

    attempts: list[ProviderStatus] = []
    for candidate in candidates:
        status = candidate.validate()
        attempts.append(status)
        if status.available:
            logger.info("DineAstra answering through %s (%s)", status.name, status.model)
            return candidate, status
        if status.detail:
            logger.warning("%s unavailable: %s", status.name, status.detail)
            if status.available_models:
                logger.warning(
                    "%s offers these model ids: %s",
                    status.name,
                    ", ".join(status.available_models[:20]),
                )

    # MockProvider always validates, so this is unreachable in practice.
    from agents.providers.mock import MockProvider as Fallback

    fallback = Fallback()
    return fallback, fallback.validate()
