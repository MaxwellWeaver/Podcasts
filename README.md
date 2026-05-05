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

In rough order of how often you'll touch them:

1. `CLAUDE.md` — **editorial voice** for the script writer (tone, anti-patterns, calibration log). Appended verbatim to every Sonnet script prompt. Most-touched file.
2. `config/pronunciations.yaml` — Kokoro substitution rules for names/acronyms. Append fixes after each listen.
3. `prompts/script.md` — script writer's **structural** instructions (section structure, length targets, output format). Touch when you want to change shape, not voice.
4. `prompts/rank.md` — Haiku news-editor scoring rubric. Touch if you find the ranker is missing or over-rating items.
5. `prompts/summarize.md` — Haiku per-topic / per-entity vault summarizer. Touch if vault summaries drift toward "general knowledge" rather than "what THIS episode added".
6. `config/sources.<feed>.yaml` — feed list, weights, recency caps.

## Capacity

Voice-only mono MP3 at 64 kbps. Daily news ≈5–7 MB/ep, weekly AI ≈12 MB/ep → ~3.2 GB/year. GitHub repo soft limit is 1 GB; first warning around month 4.

Tripwire: `python scripts/check_repo_size.py` warns at 800 MB and 950 MB. Add it to your monthly habit, or wire it into the deploy step.

### R2 migration playbook (when the tripwire fires)

The pipeline is wired so this is a one-flag move:

1. Create a Cloudflare account + R2 bucket (10 GB free; no egress fees). Enable the public R2.dev URL on the bucket, or attach a custom subdomain.
2. `rclone copy docs/ r2:<bucket-name>/` (or any S3-compatible client) to seed the bucket with all current MP3s.
3. Edit `config/config.yaml`: change `audio_base_url:` to your R2 public URL.
4. `python -m podcastgen run world_news --from-stage feed` regenerates `feed.xml` with R2-pointing enclosures. Episode GUIDs are the audio URLs, which DO change — so podcast apps will treat them as new episodes. To avoid that, either (a) accept the dupe for one cycle, or (b) one-shot regenerate `feed.xml` with the OLD GUIDs preserved by setting `feed.preserve_guids: true` (TODO if needed).
5. Once verified, delete `docs/<feed>/audio/` from the repo to reclaim the GB.
6. Future episodes write to R2 (TODO: add an `audio_storage: r2` config and an `s3` client in the feed stage when needed). Until that's wired, the manual flow is: render locally → upload MP3 to R2 → run feed regen.

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

Run the included PowerShell installer once to set up Task Scheduler:

```
powershell -ExecutionPolicy Bypass -File scripts/install_scheduled_tasks.ps1
```

Defaults: World News daily at 06:00, AI Weekly Mondays at 06:30. Edit the `.ps1` to change.

Manual trigger / verify / remove:

```
schtasks /Run    /TN "Podcast - World News"
schtasks /Query  /TN "Podcast - World News"
schtasks /Delete /TN "Podcast - World News" /F
```

Optional desktop notification on completion: `pip install -e .[notify]` and set `notify_on_complete: true` in `config/config.yaml` (default).

## Subscribing on your phone

The feed lives at:

```
https://maxwellweaver.github.io/Podcasts/world_news/feed.xml
https://maxwellweaver.github.io/Podcasts/ai/feed.xml
```

Add by URL in any podcast app that supports it:
- **Pocket Casts** (iOS / Android): Discover → search icon → enter URL
- **AntennaPod** (Android): + → Add Podcast → Add via URL
- **Overcast** (iOS): + → Add URL

Apple Podcasts won't accept arbitrary URLs without submission — use Pocket Casts on iOS instead.

Validate the feed structure with [podba.se/validate](https://podba.se/validate/) before troubleshooting in an app.
