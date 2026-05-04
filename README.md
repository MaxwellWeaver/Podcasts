# Podcasts

Automated personal podcast pipeline. Two feeds:

- **World News** — daily, ~14 min. Geopolitics, defense tech, tech news.
- **AI Capabilities** — weekly, ~25 min. SOTA model releases, research, industry, policy.

The pipeline: pulls fresh items from RSS sources, dedupes against a persistent Obsidian vault of prior coverage, ranks novelty + importance with Haiku, pulls running-thread context from the vault, writes a faithful script with Sonnet using `CLAUDE.md` as editorial guidance, narrates locally with Kokoro TTS, regenerates the RSS feed, and pushes to a GitHub Pages-hosted unlisted feed.

## Run

```
python -m podcastgen run world_news        # daily
python -m podcastgen run ai                # weekly
python -m podcastgen run world_news --dry-run        # stop after script (no audio, no commit)
python -m podcastgen run world_news --from-stage tts # resume mid-pipeline
```

## Structure

- `src/podcastgen/` — pipeline code
- `config/` — YAML knobs (sources, voices, models, pronunciations)
- `vault/` — Obsidian knowledge store (the source of truth)
- `episodes/<feed>/<date>/` — working artifacts per run (mostly gitignored)
- `docs/<feed>/` — RSS feed + MP3s (served by GitHub Pages from `/docs`)
- `CLAUDE.md` — editorial guidance, the main per-episode tuning lever

## Tuning between episodes

Two main levers:

1. `CLAUDE.md` — voice, structure, anti-patterns. Appended to every script-writing prompt.
2. `config/pronunciations.yaml` — Kokoro substitution rules for names/acronyms.

## Capacity

Voice-only mono MP3 at 64 kbps. Daily news ≈7 MB/ep, weekly AI ≈12 MB/ep → ~3.2 GB/year. GitHub repo soft limit is 1 GB; first warning around month 4. Migration: move audio to Cloudflare R2 (10 GB free, no egress), flip `audio_base_url` in `config/config.yaml`, regenerate feeds. GUIDs unchanged → no duplicate episodes.

## Setup (first time)

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
winget install Gyan.FFmpeg      # ffmpeg required for MP3 encode
python -m podcastgen llm-smoke  # confirms Claude CLI is reachable
```

Then edit `config/config.yaml` to set `audio_base_url` to your GitHub Pages URL, and edit `config/sources.world_news.yaml` to taste.

## Scheduling

```
schtasks /Create /TN "Podcast - World News" /TR "<repo>\.venv\Scripts\python.exe -m podcastgen run world_news" /SC DAILY /ST 06:00 /RL HIGHEST /F
schtasks /Create /TN "Podcast - AI Weekly"  /TR "<repo>\.venv\Scripts\python.exe -m podcastgen run ai"          /SC WEEKLY /D MON /ST 06:30 /RL HIGHEST /F
```
