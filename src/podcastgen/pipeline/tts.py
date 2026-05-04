"""Stage 7: TTS. Renders script.md to episode.mp3 using Kokoro + ffmpeg.

Steps:
  1. Read script.md and apply pronunciation rules.
  2. Split on blank lines (paragraph boundaries).
  3. Run Kokoro per paragraph; collect float32 mono PCM at the model's sample rate.
  4. Concatenate with 250ms silence between paragraphs.
  5. Write a temporary WAV via soundfile.
  6. Convert WAV -> MP3 via ffmpeg subprocess (mono, 64kbps).
  7. Tag the MP3 (title, artist, date, episode title) via mutagen.

Outputs:
  episodes/<feed>/<date>/episode.wav   (gitignored)
  episodes/<feed>/<date>/episode.mp3   (gitignored; copied to docs/ in feed stage)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import numpy as np

from podcastgen.config import Config, load_pronunciations
from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger
from podcastgen.util.pronounce import apply_pronunciations

log = get_logger(__name__)


SILENCE_BETWEEN_PARAGRAPHS_MS = 250


def run_tts(ctx: RunContext) -> None:
    script_path = ctx.work_dir / "script.md"
    if not script_path.exists():
        raise FileNotFoundError(f"script not found: {script_path}")

    raw = script_path.read_text(encoding="utf-8")
    rules = load_pronunciations()
    spoken = apply_pronunciations(raw, rules)

    paragraphs = _split_paragraphs(spoken)
    log.info("synthesizing %d paragraphs (%d spoken chars)",
             len(paragraphs), sum(len(p) for p in paragraphs))

    voice = ctx.cfg.tts.voices.get(ctx.feed) or "af_heart"
    sample_rate = ctx.cfg.tts.sample_rate
    audio = _synthesize(paragraphs, voice=voice, sample_rate=sample_rate, speed=ctx.cfg.tts.speed)

    duration_sec = int(len(audio) / sample_rate)
    log.info("synthesized %.1fs of audio", duration_sec)

    wav_path = ctx.work_dir / "episode.wav"
    _write_wav(audio, sample_rate, wav_path)

    mp3_path = ctx.work_dir / "episode.mp3"
    _wav_to_mp3(wav_path, mp3_path, bitrate=ctx.cfg.tts.output_bitrate)

    _tag_mp3(mp3_path, ctx)
    _write_audio_meta(ctx, duration_sec)
    log.info("wrote %s (%.2f MB)", mp3_path, mp3_path.stat().st_size / 1024 / 1024)


def _split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n")]
    return [p for p in paras if p]


def _synthesize(paragraphs: list[str], *, voice: str, sample_rate: int, speed: float) -> np.ndarray:
    from kokoro import KPipeline  # local import: heavy

    pipeline = KPipeline(lang_code="a")  # 'a' = American English

    silence = np.zeros(int(sample_rate * SILENCE_BETWEEN_PARAGRAPHS_MS / 1000), dtype=np.float32)
    chunks: list[np.ndarray] = []

    for i, para in enumerate(paragraphs, start=1):
        log.info("paragraph %d/%d (%d chars)", i, len(paragraphs), len(para))
        for _, _, audio_chunk in pipeline(para, voice=voice, speed=speed):
            arr = _to_float32_numpy(audio_chunk)
            chunks.append(arr)
        chunks.append(silence)

    if not chunks:
        return np.zeros(int(sample_rate * 0.1), dtype=np.float32)
    return np.concatenate(chunks)


def _to_float32_numpy(audio) -> np.ndarray:
    """Kokoro yields torch tensors; coerce to float32 numpy in [-1, 1]."""
    try:
        import torch  # type: ignore

        if isinstance(audio, torch.Tensor):
            return audio.detach().cpu().float().numpy().astype(np.float32, copy=False)
    except ImportError:
        pass
    return np.asarray(audio, dtype=np.float32)


def _write_wav(audio: np.ndarray, sample_rate: int, path: Path) -> None:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sample_rate, subtype="PCM_16")


def _wav_to_mp3(wav: Path, mp3: Path, *, bitrate: str) -> None:
    ffmpeg = _find_ffmpeg()
    if ffmpeg is None:
        raise FileNotFoundError(
            "ffmpeg not found on PATH or in winget install dir. "
            "Run: winget install Gyan.FFmpeg --scope user"
        )
    cmd = [
        ffmpeg,
        "-y",                # overwrite
        "-i", str(wav),
        "-ac", "1",          # mono
        "-b:a", bitrate,
        "-codec:a", "libmp3lame",
        str(mp3),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-500:]}")


def _find_ffmpeg() -> str | None:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    # Common winget install location
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    ]
    for base in candidates:
        if not base.exists():
            continue
        for exe in base.rglob("ffmpeg.exe"):
            return str(exe)
    return None


def _tag_mp3(mp3: Path, ctx: RunContext) -> None:
    from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TDRC, TIT2, TPE1
    from mutagen.mp3 import MP3

    feed_cfg = ctx.cfg.feeds[ctx.feed]
    meta = _load_script_meta(ctx)
    title = meta.get("title") or f"{ctx.feed} {ctx.date_str}"

    audio = MP3(str(mp3))
    try:
        tags = audio.tags or ID3(str(mp3))
    except ID3NoHeaderError:
        tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text="podcastgen"))
    tags.add(TALB(encoding=3, text=feed_cfg.title))
    tags.add(TDRC(encoding=3, text=ctx.date_str))
    audio.tags = tags
    audio.save()


def _load_script_meta(ctx: RunContext) -> dict:
    p = ctx.work_dir / "script_meta.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _write_audio_meta(ctx: RunContext, duration_sec: int) -> None:
    p = ctx.work_dir / "audio_meta.json"
    p.write_text(json.dumps({"duration_sec": duration_sec}), encoding="utf-8")
