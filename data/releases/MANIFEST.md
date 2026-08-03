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
  yarn export-hromadas                    # normalize research-log snapshot → release
  yarn export-hromadas:snapshot           # same (alias)
  yarn enrich-portal-urls                 # offline: recompute PortalUrl on current release
  # (live NocoDB pull archived under scripts/legacy/nocodb/)
  ```

- **`hromada-portals.json`** — compact index of rows with non-null `PortalUrl`
  (Name, Katottg, PortalUrl, StrategyUrl, …). Same license as the release.
  Built by `yarn export-hromadas` / `yarn enrich-portal-urls`.
  Overrides for aggregator-only StrategyUrls:
  `data/sources/portal-url-overrides.json`.

- **`mss-candidates.json`** — thin **product browse** sidecar: curated
  `registry_known` pairs + top hypotheses from explicit-ask / thematic /
  complementary / operational slices. Each row is an **МСС candidate agreement**
  with `package` (theme · legal form · `label_uk`) and `signals` (discovery
  evidence). Not a full pairwise dump; do not browse primarily by `form_id`.
  Built by `yarn export-matching-edges` via `mss_candidate.py`.

- **`matching-edges.json`** — pairwise similarity scores (unverified hypotheses
  unless `known: true`). Method v7.1: 60% goals-cosine (hierarchy-aware;
  bipartite×0.65 + document-centroid×0.35 length/hub blend) + 25% KSE
  geography + 15% KSE existing partnership network. Product framing: each edge
  also carries `kind: mss_candidate`, `package`, `signals`, `discovery_primary`,
  `status`. Combined `score` ranks one discovery path — not “strategy match”.
  Regenerate with:

  ```bash
  yarn match
  yarn export-matching-edges
  yarn test-length-norm
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
  - `matching-edges.operational.json` — ranked by `operational_score`
    (geo + fiscal similarity + DREAM sector overlap) when present, else `score`
  - `matching-edges.complementary.json` — **separate** layer
    (`yarn complementary-match`): DREAM/Strengths/resource of A ↔ Challenges of B
  - `matching-edges.explicit-ask.json` — **separate** layer
    (`yarn extract-mss-intents`): МСС / кооперація language in strategy fields
  - `goals-hierarchy.json` — strategic / operational goal lines (sidecar for v7)
  - `mss-intents.json` — per-hromada quotes of explicit МСС language

  Operational boost fields on every edge (`fiscal_similarity`, `dream_overlap`,
  `operational_score`) do **not** change v7 combined `score` weights
  (`0.60×goals + 0.25×geo + 0.15×mss_network`). Goals cosine may use hierarchy
  when operational lines exist (`yarn build-goals-hierarchy`).

  After tracks, `yarn export-matching-edges` attaches an **IMC package
  hypothesis** via `mss_suggest.py`, then normalizes via `mss_candidate.py`
  (never `known: true`, does not change score):

  | Field | Meaning |
  |-------|---------|
  | `suggested_theme` / `package.theme` | ЦНАП, туризм, відходи, … |
  | `suggested_form` / `package.form` | one of 5 Law 1508-VII forms (+ agglomeration caveat) |
  | `package.label_uk` | human line for UI, e.g. «ЦНАП — делегування» |
  | `signals` | discovery evidence (`strategy_goals`, `geo`, `complementary`, …) |
  | `discovery_primary` | main signal that surfaced the pair |
  | `status` | `hypothesis` \| `registry_known` |
  | `suggest_confidence` | low · medium · high |
  | `suggest_rationale` | short why (rules + optional registry prior) |

  **Legal forms (product types)** ≠ **signals** (how we found the pair).
  Rules and DOBRE context: [docs/mss-cooperation-research.md](../docs/mss-cooperation-research.md).
  Complementary / explicit-ask edges get the same fields from their own yarn
  commands.

- **`donor-synergy.json`** — per-program portfolio slices from `DonorsPrograms`
  tags × matching edges (within-portfolio pairs, bridge pairs, hub degrees).
  Regenerate with `yarn donor-synergy` after exporting hromadas. Hypotheses
  only; tag absence ≠ “no program.”

- **`hromada-resources.json`** — structural proxies per KATOTTG (KSE budget /
  ДФРР / community competence / health / war status + own-income per capita).
  Regenerate with `yarn hromada-resources`. Missing competence/health ≠ zero.
  Not a substitute for `Goals` text.

- **`dream-priorities.json`** — revealed project priorities from the DREAM
  public API, aggregated to hromada via settlement→hromada CATOTTG map.
  Regenerate with `yarn fetch-dream` (caches under `data/cache/dream/`).
  Hypotheses only; cancelled ideas excluded.
  Site preview: `yarn build-resources-preview` → `docs/assets/resources-preview.json`
  (`docs/resources.html`).

- **`twinning-partners.json`** — **UA–EU municipal twinning** (separate from
  domestic МСС). Sources: SKEW German–Ukrainian registry (`yarn twinning`,
  cache `data/cache/twinning/`); Cities4Cities news-title pairs + municipality
  `markers.json` (`c4c_url` = listed for matchmaking); strategy named cities.
  Aliases: `data/sources/twinning-name-aliases.json`. Does **not** fold into
  matching `score`. Preview: `docs/assets/twinning-preview.json`.

## Coverage, read before using

- Live export covers **1,469** metadata rows; **77** have strategy extractions
  (`SourceQuality` full/partial/proxy). About **68** have non-empty `Goals`.
- This is pilot-stage, not a completed sweep of mainland Ukraine.
- KSE covariates are **not duplicated** here — joined at analysis time; see
  [docs/kse-synergy.md](../../docs/kse-synergy.md).
- Matching: **2,278** pairs, method v6; only `known: true` edges are
  registry-confirmed.
