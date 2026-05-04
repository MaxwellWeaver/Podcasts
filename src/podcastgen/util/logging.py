"""Single place to configure structured logging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(log_path: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)

    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
