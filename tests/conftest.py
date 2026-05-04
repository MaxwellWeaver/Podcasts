"""Shared pytest fixtures."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from podcastgen.config import (
    Config,
    DeployConfig,
    FeedConfig,
    LLMConfig,
    RankingConfig,
    TTSConfig,
    load_config,
)


@pytest.fixture()
def tmp_cfg(tmp_path: Path) -> Config:
    """A Config pointing entirely at a tmp_path sandbox."""
    cfg = load_config()
    return replace(
        cfg,
        project_root=tmp_path,
        vault_root=tmp_path / "vault",
        docs_root=tmp_path / "docs",
        episodes_root=tmp_path / "episodes",
        logs_root=tmp_path / "logs",
    )
