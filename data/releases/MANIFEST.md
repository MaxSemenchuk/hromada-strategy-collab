# Releases — the dataset

This is the canonical, redistributable data — CC BY 4.0, see
[DATA-LICENSE.md](../../DATA-LICENSE.md). Unlike
[data/research-log/](../research-log/), files here are meant to stay current
and self-describing, not a growth history.

## Contents

- **`hromadas.json`** — canonical hromada rows (metadata + LLM-extracted strategy
  fields). Regenerate with:

  ```bash
  yarn export-hromadas                    # live NocoDB (needs .env)
  yarn export-hromadas:snapshot           # offline from research-log snapshot
  ```

- **`matching-edges.json`** — pairwise similarity scores (unverified hypotheses
  unless `known: true`). Method v6: 60% goals-cosine + 25% KSE geography +
  15% KSE existing partnership network. Regenerate with:

  ```bash
  yarn match
  yarn export-matching-edges
  yarn test-known-pairs
  ```

  `known: true` marks registry-confirmed МСС agreements used for validation.

## Coverage, read before using

- The snapshot export covers the **54-hromada text-mined pilot subset**, not
  all 1,469 mainland hromadas. Live NocoDB export includes full metadata rows.
- Only ~57 hromadas have actual strategy-text extraction — the rest show
  `null` in text fields. This is pilot-stage, not a completed sweep.
- KSE covariates are **not duplicated** here — joined at analysis time; see
  [docs/kse-synergy.md](../../docs/kse-synergy.md).
