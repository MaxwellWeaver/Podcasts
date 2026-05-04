"""LLMClient backed by the Claude Code CLI in non-interactive (-p) mode.

Calls `claude -p --output-format json --model <model>` with the prompt on stdin.
Stdin avoids Windows command-line quoting issues for multi-line prompts.

Output schema (relevant fields):
    {
      "result": "<text>",
      "is_error": false,
      "usage": {"input_tokens": N, "output_tokens": N, "cache_read_input_tokens": N, ...},
      "total_cost_usd": 0.0123,
      ...
    }
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from podcastgen.config import Config
from podcastgen.llm.client import LLMClient, LLMResponse, Tier
from podcastgen.util.logging import get_logger

log = get_logger(__name__)


class ClaudeCLIError(RuntimeError):
    pass


class ClaudeCLIClient(LLMClient):
    def __init__(self, cfg: Config, *, log_path: Path | None = None) -> None:
        self.cfg = cfg
        self.cli_path = cfg.llm.cli_path
        self.tiers = cfg.llm.tiers
        self.timeout = cfg.llm.timeout_sec
        self.retries = cfg.llm.retries
        self.backoff = cfg.llm.retry_backoff_sec
        self.log_path = log_path  # JSONL of every call, for debugging + cost tracking

    def complete(
        self,
        prompt: str,
        *,
        tier: Tier,
        system: str | None = None,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = self.tiers[tier]
        full_prompt = self._build_prompt(prompt, system=system, json_mode=json_mode)

        cmd = [
            self.cli_path,
            "-p",
            "--output-format", "json",
            "--model", model,
        ]

        last_err: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                t0 = time.monotonic()
                proc = subprocess.run(
                    cmd,
                    input=full_prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=self.timeout,
                    check=False,
                )
                elapsed = time.monotonic() - t0

                if proc.returncode != 0:
                    raise ClaudeCLIError(
                        f"claude exit {proc.returncode}: {proc.stderr[:500]}"
                    )

                data = self._parse_output(proc.stdout)
                if data.get("is_error"):
                    raise ClaudeCLIError(
                        f"claude is_error=true: {data.get('result', '')[:500]}"
                    )

                text = data.get("result", "")
                if json_mode:
                    text = self._strip_json_fences(text)
                    json.loads(text)  # validate; raises if malformed

                resp = self._make_response(text, data)
                self._log_call(tier, model, full_prompt, resp, elapsed, attempt)
                return resp

            except (subprocess.TimeoutExpired, ClaudeCLIError, json.JSONDecodeError) as e:
                last_err = e
                log.warning("claude attempt %d/%d failed: %s", attempt, self.retries, e)
                if attempt < self.retries:
                    time.sleep(self.backoff * attempt)

        raise ClaudeCLIError(f"all {self.retries} attempts failed: {last_err}")

    @staticmethod
    def _build_prompt(prompt: str, *, system: str | None, json_mode: bool) -> str:
        parts = []
        if system:
            parts.append("SYSTEM:\n" + system + "\n\n---\n")
        parts.append(prompt)
        if json_mode:
            parts.append(
                "\n\nRespond with ONLY a single valid JSON value. "
                "No prose, no markdown fences, no commentary before or after."
            )
        return "".join(parts)

    @staticmethod
    def _parse_output(stdout: str) -> dict[str, Any]:
        stdout = stdout.strip()
        if not stdout:
            raise ClaudeCLIError("empty stdout from claude CLI")
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            raise ClaudeCLIError(f"non-JSON stdout (first 500 chars): {stdout[:500]}") from e

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            # ```json ... ``` or ``` ... ```
            t = t.split("\n", 1)[1] if "\n" in t else t[3:]
            if t.endswith("```"):
                t = t[:-3]
        return t.strip()

    @staticmethod
    def _make_response(text: str, data: dict[str, Any]) -> LLMResponse:
        usage = data.get("usage", {}) or {}
        in_toks = (
            usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
        ) or None
        return LLMResponse(
            text=text,
            raw=data,
            input_tokens=in_toks,
            output_tokens=usage.get("output_tokens"),
            cost_usd=data.get("total_cost_usd"),
        )

    def _log_call(
        self,
        tier: str,
        model: str,
        prompt: str,
        resp: LLMResponse,
        elapsed: float,
        attempt: int,
    ) -> None:
        if self.log_path is None:
            return
        entry = {
            "tier": tier,
            "model": model,
            "elapsed_sec": round(elapsed, 2),
            "attempt": attempt,
            "prompt_chars": len(prompt),
            "response_chars": len(resp.text),
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
