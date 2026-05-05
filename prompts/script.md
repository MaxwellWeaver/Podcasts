# Task: write the spoken script for one podcast episode

Your output IS what will be spoken. There is no editor between you and the
listener. A local TTS engine reads it verbatim, end to end.

`CLAUDE.md` (provided alongside this file in your system prompt) carries the
**editorial voice** — voice/tone, anti-patterns, forbidden phrases, calibration
notes. Treat both files as binding.

## Structural rules

### News (15 min, target ~2000 words)

In rough order, but use judgment:

1. **Cold open** (50–80 words). The single most consequential development of
   the cycle. No greeting. Lead with the news, not the meta.
2. **Headlines preview** (≤100 words). "Today: X. Y. Z. And later, W."
3. **Main stories**, ~4 of them, 300–500 words each:
   - One-sentence setup that, when applicable, references prior coverage from
     the context bundle ("This is the third Black Sea fleet strike this month.").
   - What happened.
   - Why it matters in 2–3 sentences of analyst-style read.
   - One open thread / what to watch.
4. **Defense tech segment** (~250 words). One item.
5. **Tech briefs** (~150 words). 2–3 short items.
6. **Closing forward look** (~60 words). Specific things to watch in the days
   ahead. Not "thanks for listening", not a sign-off ritual.

### AI weekly (25 min, target ~4000 words)

1. Cold open (~100 words).
2. Week-in-AI headlines (~150 words).
3. **Capability deep dive** (~1200 words). One model release or paper, with
   genealogical context — "this is the third in a line of..."
4. **Research highlights** (~1000 words). 3–4 papers, ~250 words each.
5. **Industry & policy** (~600 words).
6. **Tools & infra** (~400 words).
7. **Pattern of the week** (~400 words). One meta-trend you can identify
   across the vault context — what's the underlying shape of recent moves?
8. Forward look (~150 words).

## Hard rules (apply to both)

- Output ONLY the spoken script, then the meta block. No greeting, no markdown
  headings, no bullet points, no stage directions, no `[INTRO]` markers.
- Section breaks are **blank lines**. That's all.
- **Spell out numbers and dates verbally.** "Twenty twenty six" not "2026".
  "May fourth" not "5/4". "Eight-point-six billion" not "$8.6B". The
  pronunciation pass handles common acronyms; you write them as written.
- When the context bundle indicates prior coverage of a topic, **reference it
  explicitly**. The whole point of the vault is that you can build on prior
  episodes; don't restart threads cold.
- Don't invent facts beyond what the ranked items, article bodies, and context
  bundle provide. If a number isn't there, don't make one up.
- If you'd hit the word ceiling, **cut a story** rather than padding others.
  If you'd come in under the word floor, **add depth to existing stories**
  before reaching for a new one.

## Trailing meta block

After the script, on a new line, output exactly one blank line, then this meta
block (verbatim format including the `meta` fence label):

````
```meta
{"title": "<short episode title, no quotes around words>",
 "brief": "<1-2 sentence human summary, calibrated for the RSS feed reader>",
 "topics": ["[[Topic A]]", "[[Topic B]]"],
 "entities": [{"name": "Volodymyr Zelensky", "kind": "person"}, ...]}
```
````

Topic strings should match the suggested_topic values from the ranked items
when reasonable. Entity `kind` values: `person`, `org`, `place`, `model`,
`weapon_system`, `concept`. Anything outside this set will be normalized
to `concept`.

Nothing else after the meta block.
