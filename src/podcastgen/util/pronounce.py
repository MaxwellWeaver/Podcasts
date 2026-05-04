"""Pronunciation substitution. Applied to a script before it goes to Kokoro.

Three rule kinds (configured in `config/pronunciations.yaml`):
  say_letters: tokens spoken as their individual letters (GPU -> "G P U")
  say_word:    tokens spoken as a phonetic respelling (NATO -> "nay-toh")
  replace:     arbitrary literal substring replacement

Substitutions are whole-word and case-sensitive so that intended uppercase
acronyms aren't confused with lowercase common words.
"""

from __future__ import annotations

import re
from typing import Any


def apply_pronunciations(text: str, rules: dict[str, Any]) -> str:
    out = text

    # say_letters: insert spaces between letters
    for token in rules.get("say_letters", []) or []:
        spaced = " ".join(list(token))
        out = _whole_word_replace(out, token, spaced)

    # say_word: phonetic respelling
    for token, spell in (rules.get("say_word", {}) or {}).items():
        out = _whole_word_replace(out, token, spell)

    # replace: arbitrary literal
    for needle, repl in (rules.get("replace", {}) or {}).items():
        out = out.replace(needle, repl)

    return out


def _whole_word_replace(text: str, token: str, replacement: str) -> str:
    """Case-sensitive whole-word substitution.

    Word boundaries are non-alphanumeric on either side. Avoids mangling
    "DOGE" inside "DOGE-coin" but does match it inside "DOGE,".
    """
    pattern = r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])"
    return re.sub(pattern, replacement, text)
