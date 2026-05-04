"""Stage 5: script writing. Sonnet writes the spoken script.

Reads ranked.json + context.md + CLAUDE.md. Writes script.md.
The script is the literal text that will be sent to TTS — no markdown headings,
no stage directions in the body.
"""

from __future__ import annotations

import json
import textwrap

from podcastgen.config import load_claude_md
from podcastgen.llm import make_client
from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger

log = get_logger(__name__)


SCRIPT_INSTRUCTIONS = textwrap.dedent("""\
    You are writing the spoken script for one episode of a personal podcast.
    The output goes directly to a single-host TTS engine. The text you produce
    IS what will be spoken — there is no editor between you and the listener.

    Hard rules:
      - Output ONLY the script body. No greeting, no markdown headings, no bullet
        points, no stage directions, no "[INTRO]" markers, no metadata block.
      - Section breaks are blank lines. That is all.
      - Spell out numbers and dates ("twenty twenty six", "May fourth").
      - When the context bundle shows prior coverage of a topic, reference it
        explicitly ("This is the third Black Sea fleet strike this month.").
      - Do not invent facts beyond what the ranked items and context provide.

    After the script, on a new line, output exactly one blank line, then a JSON
    object on a single line with the following keys:
        {"title": "<short episode title>", "brief": "<1-2 sentence human summary>",
         "topics": ["[[Topic A]]", "[[Topic B]]"],
         "entities": [{"name": "Volodymyr Zelensky", "kind": "person"}, ...]}

    Wrap that JSON in fences exactly like:
        ```meta
        {...}
        ```

    Nothing else after the meta block.
""")


def run_script(ctx: RunContext) -> None:
    feed_cfg = ctx.cfg.feeds[ctx.feed]
    ranked = json.loads((ctx.work_dir / "ranked.json").read_text(encoding="utf-8"))
    context_md = (ctx.work_dir / "context.md").read_text(encoding="utf-8")
    claude_md = load_claude_md()

    user_prompt = _build_script_prompt(ctx.feed, feed_cfg, ranked, context_md)
    system = claude_md + "\n\n---\n\n" + SCRIPT_INSTRUCTIONS

    client = make_client(ctx.cfg, log_path=ctx.work_dir / "llm_calls.jsonl")
    resp = client.complete(
        user_prompt,
        tier="sonnet",
        system=system,
        json_mode=False,
        max_tokens=12000,
    )

    script_body, meta = _split_script_and_meta(resp.text)

    (ctx.work_dir / "script.md").write_text(script_body, encoding="utf-8")
    (ctx.work_dir / "script_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("script written: %d chars, %d words; title=%r",
             len(script_body), len(script_body.split()), meta.get("title"))


def _build_script_prompt(feed: str, fc, ranked: list[dict], context_md: str) -> str:
    items_block = []
    for i, it in enumerate(ranked[:25]):  # cap items to keep prompt size bounded
        items_block.append(f"### Item {i + 1} (score {it.get('score', 0):.1f})")
        items_block.append(f"source: {it.get('source_name', '')} | category: {it.get('category', '')}")
        items_block.append(f"url: {it.get('url', '')}")
        items_block.append(f"published: {it.get('published', '')}")
        items_block.append(f"title: {it.get('title', '')}")
        if it.get("summary"):
            items_block.append(f"summary: {it['summary'][:600]}")
        if it.get("body"):
            items_block.append(f"body: {it['body'][:1500]}")
        if it.get("reasoning"):
            items_block.append(f"editor note: {it['reasoning']}")
        items_block.append("")

    return textwrap.dedent(f"""\
        Feed: {feed}
        Cadence: {fc.cadence}
        Target length: {fc.target_words} words ({fc.target_minutes} min). Floor {fc.word_floor}, ceiling {fc.word_ceiling}.

        # Context bundle (running threads, prior coverage, user inbox)

        {context_md}

        # Ranked items to cover

        {chr(10).join(items_block)}

        Write the spoken script now. Remember: only the spoken text, then the meta block.
    """)


def _split_script_and_meta(text: str) -> tuple[str, dict]:
    """Split the response into script body and the trailing ```meta``` JSON block."""
    fence = "```meta"
    idx = text.rfind(fence)
    if idx == -1:
        log.warning("no meta block found in script response; using empty meta")
        return text.strip(), {}

    script = text[:idx].rstrip()
    rest = text[idx + len(fence):]
    end = rest.find("```")
    if end == -1:
        log.warning("unterminated meta block; using empty meta")
        return script, {}
    meta_str = rest[:end].strip()
    try:
        meta = json.loads(meta_str)
    except json.JSONDecodeError as e:
        log.warning("malformed meta JSON (%s); using empty meta", e)
        meta = {}
    return script, meta
