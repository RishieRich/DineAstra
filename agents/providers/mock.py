"""The no-keys provider.

It does not call anything. The narrator hands it an intent and the computed
figures, and it renders a canned template from agents/mock_bank.py with those
figures substituted in. The prose is fixed; every number in it is live.
"""

from __future__ import annotations

import re
from typing import Iterator

from agents import mock_bank
from agents.providers.base import ProviderStatus


class MockProvider:
    name = "mock"
    model = "sample-data"

    def validate(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            available=True,
            model=self.model,
            detail="No API key needed. Prose is canned, every figure is computed.",
        )

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """Unused in mock mode -- the narrator calls render_intent instead."""
        yield from self.stream_text(prompt)

    def render_intent(self, intent: str, figures: dict[str, str]) -> str:
        return mock_bank.render(intent, figures)

    @staticmethod
    def stream_text(text: str) -> Iterator[str]:
        """Word by word, keeping the whitespace that follows each word."""
        for chunk in re.findall(r"\S+\s*", text):
            yield chunk
