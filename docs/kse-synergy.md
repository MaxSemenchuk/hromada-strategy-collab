# KSE synergy — complementary datasets, not duplication

This project and [KSE-Loc-Data-Hub](https://github.com/kse-ua/KSE-Loc-Data-Hub)
cover the same 1,469 mainland Ukrainian hromadas but answer different questions.
We join on **KATOTTG** and treat KSE as the authoritative covariate layer; this
repo adds strategy-text semantics and МСС candidate hypotheses KSE does not
produce.

For a deep dive on KSE's structure, edem data quality, and publication record,
see [external-data-sources.md](external-data-sources.md#kse-loc-data-hub).

---

## Division of labor

| Layer | KSE-Loc-Data-Hub | This repo (`hromada-strategy-collab`) |
|-------|------------------|---------------------------------------|
| **Question** | What structural/administrative factors explain hromada resilience and decentralization outcomes? | Which hromadas *should* be talking to each other (or to W3I) based on what their own strategy documents say? |
| **Primary data** | ~130 hromada-level covariates (budget, geography, elections, edem, partnerships, war status, …) compiled for academic research | LLM-structured extractions from official development-strategy documents + pairwise goals-similarity scores |
| **Method** | Econometric / GIS analysis (R pipeline in `src/manipulation/`) | Corpus NLP: mean-centered sub-goal embeddings on `Goals` text |
| **МСС output** | Counts and attributes of *existing* registered partnership agreements (`partnerships-hromadas.csv`) | Ranked *candidate* pairs — unverified hypotheses unless marked `known: true` against the registry |
| **Audience** | KSE research group, policy papers, VoxUkraine, Hromada Dashboard | W3I Civic Tech Lab outreach, МСС matchmaking pilots, open-data researchers |

**Rule of thumb:** if a variable exists in KSE's derived CSVs, we fetch and join
it at analysis time — we do not copy those files into this repo or re-derive
them. If a variable comes from strategy-document text, we own it here and can
offer it back to KSE as a complementary layer.

---

## Join key: KATOTTG

Both projects use the official Мінрегіон hromada classifier code
(`UA…`, 17 characters) as the stable row identifier.

- **This repo:** `Koatuu / Katottg` in NocoDB; `katottg` in
  `data/releases/hromadas.json` and `data/releases/matching-edges.json`.
- **KSE:** `hromada_code` in `data/derived/hromada.csv` and sibling derived
  files; same codes, same 1,469 mainland hromadas (Crimea excluded).

Join is a left join from our text-mined subset onto KSE's full universe — most
KSE rows will have no strategy extraction yet; that is expected at pilot stage.

---

## What we consume from KSE

Pinned source URLs and Zenodo DOI live in `data/sources/kse-pin.json` (when
present). Analysis scripts lazy-fetch from
`raw.githubusercontent.com/kse-ua/KSE-Loc-Data-Hub/main/data/derived/…` — we
do not vend copies of KSE CSVs in `data/releases/`.

| KSE file | Fields used | Role in this project |
|----------|-------------|----------------------|
| `geography.csv` | Distance to Russia/Belarus/EU border, frontline proximity, travel time to oblast center | Proximity signal alongside oblast/rayon adjacency in weighted matching (operational/back-office МСС pairs need geography, not just text similarity) |
| `edem-data.csv` | `edem_petitions`, `edem_consultations`, `edem_participatory_budget`, `edem_open_hromada`, `edem_total` (0–4) | Civic-tech maturity proxy for W3I outreach prioritization (see [W3I use case](#w3i-use-case-civic-tech-lab-outreach) below) |
| `partnerships-hromadas.csv` | Existing inter-municipal agreement counts and partner lists | Ground-truth validation (`known: true` edges) and sanity-check against our candidate hypotheses |
| `minregion-war-status.csv` | Occupation / frontline / LMA status | Context for missing or stale strategy documents; filter or annotate hromadas where retrieval is impossible or misleading |

We also use `hromada.csv` as the KSE row index when joining — not for fields we
already store (name, oblast, rayon, population come from our own metadata import).

### Caveat: edem missingness

**Do not use `edem_total` from KSE's `full_dataset.csv` without correction.**

KSE's merge script (`ellis-general.R`) replaces NA with `0` on edem columns.
That makes ~1,138 hromadas with *no e-dem.ua scrape match* look identical to
hromadas *confirmed* to have zero e-participation tools. Only **331 of 1,469**
hromadas appear in the standalone `edem-data.csv`; within that file, one row is
a genuine zero.

When joining edem covariates:

1. Read **`edem-data.csv`**, not the edem columns in `full_dataset.csv`.
2. Treat hromadas absent from `edem-data.csv` as **missing**, not as
   `edem_total = 0`.
3. Document coverage in any downstream score (e.g. "edem known for 331/77
   text-mined hromadas").

Attribution: KSE-Loc-Data-Hub, Zenodo [10.5281/zenodo.15267573](https://doi.org/10.5281/zenodo.15267573), MIT license — used at analysis time, not redistributed.

---

## What we contribute back

Items KSE does not currently publish that we can cross-link or share on request:

| Asset | Location | What it adds for KSE-side research |
|-------|----------|-------------------------------------|
| **Strategy extractions** | NocoDB `Hromadas` table → `data/releases/hromadas.json` | Structured `Goals`, `Projects`, `Strengths`, `Challenges`, `PartnersMentioned`, `MSSAgreements` from the actual strategy PDF — narrative intent beyond covariate proxies |
| **Matching edges (hypotheses)** | `data/releases/matching-edges.json` | Pairwise goals-cosine scores over the text-mined corpus; `known: true` marks registry-confirmed agreements for method validation; all other pairs are *candidates*, not facts |
| **Retrieval nulls** | `SourceQuality = none` rows | Honest record of hromadas where no findable strategy exists — useful when interpreting gaps in text-based outcomes |

We do **not** claim our candidate pairs are real МСС plans. KSE's
`partnerships-hromadas.csv` remains authoritative for *existing* agreements;
our edges are leads for further verification.

---

## W3I use case: Civic Tech Lab outreach

W3I's Civic Tech Lab / Digital Democracy Lab already works hromada-by-hromada.
This repo supports **prioritization at scale** by combining:

1. **Goals-similarity** (from our matching pipeline) — thematic alignment with
   Lab themes, peer clusters, or a reference hromada already in the program.
2. **`edem_total`** (from KSE `edem-data.csv`, with missingness handled) —
   existing e-participation infrastructure as a readiness signal.

A simple outreach score for hromada *h* relative to a reference set *R*:

```
outreach_score(h) = max_{r ∈ R} goals_cosine(h, r) × f(edem_total(h))
```

where `f(edem_total)` might be:

- `1.0` if `edem_total ≥ 2` (multiple tools live — higher conversion likelihood),
- `0.7` if `edem_total == 1`,
- `0.4` if `edem_total == 0` *and* h appears in `edem-data.csv` (confirmed low adoption — education opportunity),
- `null` / exclude from edem-weighted ranking if h is **missing** from `edem-data.csv`.

High goals-similarity + moderate edem maturity → strong candidate for Lab
engagement or intro to a thematic peer cluster. High similarity + edem missing
→ worth retrieval/outreach but do not infer digital maturity. Low similarity +
high edem → existing civic-tech capacity but different strategic priorities.

This is an operational heuristic for W3I staff, not a published research
claim. Tune weights after the first outreach cohort.

---

## Integration status

| Step | Status |
|------|--------|
| KSE reviewed, documented in `external-data-sources.md` | Done (2026-07-23) |
| `kse-pin.json` + `enrich_from_kse.py` lazy join | Done (2026-07-23) |
| `match.py` v6 (goals + geo + mss network) | Done (2026-07-23) |
| Cross-link issue on KSE repo | Draft in [kse-issue-draft.md](kse-issue-draft.md) — not yet filed |
| KSE attribution in `DATA-LICENSE.md` | Check [DATA-LICENSE.md](../DATA-LICENSE.md) |

Matching reads `data/releases/hromadas.json` and attaches KSE covariates at runtime
via `enrich_from_kse.py` — not duplicated in NocoDB.
