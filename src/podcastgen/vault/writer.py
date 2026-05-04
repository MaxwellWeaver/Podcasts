"""Write-side of the vault. The ONLY module that mutates vault state.

Operations are append-only or update-in-place; never destructive.

Public API:
    VaultWriter(cfg).
        append_seen_urls(rows)
        upsert_topic(slug, title, summary_para, episode_link, related_entities=...)
        upsert_entity(slug, title, kind, summary_para, aliases=...)
        write_episode(feed, ep_date, title, brief, script, ...)
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

import frontmatter
import yaml

from podcastgen.config import Config
from podcastgen.util.slug import slugify, url_hash
from podcastgen.vault.schema import (
    EntityFrontmatter,
    EntityKind,
    EpisodeFrontmatter,
    TopicFrontmatter,
)


class VaultWriter:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.root = cfg.vault_root
        self.episodes_dir = self.root / "episodes"
        self.topics_dir = self.root / "topics"
        self.entities_dir = self.root / "entities"
        self.sources_dir = self.root / "sources"
        for d in (self.episodes_dir, self.topics_dir, self.entities_dir, self.sources_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.seen_urls_path = self.sources_dir / "seen_urls.md"

    # --- URL dedup ledger ---

    def append_seen_urls(self, rows: list[dict]) -> None:
        """Append rows to seen_urls.md. Each row: {url, feed, episode_date}.

        Idempotent on the basis of url_hash — duplicates are silently dropped.
        """
        existing = self._read_existing_url_hashes()
        new_lines: list[str] = []
        for r in rows:
            h = url_hash(r["url"])
            if h in existing:
                continue
            existing.add(h)
            new_lines.append(
                f"| {h} | {r['url']} | {r.get('first_seen', date.today().isoformat())} "
                f"| {r['feed']} | {r['episode_date']} |"
            )

        if not new_lines:
            return

        if not self.seen_urls_path.exists():
            self.seen_urls_path.write_text(
                "| url_hash | url | first_seen | feed | episode |\n"
                "|----------|-----|------------|------|---------|\n",
                encoding="utf-8",
            )
        with self.seen_urls_path.open("a", encoding="utf-8") as f:
            for line in new_lines:
                f.write(line + "\n")

    def _read_existing_url_hashes(self) -> set[str]:
        if not self.seen_urls_path.exists():
            return set()
        hashes: set[str] = set()
        with self.seen_urls_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("|") or line.startswith("|---") or line.startswith("| url_hash"):
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells:
                    hashes.add(cells[0])
        return hashes

    # --- Topics ---

    def upsert_topic(
        self,
        title: str,
        summary_para: str,
        episode_link: str,
        episode_date: date,
        *,
        related_entities: list[str] | None = None,
        slug: str | None = None,
    ) -> Path:
        slug = slug or slugify(title)
        path = self.topics_dir / f"{slug}.md"

        if path.exists():
            post = frontmatter.load(path)
            meta = post.metadata
            meta["last_covered"] = episode_date.isoformat()
            meta["mentions"] = int(meta.get("mentions", 0)) + 1
            meta["status"] = meta.get("status", "active")
            if related_entities:
                merged = sorted(set(list(meta.get("related_entities", [])) + related_entities))
                meta["related_entities"] = merged
            body = post.content.rstrip() + self._format_episode_log_entry(
                episode_date, episode_link
            )
            # Append a new running-summary paragraph above episode log
            body = self._append_summary_paragraph(body, summary_para, episode_date)
        else:
            fm = TopicFrontmatter(
                first_seen=episode_date,
                last_covered=episode_date,
                mentions=1,
                related_entities=related_entities or [],
            )
            meta = fm.to_dict()
            body = (
                f"# {title}\n\n"
                "## Running summary\n\n"
                f"_{episode_date.isoformat()}:_ {summary_para}\n\n"
                "## Episode log\n"
                f"- {episode_date.isoformat()} — {episode_link}\n"
            )
            post = frontmatter.Post(content=body, **meta)

        post.metadata = meta
        post.content = body
        self._dump(post, path)
        return path

    @staticmethod
    def _format_episode_log_entry(d: date, link: str) -> str:
        return f"\n- {d.isoformat()} — {link}\n"

    @staticmethod
    def _append_summary_paragraph(body: str, paragraph: str, d: date) -> str:
        marker = "## Episode log"
        new_para = f"_{d.isoformat()}:_ {paragraph}\n\n"
        if marker in body:
            head, _, tail = body.partition(marker)
            return head.rstrip() + "\n\n" + new_para + marker + tail
        return body.rstrip() + "\n\n" + new_para

    # --- Entities ---

    def upsert_entity(
        self,
        title: str,
        kind: EntityKind,
        summary_para: str,
        episode_link: str,
        episode_date: date,
        *,
        aliases: list[str] | None = None,
        slug: str | None = None,
    ) -> Path:
        slug = slug or slugify(title)
        path = self.entities_dir / f"{slug}.md"

        if path.exists():
            post = frontmatter.load(path)
            meta = post.metadata
            meta["last_seen"] = episode_date.isoformat()
            meta["mentions"] = int(meta.get("mentions", 0)) + 1
            if aliases:
                merged = sorted(set(list(meta.get("aliases", [])) + aliases))
                meta["aliases"] = merged
            body = post.content.rstrip()
            body += f"\n\n_{episode_date.isoformat()}:_ {summary_para}\n"
            body += f"\n- [[{episode_link}]]\n"
        else:
            fm = EntityFrontmatter(
                kind=kind,
                aliases=aliases or [],
                first_seen=episode_date,
                last_seen=episode_date,
                mentions=1,
            )
            meta = fm.to_dict()
            body = (
                f"# {title}\n\n"
                f"_{episode_date.isoformat()}:_ {summary_para}\n\n"
                "## Recent appearances\n"
                f"- [[{episode_link}]]\n"
            )

        post = frontmatter.Post(content=body, **meta)
        self._dump(post, path)
        return path

    # --- Episodes ---

    def write_episode(
        self,
        feed: str,
        ep_date: date,
        title: str,
        brief: str,
        script: str,
        *,
        duration_sec: int,
        audio_relpath: str,
        audio_uuid: str,
        topics: list[str],
        entities: list[str],
        sources_count: int,
    ) -> Path:
        feed_dir = self.episodes_dir / feed
        feed_dir.mkdir(parents=True, exist_ok=True)
        path = feed_dir / f"{ep_date.isoformat()} {slugify(title)}.md"

        fm = EpisodeFrontmatter(
            feed=feed,
            date=ep_date,
            title=title,
            duration_sec=duration_sec,
            audio=audio_relpath,
            audio_uuid=audio_uuid,
            topics=topics,
            entities=entities,
            sources=sources_count,
            script_chars=len(script),
            word_count=len(script.split()),
        )
        body = (
            "# Brief\n\n"
            f"{brief.strip()}\n\n"
            "# Script\n\n"
            f"{script.strip()}\n"
        )
        post = frontmatter.Post(content=body, **fm.to_dict())
        self._dump(post, path)
        return path

    # --- IO helper ---

    @staticmethod
    def _dump(post: frontmatter.Post, path: Path) -> None:
        # python-frontmatter's default YAML dumper handles lists and strings cleanly.
        path.parent.mkdir(parents=True, exist_ok=True)
        text = frontmatter.dumps(post, sort_keys=False)
        path.write_text(text + "\n", encoding="utf-8")
