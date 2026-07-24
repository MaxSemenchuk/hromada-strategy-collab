# Releases — the dataset

This is the canonical, redistributable data — CC BY 4.0, see
[DATA-LICENSE.md](../../DATA-LICENSE.md). Unlike
[data/research-log/](../research-log/), files here are meant to stay current
and self-describing, not a growth history.

## Contents

- **`hromadas.json`** — canonical hromada rows (metadata + LLM-extracted strategy
  fields). Includes derived **`PortalUrl`** (official site homepage when known).
  Regenerate with:

  ```bash
  yarn export-hromadas                    # live NocoDB (needs .env)
  yarn export-hromadas:snapshot           # offline from research-log snapshot
  yarn enrich-portal-urls                 # offline: recompute PortalUrl on current release
  ```

- **`hromada-portals.json`** — compact index of rows with non-null `PortalUrl`
  (Name, Katottg, PortalUrl, StrategyUrl, …). Same license as the release.
  Built by `yarn export-hromadas` / `yarn enrich-portal-urls`.
  Overrides for aggregator-only StrategyUrls:
  `data/sources/portal-url-overrides.json`.

- **`matching-edges.json`** — pairwise similarity scores (unverified hypotheses
  unless `known: true`). Method v6: 60% goals-cosine + 25% KSE geography +
  15% KSE existing partnership network. Regenerate with:

  ```bash
  yarn match
  yarn export-matching-edges
  yarn test-known-pairs
  yarn report-pin-corpus
  yarn test-tracks
  yarn build-matches-preview
  yarn graph-pin-matching   # needs data/cache/kse/ (lazy via enrich_from_kse)
  yarn priority-corpus-growth
  ```

  `known: true` marks a **curated** registry-confirmed subset used for hard
  regression (`yarn test-known-pairs`). Broader KSE check: every
  `mss_network>0` pair with Goals on both sides →
  `matching-edges.pin-corpus.json` (`yarn report-pin-corpus`) and the
  **PIN ∩ корпус** layer on the map. Do not promote all PIN edges to
  `known: true` (score already includes `mss_network`; circular).

  Next extractions that add PIN∩corpus coverage:
  `yarn priority-corpus-growth` → `corpus-growth-priority.json`.

  **Combined `score` is not a pure strategy match.** Each edge also has
  `track`:

  | `track` | Meaning | Typical use |
  |---------| |---------| | ------------- |
  | `thematic` | high goals-cosine, low geo | cold-start vision partners |
  | `operational` | high geo (not thematic) | convenient service co-sharers |
  | `mixed` | everything else | browse / combined ranking |

  Ranked slices (top 50, exclude `known`; operational also excludes pairs
  already in the KSE МСС network):

  - `matching-edges.thematic.json` — ranked by `goals_cosine`
  - `matching-edges.operational.json` — ranked by combined `score`

- **`donor-synergy.json`** — per-program portfolio slices from `DonorsPrograms`
  tags × matching edges (within-portfolio pairs, bridge pairs, hub degrees).
  Regenerate with `yarn donor-synergy` after exporting hromadas. Hypotheses
  only; tag absence ≠ “no program.”

## Coverage, read before using

- Live export covers **1,469** metadata rows; **77** have strategy extractions
  (`SourceQuality` full/partial/proxy). About **68** have non-empty `Goals`.
- This is pilot-stage, not a completed sweep of mainland Ukraine.
- KSE covariates are **not duplicated** here — joined at analysis time; see
  [docs/kse-synergy.md](../../docs/kse-synergy.md).
- Matching: **2,278** pairs, method v6; only `known: true` edges are
  registry-confirmed.
