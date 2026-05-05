"""Config loading. Loads `config/config.yaml` and per-feed source files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
PROMPTS_DIR = PROJECT_ROOT / "prompts"


@dataclass
class LLMConfig:
    backend: str
    cli_path: str
    tiers: dict[str, str]
    # Per-tier timeouts in seconds. Falls back to 300s if a tier is missing.
    timeouts_sec: dict[str, int] = field(default_factory=lambda: {"haiku": 300, "sonnet": 600, "opus": 900})
    retries: int = 3
    retry_backoff_sec: int = 5

    def timeout_for(self, tier: str) -> int:
        return int(self.timeouts_sec.get(tier, 300))


@dataclass
class TTSConfig:
    engine: str
    voices: dict[str, str]
    speed: float = 1.0
    sample_rate: int = 24000
    output_bitrate: str = "64k"
    max_chars: int = 32000


@dataclass
class FeedConfig:
    title: str
    description: str
    target_minutes: int
    target_words: int
    word_floor: int
    word_ceiling: int
    cadence: str
    itunes_category: str
    itunes_subcategory: str | None = None


@dataclass
class RankingConfig:
    min_score: int = 12
    haiku_batch_size: int = 30
    body_truncate_chars: int = 1500


@dataclass
class DeployConfig:
    git_remote: str = "origin"
    git_branch: str = "main"
    commit_message_fmt: str = "[{feed}] {date} episode"


@dataclass
class Config:
    project_root: Path
    vault_root: Path
    docs_root: Path
    episodes_root: Path
    logs_root: Path
    audio_base_url: str
    llm: LLMConfig
    tts: TTSConfig
    feeds: dict[str, FeedConfig]
    ranking: RankingConfig
    deploy: DeployConfig
    notify_on_complete: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


def _resolve(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def load_config(path: Path | None = None) -> Config:
    """Load `config/config.yaml` and return a typed Config."""
    cfg_path = path or (CONFIG_DIR / "config.yaml")
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    feeds = {
        name: FeedConfig(**fc) for name, fc in raw["feeds"].items()
    }

    return Config(
        project_root=_resolve(raw["project_root"]),
        vault_root=_resolve(raw["vault_root"]),
        docs_root=_resolve(raw["docs_root"]),
        episodes_root=_resolve(raw["episodes_root"]),
        logs_root=_resolve(raw["logs_root"]),
        audio_base_url=raw["audio_base_url"].rstrip("/"),
        llm=LLMConfig(**raw["llm"]),
        tts=TTSConfig(**raw["tts"]),
        feeds=feeds,
        ranking=RankingConfig(**raw.get("ranking", {})),
        deploy=DeployConfig(**raw.get("deploy", {})),
        notify_on_complete=raw.get("notify_on_complete", True),
        raw=raw,
    )


def load_sources(feed: str) -> list[dict[str, Any]]:
    """Load `config/sources.<feed>.yaml` and return its `sources` list."""
    src_path = CONFIG_DIR / f"sources.{feed}.yaml"
    with src_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def load_pronunciations() -> dict[str, Any]:
    with (CONFIG_DIR / "pronunciations.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_claude_md() -> str:
    """Load CLAUDE.md as a string for injection into the script prompt."""
    return (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    """Load a per-task prompt from prompts/<name>.md (e.g. 'rank', 'summarize', 'script')."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
