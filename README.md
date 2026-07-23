# Hromada Strategy Collaboration Mapping

Corpus-level NLP matching of Ukrainian territorial-community (**hromada**) development
strategies, to systematically surface candidates for **МСС** (inter-municipal
cooperation) — instead of relying on the ad-hoc, relationship-based matchmaking that
is how most МСС partnerships get formed today.

Spun out from the W3I ecosystem project (`w3i-network`) on 2026-07-23 as its own
codebase. **The NocoDB database is currently shared** with the main W3I base — see
[Shared database](#shared-database) below.

Code is MIT-licensed; the dataset in [data/releases/](data/releases/) is
CC BY 4.0 — see [License & data](#license--data) below.

## Why

A natural extension of W3I's Civic Tech Lab / Digital Democracy Lab work, which
already engages individual hromadas one at a time. This project asks a systemic
question instead: *which hromadas should be talking to each other, or to W3I,* based
on what their own strategy documents say — not on who happens to already know whom.

Prior-art check (2026-07-20/21) found no public product doing this specific thing.
Adjacent efforts are single-hromada monitoring (U-LEAD's dashboards) or manual,
relationship-based МСС matchmaking (762 agreements registered as of Jan 2026).
Corpus-level NLP matching across strategy texts appears to be genuine whitespace.

## Method

1. **Retrieve** — find each hromada's official development-strategy document
   (state-mandated Мінрегіон/SURGe template, so structure is comparable across
   hromadas). Retrieval fights Cloudflare/anti-bot protection on many municipal
   sites; Wayback Machine is a frequent fallback.
2. **Structure** — extract into a fixed schema (goals, projects, strengths,
   challenges, named partners, МСС mentions, source quality). This is done in-session
   by the agent (no external LLM API); the resulting JSON is stored via
   [scripts/structure-hromada-strategy.ts](scripts/structure-hromada-strategy.ts)
   (see Cost lessons below).
3. **Match** — compute pairwise similarity on the `Goals` text. Final method: mean-centered,
   sub-goal-level embeddings (`intfloat/multilingual-e5-small`, local, no API cost) —
   materially better than raw TF-IDF or raw (non-centered) embeddings. See
   [Methodology notes](#methodology-notes) for why the simpler approaches failed.
4. **Validate** — score known, registry-confirmed МСС agreements against the model's
   own ranking. If a real agreement doesn't rank near the top, that's a finding about
   the method's limits, not noise to explain away.

## Status (as of 2026-07-23)

- **1,469 mainland hromadas** in the metadata layer (KATOTTG code, oblast, rayon,
  type, population) — effectively the full universe, not a sample.
- **57 hromadas** text-mined for actual strategy content: 40 full-strategy, 8 partial,
  9 confirmed to have no findable strategy (an honest null, not a gap).
- **174 hromadas** (12%) tagged with at least one donor/technical-assistance program
  (DOBRE, DECIDE, GIZ, ПРООН/UNDP, EGAP, DESPRO, МФ Відродження, U-LEAD, Ре:Форм) —
  a floor, not a ceiling; see caveats in [docs/hromadas-schema.md](docs/hromadas-schema.md).
- Known ground-truth trio (Ніжинська↔Козелецька↔Батуринська, a real registered МСС
  agreement) independently ranks in the top 2–5 of every matching pass run so far,
  from 7 hromadas up through the current 54–57-hromada corpus — the core validation
  signal for the whole approach.
- Best new (unverified) candidate found by the method: Новомосковськ↔Запоріжжя,
  cosine 0.571, rank #1 of 1,035 pairs at the 46-hromada stage.
- No decision yet to build a product/graph layer — this is still pilot /
  concept-validation stage.

**Read this before reusing the data:** the 57-hromada text-mined subset is a
pilot sample, not a completed sweep of the 1,469 — most rows will have no
strategy content yet. Every matching score is an **unverified hypothesis**
unless explicitly marked as a registry-confirmed agreement; treat candidate
pairs (like Новомосковськ↔Запоріжжя above) as leads to check, not claims about
real municipal plans.

Full narrative history (every pass, every false start, every honest negative finding)
lives in [docs/project-history.md](docs/project-history.md) — migrated from Claude
Code project memory on spin-out and kept current here. Cursor agents load
[.cursor/rules/hromada-project.mdc](.cursor/rules/hromada-project.mdc) for the
same guardrails.

## Repo layout

```
scripts/
├── migrations/setup-hromadas-table.ts   # create/verify the Hromadas NocoDB table
├── structure-hromada-strategy.ts        # store agent-produced structured JSON in NocoDB
├── import-hromadas-metadata.ts          # bulk PATCH/POST of KATOTTG+population metadata
├── export-hromadas.ts                   # live NocoDB -> data/releases/hromadas.json (the public dataset)
├── hromada-output/                      # per-hromada structured JSON (as produced, gitignored pattern removed — kept for provenance)
└── analysis/                            # one-off Python: KATOTTG merge, TF-IDF matching, embedding matching, MSS graph MVP
data/
├── sources/       # reference registries (KATOTTG classifier extract, Tags table dump)
├── releases/      # THE dataset — canonical, current, CC BY 4.0 (see data/releases/MANIFEST.md)
└── research-log/  # dated growth snapshots (7→13→23→30→46→54 hromadas) — provenance, not the dataset
docs/
├── hromadas-schema.md            # field schema, controlled vocab, data-source notes
├── external-data-sources.md      # findings on external datasets (e.g. KSE-Loc-Data-Hub) as candidate enrichment sources
├── kse-synergy.md                # division of labor vs KSE, join key, W3I outreach use case
├── kse-issue-draft.md            # ready-to-paste GitHub issue for KSE cross-link (draft)
├── hromada-project-passport.html # stakeholder-facing project brief (Ukrainian)
└── mss-graph-mvp.html            # early force-graph visualization prototype
internal/
└── outreach-messages.md          # draft stakeholder outreach copy — not part of the dataset, not for public reuse
REFERENCES.md                     # theoretical grounding — network governance, IMC, institutional diversity
LICENSE / DATA-LICENSE.md         # MIT (code) / CC BY 4.0 (data) — see License & data below
```

Raw scraped source documents (PDF/DOC/HTML corpora fetched during retrieval) were
**not** migrated — they're superseded by the structured extraction already stored in
NocoDB, and mostly re-fetchable from source. Ask if you want a specific hromada's raw
source preserved.

## Setup

```bash
yarn install
cp .env.example .env   # fill in NOCODB_TOKEN + NOCODB_BASE_ID (shared base, ask Max)
yarn setup-hromadas    # idempotent — verifies/creates the Hromadas table + Sectors link column
```

## Shared database

The `Hromadas` table (and the `Tags` table it links `Sectors` to) live in the
**same NocoDB base** as the main W3I ecosystem project (`w3i-network`) — there is
no separate database for this project yet. This is a deliberate, temporary choice:
splitting the codebase out doesn't yet justify splitting the data layer too.
If this project grows into its own product, re-evaluate whether it needs its own
base.

| Table | ID |
|-------|-----|
| Hromadas | `mjtetfuixggp5lg` |
| Tags (shared with w3i-network) | `moee8ep5561zt76` |

## License & data

Code (`scripts/`) is MIT. The dataset in [data/releases/](data/releases/) is
**CC BY 4.0** — see [DATA-LICENSE.md](DATA-LICENSE.md) for attribution
requirements and upstream source credits (data.gov.ua, DREAM, the МСС
registry). [data/research-log/](data/research-log/) is provenance material,
not the maintained dataset — read its README before building on it.
[internal/](internal/) (draft outreach copy) is excluded from both licenses
and not meant for reuse.

If this repo becomes public: this section, the license files, and the
`data/releases/` split exist specifically so the repo can be opened as an
open-data asset (for other researchers or a hromada-data hackathon) without
also exposing draft outreach material or an unlabeled, partially-complete
snapshot as if it were a finished dataset.

## Usage

```bash
# Store an agent-produced structured JSON record: prints to stdout + scripts/hromada-output/
# (the raw-text -> structured-JSON step is done in-session by the agent, no external LLM)
yarn structure-hromada --name "Ніжинська громада" --input structured.json

# ...and write it into NocoDB
yarn structure-hromada --name "Ніжинська громада" --input structured.json --write

# Update an existing row instead of inserting
yarn structure-hromada --name "..." --input structured.json --write --update 12

# Bulk metadata import (KATOTTG + population) — one-off, already run for all 1,469
yarn import-hromadas --updates data/research-log/hromada_updates.json --inserts data/research-log/hromada_inserts.json

# Refresh the public dataset (data/releases/hromadas.json) from live NocoDB
yarn export-hromadas

# Offline export from research-log snapshot (no NocoDB credentials)
yarn export-hromadas:snapshot

# Recompute matching edges (v6: goals + KSE geo + KSE mss network)
yarn match && yarn export-matching-edges && yarn test-known-pairs
```

## Scaling retrieval

Batch workflow for growing the corpus beyond the current pilot: see
[scripts/retrieval/README.md](scripts/retrieval/README.md). Quick start:

```bash
yarn ckan-search --out scripts/retrieval/ckan-candidates.json
# pick URLs → batch-queue.json → download raw text → agent structures it → yarn structure-hromada --write
yarn export-hromadas && yarn match
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
- **Goals-cosine similarity finds thematic/strategic-vision matches, not operational
  ones.** A real, confirmed МСС pair cooperating on a shared CNAP office scored only
  rank #132 of 253 on pure cosine — that kind of back-office cooperation needs a
  proximity/capacity signal, not text similarity. A disclosed weighted combination
  (60% goals-cosine + 40% oblast/rayon-adjacency) recovered it to rank #6.
- **Template collisions produce false positives at scale.** Two hromadas using the
  same external consulting template can produce near-identical goal-section wording
  with zero real substantive overlap. Fix was a narrow, explainable rule (flag
  near-verbatim subgoal-line duplicates, difflib ratio ≥0.98) rather than a
  corpus-wide statistical reweighting, which over-corrected and buried the real
  known cluster on a corpus this small.
- **Cost control matters.** Full in-session Agent-based retrieval+structuring burns
  60–150k tokens per hromada, mostly fighting anti-bot protection, not reasoning.
  Splitting retrieval (stays in-session, deterministic) from structuring (offloaded
  to a free external LLM) is what makes scaling past ~50 hromadas viable.

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
