"""LLMClient ABC. The pipeline only ever talks to this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Tier = Literal["haiku", "sonnet", "opus"]


@dataclass
class LLMResponse:
    text: str
    raw: dict[str, Any] = field(default_factory=dict)
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient(ABC):
    """Single complete() call. Backends live in claude_cli.py / anthropic_sdk.py."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        tier: Tier,
        system: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a prompt, get a response. JSON mode strips fences and asserts parseable."""
        ...
