"""Stage 7: vault_update.

Runs after TTS so it has duration_sec and audio_uuid available.

What it does:
  1. Calls Haiku once to generate per-topic and per-entity 1-2 sentence summaries
     from the script (so the vault entries are content-rich, not "see brief").
  2. Normalizes entity kinds returned by the script-writer model into our enum.
  3. Upserts topic and entity files via VaultWriter.
  4. Writes the episode file (frontmatter + brief + full script).
  5. Appends every URL from ranked.json to the seen_urls ledger.

Python applies the patch — the model never writes raw files.
"""

from __future__ import annotations

import json
import secrets
import textwrap
from datetime import date

from podcastgen.config import load_prompt
from podcastgen.llm import make_client
from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger
from podcastgen.util.slug import slugify
from podcastgen.vault.schema import EntityKind
from podcastgen.vault.writer import VaultWriter

log = get_logger(__name__)


# Map permissive kinds the model emits onto our schema enum.
KIND_MAP: dict[str, EntityKind] = {
    "person": "person",
    "people": "person",
    "individual": "person",
    "org": "org",
    "organization": "org",
    "company": "org",
    "agency": "org",
    "party": "org",
    "place": "place",
    "country": "place",
    "city": "place",
    "region": "place",
    "location": "place",
    "model": "model",
    "ai_model": "model",
    "weapon_system": "weapon_system",
    "weapon": "weapon_system",
    "system": "weapon_system",
    "vessel": "weapon_system",
    "ship": "weapon_system",
    "aircraft": "weapon_system",
    "concept": "concept",
    "policy": "concept",
    "event": "concept",
    "program": "concept",
}


def run_vault_update(ctx: RunContext) -> None:
    work = ctx.work_dir
    script = (work / "script.md").read_text(encoding="utf-8")
    meta = json.loads((work / "script_meta.json").read_text(encoding="utf-8"))
    ranked = json.loads((work / "ranked.json").read_text(encoding="utf-8"))
    audio_meta = _load_audio_meta(work)

    topics: list[str] = meta.get("topics", []) or []
    entities: list[dict] = meta.get("entities", []) or []
    title: str = meta.get("title", f"{ctx.feed} {ctx.date_str}")
    brief: str = meta.get("brief", "")

    # 1. Generate per-topic / per-entity summaries via Haiku.
    summaries = _generate_summaries(ctx, script, topics, entities)

    writer = VaultWriter(ctx.cfg)

    # 2. Episode file — written first so we have a stable link string.
    audio_uuid = secrets.token_hex(4)  # 8 hex chars
    audio_filename = f"{ctx.date_str}-{audio_uuid}.mp3"
    audio_relpath = f"{ctx.cfg.docs_root.name}/{ctx.feed}/audio/{audio_filename}"

    entity_links = [f"[[{e.get('name', '')}]]" for e in entities if e.get("name")]

    episode_path = writer.write_episode(
        feed=ctx.feed,
        ep_date=ctx.run_date,
        title=title,
        brief=brief,
        script=script,
        duration_sec=audio_meta.get("duration_sec", 0),
        audio_relpath=audio_relpath,
        audio_uuid=audio_uuid,
        topics=topics,
        entities=entity_links,
        sources_count=len(ranked),
    )
    episode_link_name = episode_path.stem  # e.g. "2026-05-04 may-fourth-briefing"

    # 3. Topic upserts.
    for topic_str in topics:
        topic_summary = summaries.get("topics", {}).get(topic_str) or brief
        topic_title = _wikilink_title(topic_str)
        if not topic_title:
            continue
        writer.upsert_topic(
            title=topic_title,
            summary_para=topic_summary,
            episode_link=episode_link_name,
            episode_date=ctx.run_date,
        )

    # 4. Entity upserts.
    for ent in entities:
        name = ent.get("name", "").strip()
        if not name:
            continue
        kind = KIND_MAP.get(str(ent.get("kind", "concept")).lower(), "concept")
        ent_summary = summaries.get("entities", {}).get(name) or brief
        writer.upsert_entity(
            title=name,
            kind=kind,
            summary_para=ent_summary,
            episode_link=episode_link_name,
            episode_date=ctx.run_date,
        )

    # 5. URL ledger.
    rows = [
        {
            "url": it["url"],
            "feed": ctx.feed,
            "episode_date": ctx.date_str,
            "first_seen": ctx.date_str,
        }
        for it in ranked
        if it.get("url")
    ]
    writer.append_seen_urls(rows)
    log.info(
        "vault_update: episode=%s topics=%d entities=%d urls=%d",
        episode_path.name, len(topics), len(entities), len(rows),
    )

    # Stash audio_uuid + episode path for the feed stage.
    (work / "episode_meta.json").write_text(
        json.dumps({
            "episode_path": str(episode_path),
            "audio_uuid": audio_uuid,
            "audio_filename": audio_filename,
            "title": title,
            "brief": brief,
            "duration_sec": audio_meta.get("duration_sec", 0),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _generate_summaries(
    ctx: RunContext,
    script: str,
    topics: list[str],
    entities: list[dict],
) -> dict:
    if not topics and not entities:
        return {"topics": {}, "entities": {}}

    user_prompt = textwrap.dedent(f"""\
        Topics to summarize:
        {json.dumps(topics, indent=2)}

        Entities to summarize:
        {json.dumps([e.get('name') for e in entities if e.get('name')], indent=2)}

        Script:
        ---
        {script}
        ---

        Return JSON: {{"topics": {{topic: summary, ...}}, "entities": {{name: summary, ...}}}}
    """)

    client = make_client(ctx.cfg, log_path=ctx.work_dir / "llm_calls.jsonl")
    resp = client.complete(
        user_prompt,
        tier="haiku",
        system=load_prompt("summarize"),
        json_mode=True,
        max_tokens=4096,
    )
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError as e:
        log.warning("summaries response not parseable, using empty: %s", e)
        return {"topics": {}, "entities": {}}


def _wikilink_title(s: str) -> str:
    s = s.strip()
    if s.startswith("[[") and s.endswith("]]"):
        s = s[2:-2]
    return s.strip()


def _load_audio_meta(work_dir) -> dict:
    p = work_dir / "audio_meta.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
