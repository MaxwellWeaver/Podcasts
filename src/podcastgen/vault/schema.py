"""Vault frontmatter schemas. Dataclasses double as the source of truth for fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Literal

EntityKind = Literal["person", "org", "place", "model", "weapon_system", "concept"]
TopicStatus = Literal["active", "dormant", "resolved"]


def _serialize(d: dict[str, Any]) -> dict[str, Any]:
    """Convert dataclass dict to YAML-friendly types (date -> isoformat str)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, date):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            out[k] = [
                vv.isoformat() if isinstance(vv, date) else vv for vv in v
            ]
        else:
            out[k] = v
    return out


@dataclass
class EpisodeFrontmatter:
    type: str = "episode"
    feed: str = ""
    date: date = field(default_factory=date.today)
    title: str = ""
    duration_sec: int = 0
    audio: str = ""             # path or URL where MP3 lives
    audio_uuid: str = ""        # short URL-safe token in MP3 filename
    topics: list[str] = field(default_factory=list)     # ["[[wiki-link]]", ...]
    entities: list[str] = field(default_factory=list)
    sources: int = 0
    script_chars: int = 0
    word_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass
class TopicFrontmatter:
    type: str = "topic"
    status: TopicStatus = "active"
    first_seen: date = field(default_factory=date.today)
    last_covered: date = field(default_factory=date.today)
    mentions: int = 1
    related_entities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass
class EntityFrontmatter:
    type: str = "entity"
    kind: EntityKind = "concept"
    aliases: list[str] = field(default_factory=list)
    first_seen: date = field(default_factory=date.today)
    last_seen: date = field(default_factory=date.today)
    mentions: int = 1

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))
