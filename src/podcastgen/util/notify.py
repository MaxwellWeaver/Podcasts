"""Optional Windows toast notification on completion.

Uses win10toast (install with `pip install -e .[notify]`). Silently no-ops if
the import fails so the pipeline never breaks because of a notification.
"""

from __future__ import annotations

from podcastgen.util.logging import get_logger

log = get_logger(__name__)


def toast(title: str, body: str) -> None:
    try:
        from win10toast import ToastNotifier  # type: ignore
    except ImportError:
        log.debug("win10toast not installed; skipping toast")
        return
    try:
        ToastNotifier().show_toast(title, body, duration=8, threaded=True)
    except Exception as e:  # noqa: BLE001 — toasts must never break the pipeline
        log.warning("toast failed: %s", e)
