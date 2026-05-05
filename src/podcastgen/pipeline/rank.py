"""Stage 3: rank. Haiku scores each surviving item on novelty + importance.

Reads sources.json. Writes ranked.json with each item enriched by:
    {novelty: 0-10, importance: 0-10, suggested_topic: "...", reasoning: "..."}

Items below ranking.min_score are dropped here (we don't keep them).
"""

from __future__ import annotations

import json

from podcastgen.config import load_prompt
from podcastgen.llm import make_client
from podcastgen.pipeline.runner import RunContext
from podcastgen.sources.fetch import extract_article
from podcastgen.util.logging import get_logger

log = get_logger(__name__)


def run_rank(ctx: RunContext) -> None:
    src_path = ctx.work_dir / "sources.json"
    items = json.loads(src_path.read_text(encoding="utf-8"))
    log.info("ranking %d items", len(items))

    if not items:
        (ctx.work_dir / "ranked.json").write_text("[]", encoding="utf-8")
        return

    # Pull article bodies for the items that have empty body, capped to budget.
    # Truncate to body_truncate_chars to keep token usage bounded.
    body_cap = ctx.cfg.ranking.body_truncate_chars
    for it in items:
        if not it.get("body"):
            text = extract_article(it["url"])
            it["body"] = text[:body_cap]
        else:
            it["body"] = it["body"][:body_cap]

    client = make_client(ctx.cfg, log_path=ctx.work_dir / "llm_calls.jsonl")
    system = load_prompt("rank")

    batch_size = ctx.cfg.ranking.haiku_batch_size
    ranked: list[dict] = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        prompt = _build_rank_prompt(batch)
        resp = client.complete(prompt, tier="haiku", system=system, json_mode=True, max_tokens=4096)
        try:
            scores = json.loads(resp.text)
        except json.JSONDecodeError:
            log.warning("rank batch returned malformed JSON, skipping batch")
            continue
        # scores is list of {index, novelty, importance, suggested_topic, reasoning}
        for s in scores:
            i = s.get("index")
            if not isinstance(i, int) or i < 0 or i >= len(batch):
                continue
            it = batch[i]
            it["novelty"] = int(s.get("novelty", 0))
            it["importance"] = int(s.get("importance", 0))
            it["suggested_topic"] = s.get("suggested_topic", "")
            it["reasoning"] = s.get("reasoning", "")
            it["score"] = (it["novelty"] + it["importance"]) * it.get("weight", 1.0)
            ranked.append(it)

    threshold = ctx.cfg.ranking.min_score
    kept = [it for it in ranked if it.get("score", 0) >= threshold]
    kept.sort(key=lambda it: it["score"], reverse=True)
    log.info("rank: kept %d / %d items above threshold %d",
             len(kept), len(ranked), threshold)

    (ctx.work_dir / "ranked.json").write_text(
        json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _build_rank_prompt(batch: list[dict]) -> str:
    lines = [
        "Score each item below. Return a JSON array of objects with keys:",
        '  index (int), novelty (0-10), importance (0-10), suggested_topic (str like "[[Topic Name]]"), reasoning (one sentence).',
        "",
        "Items:",
    ]
    for i, it in enumerate(batch):
        lines.append(f"--- index {i} ---")
        lines.append(f"source: {it.get('source_name', '')}  category: {it.get('category', '')}")
        lines.append(f"published: {it.get('published', '')}")
        lines.append(f"title: {it.get('title', '')}")
        if it.get("summary"):
            lines.append(f"summary: {it['summary'][:500]}")
        if it.get("body"):
            lines.append(f"body: {it['body'][:1500]}")
        lines.append("")
    return "\n".join(lines)
