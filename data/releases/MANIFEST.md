# Releases — the dataset

This is the canonical, redistributable data — CC BY 4.0, see
[DATA-LICENSE.md](../../DATA-LICENSE.md). Unlike
[data/research-log/](../research-log/), files here are meant to stay current
and self-describing, not a growth history.

## Contents

- **`matching-edges.json`** — pairwise similarity scores between hromadas'
  strategy `Goals` text (946 pairs, 54-hromada corpus, mean-centered
  sub-goal-level embeddings, `intfloat/multilingual-e5-small`). `known: true`
  marks a real, registry-confirmed МСС agreement used for validation, not a
  claim about the other pairs — every other pair is an **unverified
  hypothesis**, not a confirmed relationship. See
  [README.md#methodology-notes](../../README.md#methodology-notes) for how
  this was computed and where it's known to fail (back-office cooperation,
  template-collision false positives).

- **`hromadas.json`** — *not yet generated in this pass.* The existing dated
  snapshots in `research-log/` turned out to be partial exports (different
  subsets of columns at different pipeline stages — see that folder's
  README), and hand-merging them risked producing a silently wrong "canonical"
  file. The correct source is a live pull from NocoDB: run

  ```bash
  yarn export-hromadas
  ```

  (needs `NOCODB_TOKEN` / `NOCODB_TABLE_HROMADAS` in `.env`, see
  [scripts/export-hromadas.ts](../../scripts/export-hromadas.ts)) to populate
  `hromadas.json` + `hromadas.manifest.json` here. Not yet run against the
  live table as part of this restructuring — do that before treating this
  folder as ready to publish.

## Coverage, read before using

- 1,469 mainland hromadas have basic metadata (KATOTTG, oblast, rayon, type,
  population) once `hromadas.json` is generated.
- Only ~57 of those have actual strategy-text extraction
  (`SourceQuality` set) — the rest will show `null` in the text fields. This
  is a pilot-stage subset, not a gap in an otherwise-complete dataset.
- See [data/sources/](../sources/) for the raw KATOTTG classifier extract and
  Tags dump these are built from, and
  [docs/external-data-sources.md](../../docs/external-data-sources.md) for a
  complementary open dataset (KSE-Loc-Data-Hub) covering general hromada
  covariates (budget, population, e-participation, existing МСС agreements)
  that this project does not duplicate.
