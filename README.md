# Hromada Strategy Collaboration Mapping

**Product unit:** candidate **МСС** (inter-municipal cooperation) agreements —
pair · theme · legal form (one of five under Law 1508-VII) — instead of ad-hoc,
relationship-based matchmaking. Strategy-text NLP is **one discovery signal**
among geography, complementary resources/DREAM, explicit МСС language, and the
existing partnership network.

Spun out from the W3I ecosystem project (`w3i-network`) on 2026-07-23 as its own
codebase. **Canonical data store is local JSON** under [`data/releases/`](data/releases/)
(NocoDB sync archived under [`scripts/legacy/nocodb/`](scripts/legacy/nocodb/)).

Code is MIT-licensed; the dataset in [data/releases/](data/releases/) is
CC BY 4.0 — see [License & data](#license--data) below.

## Why

DOBRE (2024): the hardest IMC stage is **partner search & communication**, not
the legal form of the contract. This pilot surfaces **agreement candidates**
(who · about what · which of the five legal forms) with evidence — so hromadas
and facilitators are not limited to who already knows whom.

**Practitioner correction (Anatoliy Tkachuk / ІГС, 2026-08 — top expert input
for this study):** most agreements still follow contact between hromada heads;
tools do not replace that trust. Stronger product claim — reduce uncertainty,
surface mutual benefit («навіщо»), and prepare a safer first talk. Near-term
thematic window he flagged: **water / shared basins**. Full notes:
[internal/tkachuk-interview-2026-08.md](internal/tkachuk-interview-2026-08.md).

**Institutional context (2026-08):** no local elections since Oct 2020 under
martial law → *sticky heads* (denser personal trust networks now) but
*fragile heads* after future elections. Matching implication: lean on
`mss_network` / known pairs in this phase; do not treat head-pair edges as
permanent. Write-up:
[docs/mss-cooperation-research.md#frozen-elections-otg](docs/mss-cooperation-research.md#frozen-elections-otg).

Prior-art check (2026-07-20/21) found no public product doing this specific
thing. Adjacent efforts are single-hromada monitoring (U-LEAD) or manual МСС
matchmaking. Combining registry/network topology with strategy and resource
signals appears to be genuine whitespace.

## Method

1. **Gather signals** — strategy Goals (retrieve + structure), KSE geography /
   existing МСС network, complementary resource↔Challenges, explicit МСС language,
   DREAM/fiscal covariates. Strategy scan is signal #1, not the whole product.
2. **Package** — rule-based `suggested_theme` / `suggested_form` (`mss_suggest.py`)
   normalized to `package` + `signals[]` (`mss_candidate.py`). Five Law 1508-VII
   forms (+ agglomeration caveat). Never set `known: true` from suggestions.
3. **Rank within signals** — v7.1 pairwise: `0.60 × goals_cosine + 0.25 × geo +
   0.15 × mss_network` (hierarchy-aware Goals; bipartite×0.65 + centroid×0.35
   length/hub blend). Combined `score` is an internal rank for one path — UI
   leads with package + evidence chips.
4. **Validate** — curated `known: true` / `status: registry_known` against
   registry-confirmed agreements (`yarn test-known-pairs`).

## Status (as of 2026-08-10)

- **~1,463 mainland hromadas** in the metadata layer (KATOTTG code, oblast, rayon,
  type, population) — effectively the full universe, not a sample.
- **~293 hromadas** text-mined for strategy content: **274** full-strategy, **18**
  partial, **1** proxy-info; all have non-empty `Goals` for matching. Grown from
  the original 77-hromada pilot via the GISRR batch fold-in, wave-C, and
  western-PIN-hub extraction passes (see
  [project-history.md](docs/project-history.md)). (Honest retrieval nulls are
  recorded separately where no strategy could be found.)
- **181 hromadas** (12%) tagged with at least one donor/technical-assistance
  program (DOBRE, DECIDE, GIZ, ПРООН/UNDP, EGAP, DESPRO, МФ Відродження, U-LEAD,
  Ре:Форм, STRATEGY LAB, JICA, ЄІБ, ЄБРР, AFD) — a floor, not a ceiling (`DonorsPrograms` on
  the release JSON).
- Matching **v7.1** (`0.60 × goals_cosine + 0.25 × geo + 0.15 × mss_network`):
  goals_cosine prefers operational lines when hierarchy is present
  (`goals-hierarchy.json`) and blends bipartite soft-align with a document
  centroid (length / hub mitigation). Combined score weights unchanged from v6.
- Extra layers (not folded into combined `score`):
  **complementary** (resource/DREAM ↔ Challenges), **explicit-ask** (МСС language
  in strategy text), **resources** / **DREAM priorities**, **twinning** (UA–EU
  sister cities via SKEW + strategy mentions — `yarn twinning`).
- Stakeholder site under [`docs/`](docs/) (GitHub Pages): landing · matches ·
  funds · resources · PIN map (discovery-signal overlays). Browse sidecar:
  `data/releases/mss-candidates.json`. Still pilot / concept-validation stage.

**Read this before reusing the data:** the ~293-hromada text-mined subset is a
pilot sample, not a completed sweep of the 1,463 — most rows will have no
strategy content yet. Every candidate is an **unverified hypothesis** unless
`known: true` / `status: registry_known`.

Full narrative history (every pass, every false start, every honest negative finding)
lives in [docs/project-history.md](docs/project-history.md) — migrated from Claude
Code project memory on spin-out and kept current here. Cursor agents load
[.cursor/rules/hromada-project.mdc](.cursor/rules/hromada-project.mdc) for the
same guardrails.

## Repo layout

```
scripts/
├── structure-hromada-strategy.ts        # structured JSON → hromada-output/ + optional --write-release
├── export-hromadas.ts                   # research-log snapshot → data/releases/hromadas.json
├── hromada-output/                      # per-hromada structured JSON (provenance)
├── retrieval/                           # CKAN search, download-raw, fetch-mss-registry, batch queue
├── analysis/                            # matching, PIN map, sidecars (canon: match.py v7.1)
│   └── legacy/                          # archived Pass 1–5 / early embed scripts (do not run)
└── legacy/nocodb/                       # archived NocoDB sync (setup/import/live export)
data/
├── sources/       # reference registries (KATOTTG classifier extract, Tags table dump, hierarchy overrides)
├── releases/      # THE dataset — canonical, current, CC BY 4.0 (see data/releases/MANIFEST.md)
├── cache/         # gitignored re-fetchable sources (KSE pulls, МСС registry XLSX, …)
└── research-log/  # dated growth snapshots (7→13→23→30→46→54 hromadas) — provenance, not the dataset
docs/                             # GitHub Pages site root (see docs/README.md)
├── index.html                    # landing «О проєкті» (all stakeholder audiences)
├── matches.html                  # known pairs + thematic/operational/complementary/explicit-ask
├── funds.html                    # donor portfolio: shared next grant / bridges / hubs
├── resources.html                # KSE resource proxies × DREAM priorities
├── strategy-writing-guide.md     # how to write strategies that surface МСС signals
├── donor-programs.md             # DOBRE / EGAP / U-LEAD / GIZ / USAID… reference
├── corpus-growth.md              # priority corpus growth checklist
├── mss-pin-matching-graph.html   # full PIN map + matching overlays
├── hromada-project-passport.html # legacy redirect → index.html
├── hromadas-schema.md            # field schema, controlled vocab, data-source notes
├── external-data-sources.md      # findings on external datasets (e.g. KSE-Loc-Data-Hub)
└── kse-synergy.md                # division of labor vs KSE, join key, W3I outreach use case
internal/
└── outreach-messages.md          # draft stakeholder outreach copy — not part of the dataset, not for public reuse
REFERENCES.md                     # theoretical grounding — network governance, IMC, institutional diversity
docs/mss-cooperation-research.md  # DOBRE bottleneck thesis, МСС forms/procedure, ЗП 11412, theme/form roadmap
docs/ua-eu-twinning.md            # UA–EU sister cities: format, SKEW/C4C, cases (≠ МСС)
docs/donor-programs.md            # donor/fund cheat-sheet (DOBRE, EGAP, U-LEAD, GIZ, USAID…)
LICENSE / DATA-LICENSE.md         # MIT (code) / CC BY 4.0 (data) — see License & data below
```

## Stakeholder site (GitHub Pages)

Static site in [`docs/`](docs/) — landing («О проєкті»), matching candidates, fund
portfolio view, МСС map, shared top menu.

**URL (after Pages is enabled):** https://maxsemenchuk.github.io/hromada-strategy-collab/

One-time setup: repo **Settings → Pages → Source: GitHub Actions**, then push to `main`
(or run the **Deploy GitHub Pages** workflow). Local preview: `cd docs && python3 -m http.server 8765`.

> The repository is currently private — public Pages needs a public repo (or GitHub Pro
> for private Pages). Collaborators with repo access can still use the workflow URL once enabled.

Raw strategy PDFs/DOC/HTML and the МСС registry XLSX are kept as a **local
cache** for re-extraction and alternate analyses — not committed, not part of
the public release. Populate with:

```bash
yarn download-raw --all          # queue URLs → scripts/retrieval/raw/ (gitignored)
yarn fetch-mss-registry          # data.gov.ua registry → data/cache/mss/
```

See [scripts/retrieval/README.md](scripts/retrieval/README.md).

## Setup

```bash
yarn install
# Optional: cp .env.example .env  (no remote DB required)
```

## Data store: local JSON

**Canonical working dataset** is [`data/releases/hromadas.json`](data/releases/hromadas.json)
(plus matching / sidecar releases next to it). Matching, map build, and the
stakeholder site all read from `data/releases/`.

```bash
# always writes scripts/hromada-output/<name>.json
yarn structure-hromada --name "…" --json structured.json --write-release
# → upserts Goals/Projects/… into data/releases/hromadas.json by Name
yarn match   # reads the release JSON
```

Former NocoDB setup/import/live-export scripts live under
[`scripts/legacy/nocodb/`](scripts/legacy/nocodb/) and are **not** wired into yarn.

## License & data

Code (`scripts/`) is MIT. The dataset in [data/releases/](data/releases/) is
**CC BY 4.0** — see [DATA-LICENSE.md](DATA-LICENSE.md) for attribution
requirements and upstream source credits (data.gov.ua, DREAM, the МСС
registry). [data/research-log/](data/research-log/) is provenance material,
not the maintained dataset — read its README before building on it.
[internal/](internal/) holds private outreach drafts (`outreach-messages.md`;
optional local `outreach.html` is gitignored — not on GitHub Pages).

If this repo becomes public: this section, the license files, and the
`data/releases/` split exist specifically so the repo can be opened as an
open-data asset (for other researchers or a hromada-data hackathon) without
also exposing draft outreach material or an unlabeled, partially-complete
snapshot as if it were a finished dataset.

## Usage

```bash
# Persist in-session structured JSON to hromada-output/
yarn structure-hromada --name "Ніжинська громада" --json structured.json

# Upsert strategy fields into local release JSON
yarn structure-hromada --name "Ніжинська громада" --json structured.json --write-release

# Optional: re-normalize release from a research-log snapshot
yarn export-hromadas
yarn export-hromadas:snapshot

# Recompute matching edges (v7.1: goals + length/hub blend + KSE geo + mss)
# Combined score ≠ pure strategy match — also writes track labels + dual slices
# export-matching-edges also adds fiscal/DREAM boost + suggested_theme/form (score unchanged)
yarn match && yarn export-matching-edges && yarn test-length-norm && yarn test-known-pairs && yarn report-pin-corpus && yarn test-tracks && yarn test-mss-suggest && yarn build-matches-preview

# Agent-centric recommendations for one seed (re-rank existing edges; no rematch)
yarn recommend-for --seed "Галицька" --motivation water_basin
yarn test-recommend-for && yarn build-recommend-preview
# docs: agent-centric vs global score → docs/agent-centric-recommendations.md

# Hierarchy + explicit МСС language + complementary (separate from combined score)
yarn build-goals-hierarchy
yarn extract-mss-intents
yarn complementary-match
yarn twinning                    # UA–EU twinning (SKEW cache + strategy mentions)
yarn twinning --offline          # rebuild from data/cache/twinning/ only
yarn graph-pin-matching

# Structural proxies (KSE budget/DFRR/competence/health) + DREAM revealed priorities
yarn hromada-resources
yarn fetch-dream                 # ~16k ideas; resumes data/cache/dream/
yarn fetch-dream --limit 200     # smoke test
yarn build-resources-preview
```

Track labels on each edge (`thematic` / `operational` / `mixed`) and ranked
slices `matching-edges.thematic.json` / `matching-edges.operational.json` are
documented in [data/releases/MANIFEST.md](data/releases/MANIFEST.md).
`matching-edges.json` is a **slim** compact score matrix (full pairwise for
lab ranks); IMC `package` / `signals` live on `mss-candidates.json` and the
slice files (rich local cache under `data/cache/matching/` after export).
`yarn report-pin-corpus` writes the broader KSE PIN∩corpus check;
`yarn priority-corpus-growth` lists next strategy extractions that add overlap
([docs/corpus-growth.md](docs/corpus-growth.md)).

Fund portfolio lenses (within-program pairs, bridge pairs, hubs) live in
`donor-synergy.json` and on the stakeholder site at [`docs/funds.html`](docs/funds.html).
Resource / competence covariates: `hromada-resources.json`; DREAM project
priorities: `dream-priorities.json`; complementary / explicit-ask edges:
`matching-edges.complementary.json` / `matching-edges.explicit-ask.json`;
UA–EU twinning: `twinning-partners.json`
(see [docs/external-data-sources.md](docs/external-data-sources.md) and
[matches.html](docs/matches.html)). Writing guide:
[docs/strategy-writing-guide.md](docs/strategy-writing-guide.md).

## Scaling retrieval

Batch workflow for growing the corpus beyond the current pilot: see
[scripts/retrieval/README.md](scripts/retrieval/README.md). Quick start:

```bash
yarn ckan-search --out scripts/retrieval/ckan-candidates.json
# pick URLs → batch-queue.json → download → structure in-session →
# yarn structure-hromada --json … --write-release
yarn match
```

## Methodology notes

- **Sector-tag overlap is useless as a matching signal.** The standard Мінрегіон
  template makes every hromada strategy formally touch nearly all sectors — every
  pair scores 0.75–1.0 Jaccard regardless of actual similarity. Good for coarse
  browsing/filtering, not for matching.
- **Raw embeddings fail on this corpus.** Government strategy documents share so
  much bureaucratic register that generic sentence embeddings pick up "this is a
  government strategy" as the dominant signal. Fix: mean-center (subtract the
  corpus-average sub-goal vector) before comparing, to isolate what's actually
  distinctive per hromada.
- **Long “comprehensive” strategies create hub false positives.** Pure bipartite
  avg-of-best-line matches let two thick, all-sector docs score well without a
  shared profile (Pass 4: Poltava↔Zhytomyr). v7.1 blends bipartite soft-alignment
  with a DF-weighted **document-centroid** cosine of the same centered subgoals
  (`yarn test-length-norm`). Same release also restores true pairwise cosine
  (`A @ B.T`); v4–v7 accidentally sliced embedding coordinates via `np.ix_`.
- **Goals-cosine similarity finds thematic/strategic-vision matches, not operational
  ones.** A real, confirmed МСС pair cooperating on a shared CNAP office scored only
  rank #132 of 253 on pure cosine — that kind of back-office cooperation needs a
  proximity/capacity signal, not text similarity. A disclosed weighted combination
  (60% goals-cosine + 40% oblast/rayon-adjacency) recovered it to rank #6.
  Same split in product language: **tourism / clusters** → `схожа стратегія`
  (multi-purpose IMC; NLP’s comparative advantage); **water / ЦНАП / waste** →
  `зручний сусід` (single-purpose with neighbours; geo does the work, text only
  confirms when a shared asset is named). IMC-ladder mapping in
  [REFERENCES.md](REFERENCES.md#how-imc-typologies-map-onto-this-projects-method).
- **Template collisions produce false positives at scale.** Two hromadas using the
  same external consulting template can produce near-identical goal-section wording
  with zero real substantive overlap. Fix was a narrow, explainable rule (flag
  near-verbatim subgoal-line duplicates, difflib ratio ≥0.98) rather than a
  corpus-wide statistical reweighting, which over-corrected and buried the real
  known cluster on a corpus this small.
- **Cost control matters.** Full in-session Agent-based retrieval+structuring burns
  60–150k tokens per hromada, mostly fighting anti-bot protection, not reasoning.
  Split retrieval (scripts + deterministic download) from structuring (in-session
  on already-extracted text, then `yarn structure-hromada --json` to persist).
  External LLM APIs were tried as a cost stopgap and removed from the repo path.

See [docs/hromadas-schema.md](docs/hromadas-schema.md) for the full field schema and
[REFERENCES.md](REFERENCES.md) for the theoretical literature this approach draws on.

## Related datasets

This project deliberately **does not duplicate** hromada-level covariate work
already done elsewhere. The primary complement is
**[KSE-Loc-Data-Hub](https://github.com/kse-ua/KSE-Loc-Data-Hub)** (KSE
Institute; Zenodo [10.5281/zenodo.15267573](https://doi.org/10.5281/zenodo.15267573)) —
budget, geography, e-dem, existing МСС agreements, war status, and ~130 other
vars for all 1,469 mainland hromadas. We join on **KATOTTG** and consume those
covariates at analysis time; KSE does not publish strategy-text extractions or
goals-similarity candidate pairs — that is what this repo adds.

See [docs/kse-synergy.md](docs/kse-synergy.md) for division of labor, edem
missingness caveats, what we contribute back, and the W3I Civic Tech Lab outreach
use case (`edem_total` × goals-similarity). Deep KSE review:
[docs/external-data-sources.md](docs/external-data-sources.md#kse-loc-data-hub).
