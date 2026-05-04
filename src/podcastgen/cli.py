"""Single entry point for the podcast pipeline.

Usage:
    python -m podcastgen run <feed>                      # full pipeline
    python -m podcastgen run <feed> --dry-run            # stop after script stage
    python -m podcastgen run <feed> --from-stage tts     # resume mid-pipeline
    python -m podcastgen llm-smoke --tier haiku          # round-trip a prompt
    python -m podcastgen list-feeds                      # show configured feeds
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from podcastgen.config import load_config
from podcastgen.pipeline import STAGES
from podcastgen.util.logging import setup_logging


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Override config.yaml path.",
)
@click.pass_context
def main(ctx: click.Context, config_path: Path | None) -> None:
    cfg = load_config(config_path)
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = cfg


@main.command("run")
@click.argument("feed")
@click.option("--dry-run", is_flag=True, help="Stop after script; write no audio, no vault, no commit.")
@click.option(
    "--from-stage",
    type=click.Choice(STAGES),
    default="gather",
    help="Resume mid-pipeline from this stage.",
)
@click.pass_context
def run_cmd(ctx: click.Context, feed: str, dry_run: bool, from_stage: str) -> None:
    cfg = ctx.obj["cfg"]
    if feed not in cfg.feeds:
        raise click.BadParameter(f"unknown feed '{feed}'. configured: {list(cfg.feeds)}")

    log_path = cfg.logs_root / feed / f"{date.today().isoformat()}.log"
    setup_logging(log_path)

    from podcastgen.pipeline.runner import run as run_pipeline
    run_pipeline(feed, cfg, from_stage=from_stage, dry_run=dry_run)


@main.command("list-feeds")
@click.pass_context
def list_feeds(ctx: click.Context) -> None:
    cfg = ctx.obj["cfg"]
    for name, fc in cfg.feeds.items():
        click.echo(f"{name:14} {fc.cadence:7} {fc.target_minutes:3}min  {fc.title}")


@main.command("llm-smoke")
@click.option("--tier", default="haiku", type=click.Choice(["haiku", "sonnet", "opus"]))
@click.option("--prompt", default="Reply with the single word 'pong' and nothing else.")
@click.pass_context
def llm_smoke(ctx: click.Context, tier: str, prompt: str) -> None:
    """Round-trip a tiny prompt through the configured LLM backend."""
    setup_logging()
    cfg = ctx.obj["cfg"]
    from podcastgen.llm import make_client
    client = make_client(cfg)
    resp = client.complete(prompt, tier=tier, max_tokens=64)
    click.echo(f"--- response ---\n{resp.text}\n--- /response ---")
    click.echo(f"input_tokens={resp.input_tokens} output_tokens={resp.output_tokens}")


if __name__ == "__main__":
    main()
