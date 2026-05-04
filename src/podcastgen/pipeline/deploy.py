"""Stage 9: deploy. git add + commit + push.

Pushes the docs/ tree (RSS + audio) and the vault state (episodes, topics,
entities, sources) to the configured remote. GitHub Pages then serves the new
episode automatically.
"""

from __future__ import annotations

import subprocess

from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger

log = get_logger(__name__)


def run_deploy(ctx: RunContext) -> None:
    cfg = ctx.cfg
    repo = cfg.project_root

    add_paths = [str(cfg.docs_root.relative_to(repo)),
                 str(cfg.vault_root.relative_to(repo))]

    msg = cfg.deploy.commit_message_fmt.format(feed=ctx.feed, date=ctx.date_str)

    _run(["git", "add", *add_paths], cwd=repo)

    # If nothing staged, skip cleanly.
    diff = _run(["git", "diff", "--cached", "--name-only"], cwd=repo, capture=True)
    if not diff.strip():
        log.info("deploy: nothing staged, skipping commit + push")
        return

    _run(["git", "commit", "-m", msg], cwd=repo)
    log.info("deploy: committed %s", msg)

    remote = cfg.deploy.git_remote
    branch = cfg.deploy.git_branch
    has_remote = bool(_run(["git", "remote"], cwd=repo, capture=True).strip())
    if not has_remote:
        log.warning("deploy: no git remote configured; skipping push")
        return
    _run(["git", "push", remote, branch], cwd=repo)
    log.info("deploy: pushed to %s/%s", remote, branch)


def _run(cmd: list[str], *, cwd, capture: bool = False) -> str:
    log.debug("$ %s", " ".join(cmd))
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git command failed: {' '.join(cmd)}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return proc.stdout if capture else ""
