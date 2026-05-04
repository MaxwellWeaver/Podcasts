"""Stage 4: context retrieval. Builds context.md from vault topics + entities + inbox.

For each ranked item with a suggested_topic, look up the topic file and pull its
running summary + recent episode log. Also surface any active topics that haven't
been covered recently. Append everything in _inbox/ as the user's free-form notes.
"""

from __future__ import annotations

import json
from datetime import date

from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger
from podcastgen.util.slug import slugify
from podcastgen.vault.reader import VaultReader

log = get_logger(__name__)

STALE_TOPIC_DAYS = 14  # surface active topics not touched in this long


def run_context(ctx: RunContext) -> None:
    ranked_path = ctx.work_dir / "ranked.json"
    items = json.loads(ranked_path.read_text(encoding="utf-8"))
    reader = VaultReader(ctx.cfg)

    blocks: list[str] = ["# Context bundle for episode\n"]

    # Per-item topic context
    blocks.append("## Topic context for ranked items\n")
    seen_slugs: set[str] = set()
    for it in items:
        topic_str = it.get("suggested_topic", "")
        slug = _topic_to_slug(topic_str)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        topic = reader.load_topic(slug)
        if topic is None:
            blocks.append(f"### {topic_str} — NEW TOPIC (no prior coverage)\n")
        else:
            last = topic.metadata.get("last_covered", "?")
            mentions = topic.metadata.get("mentions", "?")
            blocks.append(
                f"### {topic_str} — last covered {last}, {mentions} prior mentions\n"
            )
            blocks.append(topic.content + "\n")

    # Active topics gone quiet
    quiet = _quiet_active_topics(reader, ctx.run_date)
    if quiet:
        blocks.append("## Active topics that have gone quiet (consider revisiting)\n")
        for t in quiet:
            title = _first_h1(t.content) or t.metadata.get("type", "topic")
            blocks.append(f"- {title} — last covered {t.metadata.get('last_covered', '?')}\n")

    # Inbox
    notes = reader.inbox_notes()
    if notes:
        blocks.append("## User notes from _inbox/\n")
        for note in notes:
            blocks.append(note.strip() + "\n\n")

    out_path = ctx.work_dir / "context.md"
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    log.info("wrote context bundle (%d topic blocks, %d quiet, %d inbox notes) to %s",
             len(seen_slugs), len(quiet), len(notes), out_path)


def _topic_to_slug(topic_str: str) -> str | None:
    """Extract slug from a wikilink like '[[Topic Name]]'."""
    s = topic_str.strip()
    if s.startswith("[[") and s.endswith("]]"):
        s = s[2:-2]
    s = s.strip()
    if not s:
        return None
    return slugify(s)


def _quiet_active_topics(reader: VaultReader, today: date) -> list:
    out = []
    for t in reader.active_topics():
        last = t.metadata.get("last_covered")
        last_d = reader._coerce_date(last)
        if last_d and (today - last_d).days >= STALE_TOPIC_DAYS:
            out.append(t)
    return out


def _first_h1(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None
