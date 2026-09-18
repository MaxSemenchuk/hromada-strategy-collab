---
name: intl-harvest
description: Bounded harvest of UA hromada international cooperation (twinning / 3668 / Interreg-adjacent news). One source per tick, 30% token budget, write candidates to research-log only. Use when the user asks for autonomous intl scrape, harvest ticks, Nordic/C4C/SALAR/VNG/UBC news-pass, or leftover Auto-token harvest.
---

# Intl harvest (bounded, not a web crawler)

This is **not** “scrape the internet”. Each wake processes **one** queued source, extracts named UA–foreign municipal pairs, and stops. Unbounded search dumps HTML into context, collides names, and invents pairs.

## Token budget (Auto mode)

Treat **30% of unused Auto tokens** as a hard cap for this tick:

- **1 source** from `data/sources/intl-harvest-queue.json` (`status: pending`).
- **≤8 HTTP fetches**. Prefer official lists / news APIs over HTML bios.
- Do **not** paste full HTML/PDF into the prompt. Extract `{ua, partner, country, date, url}` then discard the page.
- Stop when the source is done **or** the fetch cap is hit — whichever first. Write what you have.
- Do not start a second source “while tokens remain”.

## Write path

Append JSONL (one object per candidate) to:

`data/research-log/intl-harvest/YYYY-MM-DD-<source-id>.jsonl`

Then mark the queue item `done` / `partial` / `blocked` and set `last_run`.

**Never** in a harvest tick:

- set `known: true`
- fold into v7 `score`
- write straight into `twinning-partners.json` / `intl-agreements.json`
- map raion RDA / райрада / ODA onto the host city
- ingest Wikipedia twin-town lists (Crimea / RU noise)
- scrape all ~598 Cities4Cities profile HTML pages (those are **seeking bios**, not a pair registry)
- scrape Kyiv city / Kyiv districts / Crimea Yalta
- bypass Ministry Tableau export controls

Reviewed pairs later fold into `data/sources/twinning-nordic-pairs.json` or `twinning-name-aliases.json` via a **separate** explicit request.

## Candidate shape

```json
{
  "ua_name": "",
  "katottg": null,
  "partner_name": "",
  "partner_country": "SE",
  "since": null,
  "source_url": "",
  "evidence": "one sentence",
  "confidence": "directory|news_mention|hypothesis",
  "skip_reason": null
}
```

Resolve KATOTTG against `hromadas.json` when cheap; leave `null` if ambiguous (several Миколаїв / Ямпіль / Слобожанське). Prefer city over rural namesake only with oblast evidence.

## Tick steps

1. Read this skill and the queue file.
2. Pick the first `pending` item (or the id named in the wake prompt).
3. Fetch the listed URLs only. Follow at most 3 in-domain links if the index page is a hub.
4. Dedup against existing `twinning-partners.json` partner names (case-insensitive) and against already-harvested JSONL for this source.
5. Write JSONL + update queue status.
6. In chat: 5–10 lines — source, N new candidates, N skipped, next pending id. No tables of raw HTML.

## Layers stay distinct

Twinning ≠ Law 3668-IX ≠ Interreg LPA ≠ C4C seeking. Tag `layer` on each candidate: `twinning` | `law3668` | `interreg` | `seeking`.
