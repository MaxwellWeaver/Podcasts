"""Pipeline stages. Each stage reads/writes artifacts under episodes/<feed>/<date>/."""

# Canonical stage order. The CLI uses this to enable --from-stage.
STAGES = [
    "gather",
    "dedupe",
    "rank",
    "context",
    "script",
    "tts",
    "vault_update",
    "feed",
    "deploy",
]
