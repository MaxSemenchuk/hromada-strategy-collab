# Research log — not the dataset

Everything in this folder is a dated snapshot from the pilot's growth
(7 → 13 → 23 → 30 → 46 → 54 hromadas), plus one-off ETL/matching outputs from
along the way. It exists for **provenance and reproducibility** — so any past
matching pass or claim in [README.md](../../README.md) can be traced back to
the exact data it ran on.

**If you want the current dataset, use [data/releases/](../releases/)
instead.** Nothing here is guaranteed current, deduplicated, or
production-quality — several files are near-duplicates of each other at
different pipeline stages (e.g. `embed_edges54.json` →
`embed_edges54_flagged.json` → `embed_edges54_weighted.json` →
`embed_edges54_final.json` is one matching run's successive refinements, not
four different datasets).

## What's here

- `hromadas_full*.json` — raw NocoDB API dumps of the `Hromadas` table at
  each corpus-size milestone.
- `hromada_sectors*.jsonl`, `matching_edges*.json`, `embed_edges*.json` —
  matching-pipeline inputs/outputs at each stage. See the "Methodology
  notes" section of the [root README](../../README.md#methodology-notes) for
  what changed between stages and why.
- `*_final.json`, `*_payload.json`, `*_final.json` (per-hromada) — one-off
  outputs from individual insert/structuring runs (Nizhyn, Novomoskovsk,
  Vinnytsia, Znob), kept as a record of what was actually written.
- `hromada_inserts.json` / `hromada_updates.json` — the bulk KATOTTG/population
  metadata import payload, already applied.
