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


@main.command("tokens")
@click.argument("feed")
@click.option("--date", "ep_date", default=None,
              help="Episode date YYYY-MM-DD (defaults to today).")
@click.option("--all", "show_all", is_flag=True,
              help="Aggregate across all episode dirs for the feed.")
@click.pass_context
def tokens(ctx: click.Context, feed: str, ep_date: str | None, show_all: bool) -> None:
    """Summarize LLM token + cost usage from llm_calls.jsonl logs.

    The cost figures are API-equivalent prices reported by the Claude CLI.
    On the subscription backend you don't pay these — this is just for
    knowing what the equivalent API spend would be.
    """
    import json
    from datetime import date as _date

    cfg = ctx.obj["cfg"]
    feed_dir = cfg.episodes_root / feed
    if not feed_dir.exists():
        raise click.ClickException(f"no episodes dir at {feed_dir}")

    if show_all:
        log_paths = sorted(feed_dir.glob("*/llm_calls.jsonl"))
    else:
        d = ep_date or _date.today().isoformat()
        log_paths = [feed_dir / d / "llm_calls.jsonl"]

    grand_in = grand_out = 0
    grand_cost = 0.0
    grand_calls = 0
    for path in log_paths:
        if not path.exists():
            click.echo(f"(no log: {path})")
            continue
        click.echo(f"--- {path.parent.name} ---")
        per_tier: dict[str, dict] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            t = entry["tier"]
            d = per_tier.setdefault(t, {"calls": 0, "in": 0, "out": 0, "cost": 0.0, "elapsed": 0.0})
            d["calls"] += 1
            d["in"] += entry.get("input_tokens") or 0
            d["out"] += entry.get("output_tokens") or 0
            d["cost"] += entry.get("cost_usd") or 0.0
            d["elapsed"] += entry.get("elapsed_sec") or 0.0
        for t, d in per_tier.items():
            click.echo(f"  {t:7s} {d['calls']:2d} calls  in={d['in']:>7d}  out={d['out']:>6d}  "
                       f"cost=${d['cost']:.4f}  elapsed={d['elapsed']:.1f}s")
            grand_calls += d["calls"]
            grand_in += d["in"]
            grand_out += d["out"]
            grand_cost += d["cost"]

    if grand_calls:
        click.echo("=" * 60)
        click.echo(f"  total   {grand_calls:2d} calls  in={grand_in:>7d}  out={grand_out:>6d}  "
                   f"cost=${grand_cost:.4f}")
        click.echo("(cost is API-equivalent; subscription backend pays $0)")


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
