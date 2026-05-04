"""LLMClient backed by the Anthropic Python SDK. Future swap target.

Stub today. To enable: `pip install -e .[api]` and set `llm.backend: anthropic_sdk`
in config.yaml plus `ANTHROPIC_API_KEY` in environment.
"""

from __future__ import annotations

from podcastgen.config import Config
from podcastgen.llm.client import LLMClient, LLMResponse, Tier


class AnthropicSDKClient(LLMClient):
    def __init__(self, cfg: Config) -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "anthropic SDK not installed. Run: pip install -e '.[api]'"
            ) from e
        self.cfg = cfg
        from anthropic import Anthropic
        self._client = Anthropic()  # picks up ANTHROPIC_API_KEY from env

    def complete(
        self,
        prompt: str,
        *,
        tier: Tier,
        system: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = self.cfg.llm.tiers[tier]
        if json_mode:
            prompt = (
                prompt
                + "\n\nRespond with ONLY a single valid JSON value. "
                "No prose, no markdown fences."
            )

        kwargs: dict = dict(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        msg = self._client.messages.create(**kwargs)
        text = "".join(block.text for block in msg.content if getattr(block, "text", None))
        return LLMResponse(
            text=text,
            raw=msg.model_dump() if hasattr(msg, "model_dump") else {},
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            cost_usd=None,
        )
