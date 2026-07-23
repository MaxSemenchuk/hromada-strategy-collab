# Hromada Strategy Collaboration Mapping

Corpus-level NLP matching of Ukrainian territorial-community (**hromada**) development
strategies, to systematically surface candidates for **МСС** (inter-municipal
cooperation) — instead of relying on the ad-hoc, relationship-based matchmaking that
is how most МСС partnerships get formed today.

Spun out from the W3I ecosystem project (`w3i-network`) on 2026-07-23 as its own
codebase. **The NocoDB database is currently shared** with the main W3I base — see
[Shared database](#shared-database) below.

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
   challenges, named partners, МСС mentions, source quality) via a cheap external
   LLM ([scripts/structure-hromada-strategy.ts](scripts/structure-hromada-strategy.ts),
   Groq `llama-3.3-70b-versatile`, genuinely free) — kept out of the main
   conversation loop specifically to control cost (see Cost lessons below).
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

Full narrative history (every pass, every false start, every honest negative finding)
lives in Claude Code project memory (`project_hromada_strategy_collab.md`), not
duplicated here to avoid drift. Ask Claude to pull it up for detail on any specific
round.

## Repo layout

```
scripts/
├── migrations/setup-hromadas-table.ts   # create/verify the Hromadas NocoDB table
├── structure-hromada-strategy.ts        # raw strategy text -> structured JSON (Groq/Gemini)
├── import-hromadas-metadata.ts          # bulk PATCH/POST of KATOTTG+population metadata
├── hromada-output/                      # per-hromada structured JSON (as produced, gitignored pattern removed — kept for provenance)
└── analysis/                            # one-off Python: KATOTTG merge, TF-IDF matching, embedding matching, MSS graph MVP
data/
├── sources/     # reference registries (KATOTTG classifier extract, Tags table dump)
└── snapshots/   # dated growth snapshots of the studied set (7→13→23→30→46→54 hromadas) + matching-edge outputs
docs/
├── hromadas-schema.md            # field schema, controlled vocab, data-source notes
├── hromada-project-passport.html # stakeholder-facing project brief (Ukrainian)
├── mss-graph-mvp.html            # early force-graph visualization prototype
└── outreach-messages.md          # draft stakeholder messages (not yet re-scrutinized for overclaiming)
REFERENCES.md                     # theoretical grounding — network governance, IMC, institutional diversity
```

Raw scraped source documents (PDF/DOC/HTML corpora fetched during retrieval) were
**not** migrated — they're superseded by the structured extraction already stored in
NocoDB, and mostly re-fetchable from source. Ask if you want a specific hromada's raw
source preserved.

## Setup

```bash
yarn install
cp .env.example .env   # fill in NOCODB_TOKEN + NOCODB_BASE_ID (shared base, ask Max) and GROQ_API_KEY (free, console.groq.com/keys)
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

## Usage

```bash
# Structure a raw strategy text file into the schema, print to stdout + scripts/hromada-output/
yarn structure-hromada --name "Ніжинська громада" --input raw.txt

# ...and write it into NocoDB
yarn structure-hromada --name "Ніжинська громада" --input raw.txt --write

# Update an existing row instead of inserting
yarn structure-hromada --name "..." --input raw.txt --write --update 12

# Bulk metadata import (KATOTTG + population) — one-off, already run for all 1,469
yarn import-hromadas --updates data/snapshots/hromada_updates.json --inserts data/snapshots/hromada_inserts.json
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
