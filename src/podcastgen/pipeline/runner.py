"""Pipeline orchestrator. Stages are wired in here as they are built."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from podcastgen.config import Config
from podcastgen.pipeline import STAGES
from podcastgen.util.logging import get_logger

log = get_logger(__name__)


@dataclass
class RunContext:
    """Carries per-run state: which feed, the dated working dir, config."""

    feed: str
    run_date: date
    cfg: Config
    work_dir: Path
    dry_run: bool = False

    @property
    def date_str(self) -> str:
        return self.run_date.isoformat()


def make_context(feed: str, cfg: Config, *, dry_run: bool = False) -> RunContext:
    today = date.today()
    work_dir = cfg.episodes_root / feed / today.isoformat()
    work_dir.mkdir(parents=True, exist_ok=True)
    return RunContext(feed=feed, run_date=today, cfg=cfg, work_dir=work_dir, dry_run=dry_run)


def run(feed: str, cfg: Config, *, from_stage: str = "gather", dry_run: bool = False) -> None:
    """Execute the pipeline for `feed`, optionally resuming from `from_stage`."""
    if from_stage not in STAGES:
        raise ValueError(f"unknown stage: {from_stage}. valid: {STAGES}")

    ctx = make_context(feed, cfg, dry_run=dry_run)
    log.info("run start: feed=%s date=%s work_dir=%s dry_run=%s",
             feed, ctx.date_str, ctx.work_dir, dry_run)
    started = datetime.now()

    start_idx = STAGES.index(from_stage)
    for stage in STAGES[start_idx:]:
        if dry_run and stage in ("vault_update", "tts", "feed", "deploy"):
            log.info("[dry-run] skipping stage: %s", stage)
            continue
        log.info("--- stage: %s ---", stage)
        _dispatch(stage, ctx)

    elapsed = datetime.now() - started
    log.info("run done in %s", elapsed)
    if cfg.notify_on_complete and not dry_run:
        from podcastgen.util.notify import toast
        toast(f"Podcast: {feed} done",
              f"{ctx.run_date.isoformat()} episode shipped in {elapsed}.")


def _dispatch(stage: str, ctx: RunContext) -> None:
    """Lazy-import stage modules so partial-build doesn't break the CLI."""
    if stage == "gather":
        from podcastgen.pipeline.gather import run_gather
        run_gather(ctx)
    elif stage == "dedupe":
        from podcastgen.pipeline.dedupe import run_dedupe
        run_dedupe(ctx)
    elif stage == "rank":
        from podcastgen.pipeline.rank import run_rank
        run_rank(ctx)
    elif stage == "context":
        from podcastgen.pipeline.context import run_context
        run_context(ctx)
    elif stage == "script":
        from podcastgen.pipeline.script import run_script
        run_script(ctx)
    elif stage == "vault_update":
        from podcastgen.pipeline.vault_update import run_vault_update
        run_vault_update(ctx)
    elif stage == "tts":
        from podcastgen.pipeline.tts import run_tts
        run_tts(ctx)
    elif stage == "feed":
        from podcastgen.pipeline.feed import run_feed
        run_feed(ctx)
    elif stage == "deploy":
        from podcastgen.pipeline.deploy import run_deploy
        run_deploy(ctx)
    else:
        raise ValueError(f"no dispatcher for stage: {stage}")
