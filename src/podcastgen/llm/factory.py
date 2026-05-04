"""Factory for LLM client selection. Backends keyed by config.llm.backend."""

from __future__ import annotations

from pathlib import Path

from podcastgen.config import Config
from podcastgen.llm.client import LLMClient


def make_client(cfg: Config, *, log_path: Path | None = None) -> LLMClient:
    backend = cfg.llm.backend
    if backend == "claude_cli":
        from podcastgen.llm.claude_cli import ClaudeCLIClient
        return ClaudeCLIClient(cfg, log_path=log_path)
    if backend == "anthropic_sdk":
        from podcastgen.llm.anthropic_sdk import AnthropicSDKClient
        return AnthropicSDKClient(cfg)
    raise ValueError(f"unknown llm.backend: {backend}")
