# Engine vs plumbing — what transfers if this is pitched as an EU system

**Purpose:** support the positioning "this is a system for EU cooperation instruments;
the Ukraine rollout is the validation experiment" — worked out in chat 2026-08-10.
Separates reusable methodology from Ukraine-specific data/legal plumbing, so the
pitch doesn't overclaim and so there's a concrete list of what porting actually requires.

## Universal engine (method transfers, data source swaps)

1. **Goals-embedding similarity** (`goals_cosine`, DF-weighted bipartite +
   document-centroid cosine over strategy-goal text, `match.py` v7.1) — the
   method is language-agnostic; needs a multilingual/target-language embedding
   model, not a rewrite.
2. **Geo-adjacency as a discovery signal** — the *pattern* (administrative +
   basin adjacency lowers cooperation cost) is generic; HydroBASINS itself is
   already a global dataset, already used as an overlay.
3. **Funder-overlap as a trust-lowering instrument** — Tkachuk's "AI lowers
   uncertainty, doesn't replace trust" mechanism (see
   [mss-cooperation-research.md](../docs/mss-cooperation-research.md)) is
   general. The specific programs (DOBRE/GIZ/U-LEAD) are Ukrainian; an EU
   version would key off Interreg/LEADER/Horizon co-participation instead.
4. **Explicit-ask extraction** from strategy text — generic text-mining method;
   needs access to comparably structured EU planning documents.
5. **Template-collision as a governance signal** — the *idea* (shared
   consulting template → testable hypothesis about capacity) is generic; EU
   detection would need whatever template ecosystem dominates a given
   country's regional planning, likely far more fragmented than Ukraine's
   single Мінрегіон template (наказ №265).
6. **Pair-scoring + multi-signal package architecture** — the general
   recommendation shape (signals → candidate pair → package) is portable.

## Ukraine-specific plumbing (rebuild required per market)

1. **Мінрегіон наказ №265 template parsing** — the ingestion pipeline assumes
   this document structure; the EU has 27 different national/regional
   planning traditions, no single template.
2. **Law 1508-VII's five legal cooperation forms** as the "form" layer of the
   recommendation — no EU equivalent. An EU version would map onto Interreg
   programmes, EGTC (European Grouping of Territorial Cooperation), LEADER
   Local Action Groups, or twinning agreements — much softer, no legal-form
   menu to recommend from.
3. **KSE PIN registry** as validation ground truth (existing Law 1508
   agreements) — no single EU equivalent; validation data would be
   per-country or per-programme and likely harder to access.
4. **`DonorsPrograms` tag set** (DOBRE, EGAP, U-LEAD, GIZ, USAID) — Ukrainian
   donor landscape; an EU pitch needs a different program list entirely.
5. **Hromada metadata corpus** (1,469 rows from open Ukrainian sources) — EU
   municipal open-data coverage is per-country and wildly uneven.
6. **Existing bridge:** the [UA–EU twinning layer](../docs/ua-eu-twinning.md)
   (176 nodes via SKEW/C4C) is the one piece that already reaches across the
   border — closer to shovel-ready than inventing a new EU-only product from
   nothing.

## What has to be decided before the EU claim survives scrutiny

- **Pick one EU instrument to target first.** Interreg looks structurally
  closest to Law 1508 МСС (funded, multi-year, application-based) —
  probably the easiest analogy to defend. LEADER, EGTC, and twinning
  (SKEW/C4C) are alternates with different feasibility and audiences.
- **Confirm a validation dataset exists** for that instrument — i.e. some
  EU-side registry of existing cooperation agreements to replicate the "the
  method found a real, already-existing agreement without being told"
  credibility move (Ніжин–Батурин–Козелець in the UA pilot). Without this,
  the EU claim has no analogous proof point.
  - **Built and confirmed (2026-08-12): [keep.eu](https://keep.eu)** —
    the EU's official Interreg/ETC project database. It has a **public
    browse API that needs no registered key** (only its *bulk* Open Data
    export does) — `POST /api/search/projects/` + `GET /api/project/<id>/`,
    found by capturing the real request the public web UI makes (plain GET
    query-param filters are silently ignored by the endpoint). Built
    [scripts/analysis/build_interreg_layer.py](../scripts/analysis/build_interreg_layer.py)
    (`yarn interreg`) against the five 2021-2027 programmes covering Ukraine
    (Poland-Ukraine, Hungary-Slovakia-Romania-Ukraine, Romania-Ukraine,
    Danube, Black Sea Basin) → `data/releases/interreg-partners.json`; then
    ran `--historical` too (2000-2020 programmes, same country pairs).
  - **Combined numbers, and the honest caveat that matters more than the
    headline count**: 1,550 projects scanned across all four programming
    periods (2000-2006 through 2021-2027) → 100 hromadas matched to at
    least one Ukrainian project partner (734 matched partnerships, 581
    unmatched). But partner-level granularity confirms the concern flagged
    last time: **only 57/734 matched partnerships (43/100 hromadas) are
    tagged `organisation_type == "Local public authority"`** — i.e.
    plausibly the hromada council itself or a direct department. The rest
    are oblast/national/sectoral bodies (regional development agencies,
    universities, hospitals, NGOs, even a National Guard unit) that merely
    have a mailing address in that hromada's town — town-matching alone
    conflates these with real hromada-level cooperation. Treat the 57, not
    the 100 hromadas, as the analogue to SKEW's twinning edges.
  - **Second finding, only visible after running `--historical`**: keep.eu's
    `organisation_type` field is **null on every 2000-2020 record** — it was
    only captured from the 2021-2027 period onward. All 57 confirmed
    local-authority matches come from the current period; the historical
    expansion added 513 more matched partnerships (100 hromadas vs. 60) but
    zero more *confirmed* ones — they're unclassified, not disconfirmed.
    Don't read "100 hromadas" as apples-to-apples with the 60 from the
    current period alone.
  - **This is still a real, usable validation dataset** — 43 hromadas with
    a confirmed direct EU-project tie is a legitimate "already-formed
    cooperation" registry, same role as
    [ua-eu-twinning.md](../docs/ua-eu-twinning.md)'s SKEW layer, just
    smaller and requiring the `is_local_authority` + `period` filters to use
    honestly.
- **Decide which product this actually is**, because these are not the same
  thing: (a) matching EU municipalities to each other, or (b) matching UA
  hromadas to EU twinning/funding partners by extending the existing
  176-node twinning layer. (b) is much closer to shovel-ready.
- **Expect re-calibration, not a rewrite**, for the engine pieces (embedding
  model, weights, thresholds) once a target EU dataset is chosen.

## Risk

Positioning without at least a rough version of the above reads as
grant-chasing repackaging to any funder who has seen this move before ("did
X in country Y, pivoting to sell as EU platform"). The AIM-CC pre-registration
discipline already applied to the Ukraine pilot
([internal/aim-cc-field-experiment-prereg.md](aim-cc-field-experiment-prereg.md))
is the model for de-risking this: pre-register the *transfer* claim itself —
name the EU instrument and validation dataset before running anything — so
the EU pitch carries the same rigor as the UA experiment.
