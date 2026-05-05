# Task: extract per-topic and per-entity summaries from a finished script

The script you're given was just narrated as one episode of the podcast. The
podcast keeps a persistent vault of running notes — one file per topic, one
per entity — that future episodes consult to avoid restarting threads from
scratch.

Your job is to write **one or two sentences per topic and per entity** that
capture **what THIS episode contributed** to that thread. The vault writer
will append your text to the relevant files.

## Critical: episode-specific, not encyclopedic

Bad (general): "Ukraine is at war with Russia. Zelensky is its president."
Good (episode-specific): "Patriot interceptor supply for Kyiv now competes with
the Persian Gulf carrier deployment; one European diplomat told Foreign Policy
'everything depends on Iran'."

If a topic or entity is mentioned only in passing, your summary should reflect
that — don't pad with general background.

## What "specific" looks like

- Quotes the actual development, person, or number from the script
- Names what the new development is, not just that there was one
- Connects to prior coverage where the script does so explicitly
- Does NOT introduce facts that aren't in the script

## Output format

Return strict JSON:

```
{
  "topics": {
    "[[Topic A]]": "Episode-specific summary sentence(s).",
    "[[Topic B]]": "..."
  },
  "entities": {
    "Person Name": "Episode-specific summary sentence(s).",
    "Organization Name": "..."
  }
}
```

Use the EXACT topic strings (with `[[` `]]`) and entity names you were given —
the vault writer keys off them. If a topic or entity wasn't actually substantive
in the script, you may omit it from the output.

No prose outside the JSON, no markdown fences, no commentary.
