"""Stage 2: dedupe. Drops sources whose URLs are already in the vault ledger."""

from __future__ import annotations

import json

from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger
from podcastgen.vault.reader import VaultReader

log = get_logger(__name__)


def run_dedupe(ctx: RunContext) -> None:
    src_path = ctx.work_dir / "sources.json"
    items = json.loads(src_path.read_text(encoding="utf-8"))

    reader = VaultReader(ctx.cfg)
    seen = reader.seen_url_hashes()

    from podcastgen.util.slug import url_hash
    kept = [it for it in items if url_hash(it["url"]) not in seen]
    log.info("dedupe: kept %d / %d items", len(kept), len(items))

    src_path.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
