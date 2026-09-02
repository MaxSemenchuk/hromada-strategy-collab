# External Data Sources — Knowledge Base

Findings on external repositories/datasets reviewed as potential sources of
hromada-level covariates or comparison data for this project. One dated section
per source. Not yet folded into `data/releases/hromadas.json` unless noted.

---

## KSE-Loc-Data-Hub

> **Synergy doc:** how this project uses KSE without duplicating it — join key,
> consumed files, edem caveats, and what we contribute back —
> [kse-synergy.md](kse-synergy.md). Cross-link issue:
> [kse-ua/KSE-Loc-Data-Hub#25](https://github.com/kse-ua/KSE-Loc-Data-Hub/issues/25).

- **Reviewed:** 2026-07-23
- **URL:** https://github.com/kse-ua/KSE-Loc-Data-Hub
- **Zenodo DOI:** [10.5281/zenodo.15267573](https://doi.org/10.5281/zenodo.15267573) (v1.0.1, Apr 2025, MIT license)

### What it is

A KSE Institute research data hub studying the effect of Ukraine's 2014–2022
decentralization reform (11,250 radas → 1,469 hromadas), with a specific focus
on hromada resilience to the 2022-02-24 invasion. Funded by GIZ (U-LEAD with
Europe, Phase II). Not a general-purpose open dataset with wide external
uptake — 15 stars / 9 forks — functions mainly as the working data layer for
one KSE research group's own publications (see "Who uses it" below).

### Structure

```
data/raw/            unprocessed source files
data/derived/         cleaned, hromada-level datasets — data/derived/full_dataset.csv
                       is the main compiled file (1,469 hromadas × ~130 variables)
data/data-private/    same structure, gitignored (sensitive survey data)
src/manipulation/     ellis-*.R — one script per raw→derived transform
src/analysis/         modeling/analysis scripts
```

Repo is ~570 MB (shapefiles, geojson, private survey data) — `git clone` times
out. Use the GitHub API tree (`/repos/.../git/trees/main?recursive=1`) plus
`raw.githubusercontent.com/.../<path>` fetches for individual files instead.

### Key datasets (from `data/derived/README.md`)

Administrative units/history, population, geography (distance to
Russia/Belarus/EU border, frontline proximity), budget & tax revenue
2020–2022, DFRR (ДФРР — Держфонд регіонального розвитку) project financing,
road lengths, internet speed, community competence (youth centers/councils),
OSBB counts, inter-municipal partnership agreements, **E-dem**, mayor bios,
election results, health facility declarations, ZNO scores, war-zone/occupation
status (Ministry of Reintegration), 2025 maps of Local Military Administrations
and ACLED-based conflict-intensity/infrastructure-damage.

### E-dem dataset (detail)

- **Source:** scraped from e-dem.ua, as of Sep 2022. Script:
  [`src/manipulation/ellis-edem.R`](https://github.com/kse-ua/KSE-Loc-Data-Hub/blob/main/src/manipulation/ellis-edem.R)
- **Fields:** 4 binary indicators of e-participation tools —
  `edem_petitions`, `edem_consultations`, `edem_participatory_budget`,
  `edem_open_hromada` — plus `edem_total` (sum, 0–4).
- **Coverage:** only 331 of 1,469 hromadas have a match on e-dem.ua.
  Adoption within that 331: petitions 62.8%, participatory budget 56.5%,
  consultations 37.2%, open hromada 27.8%. Distribution of `edem_total`:
  47.7% have exactly 1 tool, 26.6% have 2, 18.1% have 3, 7.3% have all 4.
  Oblast averages range from 2.38 (Волинська) down to 1.12 (Чернігівська).
- **Data-quality caveat (found by reading the merge code, not documented
  anywhere in the repo):** in
  [`src/manipulation/ellis-general.R:352-374`](https://github.com/kse-ua/KSE-Loc-Data-Hub/blob/main/src/manipulation/ellis-general.R#L352),
  the join into `full_dataset.csv` does `replace(is.na(.), 0)` on the edem
  columns. The ~77.5% of hromadas absent from the e-dem.ua scrape are coded
  as `0` in `full_dataset.csv`, indistinguishable from hromadas confirmed to
  have zero e-participation tools. Confirmed empirically:
  `full_dataset.csv` shows 1,139 hromadas with `edem_total == 0`, but only
  331 hromadas exist in the standalone `data/derived/edem-data.csv` at all
  (1 of which is a genuine zero). Anyone using `edem_total` from
  `full_dataset.csv` as-is should re-derive true missingness from
  `edem-data.csv` rather than trust the merged column.
- **Superseded (partially) by our own live pull:** `yarn edem-barometer` hits
  e-dem.ua's own public API directly instead of relying on KSE's 2022
  scrape — current coverage, quantitative counts, but only petitions +
  participatory budget (no consultations/open_hromada — the platform's
  those two endpoints are aggregate-only). See
  [edem-barometer.md](edem-barometer.md).

### Who uses it / how

- **Primary users are the repo's own team** (KSE Center for Sociological
  Research, Decentralization and Regional Development; lead researcher
  Tymofii Brik). Commit volume: velgaks/Hatsko 1357, andkov/Koval 212,
  Tytser/Tytiuk 144, ipiddubnyi/Piddubniy 66, splanetina/Savisko 4, plus
  sheman0098/kpetrynka/izasimovych (not listed in the README's team table).
- **Feeds the team's own academic output:**
  - Rabinovych, Brik, Darkovich, Savisko, Hatsko et al. — ["Explaining
    Ukraine's Resilience to Russia's Invasion: The Role of Local
    Governance"](https://onlinelibrary.wiley.com/doi/10.1111/gove.12827),
    *Governance*, 2024
  - Rabinovych, Brik, Darkovich, Hatsko, Savisko —
    ["Ukrainian decentralization under martial law"](https://doi.org/10.1080/1060586X.2025.2520167),
    *Post-Soviet Affairs*, 2025 (uses the repo's LMA map)
  - ["Does decentralization boost Ukrainian resilience? The role of local
    authorities in supporting IDPs"](https://www.tandfonline.com/doi/full/10.1080/1060586X.2025.2547336),
    *Post-Soviet Affairs*, 2025
  - Earlier PONARS Eurasia policy memo (Darkovich, Savisko, Rabinovych, 2023)
- **Public-facing policy output:** several VoxUkraine articles; an
  interactive [Hromada Dashboard](https://valentyn-hatsko.shinyapps.io/hromada-dash/)
  on shinyapps.io; 2025 interactive maps (LMAs, conflict intensity,
  infrastructure damage).
- **External reuse is thin:** all GitHub Issues/PRs are internal
  (team-only); the 9 forks look like individual researchers/students copying
  it for their own use rather than active collaborators; Zenodo shows 95
  views / 36 downloads.

### Relevance to this project

Candidate enrichment covariates for matching / outreach — now also packaged
via `yarn hromada-resources` (see release `hromada-resources.json`):

- `geography.csv` — proximity (already in match.py v6)
- `edem_total` / `partnerships-hromadas.csv` — civic-tech + PIN validation
- `minregion-war-status.csv` — occupation/frontline context
- `hromada_budget_2020_2022.csv`, `dfrr_hromadas.csv`,
  `community-competence-hromada.csv`, `health_facilities.csv` — fiscal /
  competence / health proxies

For the integration plan and W3I outreach use case, see
[kse-synergy.md](kse-synergy.md).

---

## DREAM public API

- **Reviewed:** 2026-07-29
- **URL:** https://public-api.dream.gov.ua
- **Docs:** https://open-contracting.github.io/dream-api-docs/

Reconstruction / public-investment project registry. List endpoint paginates
with `?from=<updated>` (~16k ideas). Per-idea detail carries UA-CATOTTG
settlement locations + WB-ECO sector codes. Aggregated to hromada level by
`yarn fetch-dream` → `data/releases/dream-priorities.json` (raw cache in
`data/cache/dream/`). Revealed priorities, not strategy text.

---

## SKEW — German–Ukrainian municipal partnerships (twinning)

- **Reviewed:** 2026-07-29
- **Map:** https://skew.engagement-global.de/landkarte-deutsch-ukrainischer-kommunalbeziehungen.html
- **List:** https://skew.engagement-global.de/Liste-deutsch-ukrainischer-kommunalbeziehungen.html
- **Operator:** Servicestelle Kommunen in der Einen Welt (Engagement Global / BMZ)

Authoritative registry of **DE↔UA** municipal partnerships (~250+, Kommunal-
and Betreiberpartnerschaften). No public CSV/API — HTML map embeds `MAPDATA`
(Leaflet points with partner links + oblast labels); list table adds partnership
type. Integrated as a **separate** release layer (not in v7 `score`):

```bash
yarn twinning                 # fetch HTML → data/cache/twinning/ + build release
yarn twinning --offline       # rebuild from cache
yarn fetch-twinning           # refresh cache only
```

→ `data/releases/twinning-partners.json`. Latin UA names resolved via
transliteration + `data/sources/twinning-name-aliases.json`. Strategy-text
foreign cities (Kalmar, Łowicz, …) merge in with `confidence: strategy_mention`.
Skips Kyiv city, raions, utilities. Cities4Cities (~100 partnerships, multi-EU) is integrated via news-title
pair extraction + `markers.json` profile URLs (`yarn twinning`). Not a bulk
partnership registry like SKEW — confirmed pairs are hypotheses from press
titles; `c4c_url` means «listed in C4C municipality DB» (seeking partners).

**Format / cases / how hromadas find partners:**
[ua-eu-twinning.md](ua-eu-twinning.md).

---

## keep.eu — Interreg / ETC project & partner database

- **Reviewed:** 2026-08-12
- **Site:** https://keep.eu
- **Operator:** Interact (EU programme supporting Interreg cooperation)

Official EU database of Interreg/European Territorial Cooperation projects
and partner organisations (32,000+ projects, 150,000+ partnerships since
2000). Two separate access paths:

1. **Registered Open Data API** (`/api/open-data?key=...`) — bulk export,
   requires registering at keep.eu and requesting a key by email
   (`keep.support@interact.eu`, case-by-case approval). Not used here.
2. **Public browse API** (what this repo uses) — the same endpoints the
   public web UI calls, reachable with no key: `POST /api/search/projects/`
   (paginated project list, filtered via a `programmes.available: [{id}, ...]`
   body — plain GET query params are silently ignored, this shape was found
   by capturing the real browser request) and `GET /api/project/<id>/`
   (full detail incl. `partnerships[].partner` — name, country, town,
   coordinates, `organisation_type`, budget).

Separate release layer (not in v7 `score`, not `known: true`):

```bash
yarn interreg                 # fetch keep.eu + build release (2021-2027 programmes only)
yarn interreg --historical    # also fetch 2000-2020 programmes (~1,100 more projects)
yarn interreg --offline       # rebuild from cache, no network
yarn fetch-interreg           # refresh cache only
```

→ `data/releases/interreg-partners.json`. Covers all 16 Interreg
NEXT/B/ENI CBC/ENPI CBC programmes bordering or covering Ukraine since 2000
(Poland-Ukraine, Hungary-Slovakia-Romania-Ukraine, Romania-Ukraine, Danube,
Black Sea Basin, across the 2000-2006/2007-2013/2014-2020/2021-2027
periods). Partner orgs matched to `hromadas.json` by name-stem (Ukrainian
legal name, e.g. «...ської міської ради» → stem) or by registered town as
fallback — no transliteration table needed since keep.eu gives original
Cyrillic names for current-period records, unlike SKEW's German-side source.

**Read `organisation_type` (and `period`) before treating a match as a real
cooperation tie**: town-matching alone conflates the hromada with any
oblast/national body that merely has its mailing address there (regional
development agencies, universities, hospitals, NGOs, even a National Guard
unit turned up this way). Only entries where `is_local_authority: true`
(`organisation_type == "Local public authority"`) plausibly are the hromada
council or a direct department — combined run: **57/734 matched
partnerships** (43/100 hromadas have at least one). The other 677 aren't
necessarily wrong, they're just unclassified: **keep.eu's own
`organisation_type` field is null on every 2000-2020 ("historical") record
observed so far** (populated only from the 2021-2027 period onward), so all
513 historical-period matches show up as `organisation_type: unspecified` —
absence of the flag there is a metadata gap, not evidence the partner isn't
a hromada council. See `coverage.org_type_breakdown` and
`coverage.period_breakdown` in the release for the full picture.

---

## decentralization.ua — Ministry partnership map (all countries, not just DE)

- **Reviewed:** 2026-09-02
- **Page:** https://decentralization.ua/twincities (overview + Tableau dashboard)
- **Scraped:** https://decentralization.ua/newgromada/&lt;id&gt; (per-hromada pages)
- **Operator:** Мінрозвитку громад та територій, with Council of Europe
  (Swiss-funded DECIDE project) and Programme "U-LEAD with Europe"

Fills the exact gap SKEW leaves open: SKEW only covers Germany. This is the
**Ukrainian side's own verified partnership registry**, covering every
partner country at once (found: 47 country codes, led by Poland).
Each hromada's own page (`/newgromada/<id>`) lists partner **country + partner
city name**, with the hromada's own **KATOTTG printed on the page** — so
resolution is a direct KATOTTG join, no transliteration/alias table needed
(unlike SKEW, where the source only gives German-side Latin spellings).
Trade-off vs SKEW: no per-partner "since" year or partnership-type field,
just a verified country+city pair.

```bash
yarn partnership-map                 # fetch (listing + ~1440 hromada pages) + build release
yarn partnership-map --offline       # rebuild from cache, no network
yarn partnership-map --limit N       # fetch only first N hromadas (testing)
yarn fetch-partnership-map           # refresh data/cache/decentralization/ only
```

→ `data/releases/partnership-map.json`. Current run: 1438/~1470 hromadas
fetched, **288 hromadas with at least one partner, 1134 partner-city rows**,
6 KATOTTG misses (hromadas with no `Katottg` in our own `hromadas.json`, a
pre-existing gap — see `unmatched` in the release). That's already more than
double SKEW's 114 confirmed hromadas and ~6× its 194 edges, and it spans all
47 countries at once instead of only Germany.

**Do not treat as authoritative-and-complete, and do not treat as a
replacement for the SKEW layer**: the site itself labels `/newgromada` as
"працює у тестовому режимі" (beta), and its own headline dashboard claims a
higher total (490 hromadas / 2119 agreements / 1740 partners / 64 countries,
"станом на кінець 2025") than what the scraped per-hromada pages currently
show — the Tableau dashboard behind `/twincities` is evidently a fuller or
more current dataset than the per-hromada page snapshot scraped here. Spot
check: Poltava's page here lists 9 partners but is **missing Kalmar (SE)**,
the flagship case documented in [ua-eu-twinning.md](ua-eu-twinning.md) — so
this source and the SKEW/C4C/strategy layer each catch cases the other
misses.

**Tried and deliberately abandoned: scraping the `/twincities` Tableau
dashboard for the fuller numbers.** Checked 2026-09-02: the embed's own
session config reports `allow_view_underlying: false` and
`allow_summary: false`, and a fresh `bootstrapSession` call against the
data-export command path returns `410 Gone`. The publisher has explicitly
turned off Tableau's "view/download data" feature for this workbook — that
reads as an intentional access control, not an incidental gap, so we did not
try to route around it (no reverse-engineered VizQL replay, no
`tableauscraper`). The per-hromada `/newgromada` pages remain the ceiling of
what this project pulls from decentralization.ua.

**Merged 2026-09-02** into `twinning-partners.json` (union, not
deduplicated — see that file's `warning` field and
[ua-eu-twinning.md](ua-eu-twinning.md) for why cross-alphabet dedup isn't
attempted). Also wired into the map/graph: `yarn graph-pin-matching`'s
`twinning` layer now reads the merged file directly (no separate layer
needed), taking `country_ids` from `COUNTRY_LABELS` in
`build_pin_matching_graph.py`, extended 2026-09-02 to cover all ~47 country
codes this source introduces.

---

## Own revenues (data.gov.ua) — caveat

CKAN packages titled «Власні доходи громад … на одиницю населення» are often
**oblast-scoped** dumps (e.g. Івано-Франківська, ~60 rows), not a national
series. Prefer KSE `hromada_budget_2020_2022.csv` ÷ `ua-pop-2022` for
comparable per-capita coverage across all 1,469 mainland hromadas
(`own_income_per_capita` in `hromada-resources.json`). Live national open-budget
CSVs exist per oblast with `CATUTTC` but are not yet federated here.

---

## Prozorro — deferred

National procurement is high-signal for revealed infrastructure priorities, but
stable **EDRPOУ → KATOTTG** join at hromada level is not in this repo yet (DREAM
parties expose EDR ids; mapping them to municipal budgets needs a separate
registry). Do not invent tender→hromada heuristics. Revisit after an EDR/budget
code bridge exists.

---

## HydroBASINS / river catchments (water underlay)

- **Reviewed:** 2026-08-03
- **Spike:** `python3 scripts/analysis/basin_overlay_spike.py` (optional `--fetch`)
- **Source:** [HydroBASINS EU lev06 v1c](https://data.hydrosheds.org/file/hydrobasins/standard/hybas_eu_lev06_v1c.zip)
  (HydroSHEDS) — hydrological catchments, **not** the nine legal Ukrainian
  river basin districts (ВК ст. 13-1 / наказ Мінприроди №103). Official DAVR
  WFS (`geoportal.davr.gov.ua:81`) was unreachable at review time; prefer
  legal RBD polygons when that geoportal recovers.
- **Cache:** `data/cache/water/` (gitignored). Clipped UA layer + simplified
  web GeoJSON: [`docs/geo/ukraine-basins-lev06.geojson`](geo/ukraine-basins-lev06.geojson).
- **Join:** KSE `lat_center`/`lon_center` → point-in-polygon → `basin_id`
  (`data/research-log/hromada-basin-assignment.json`).
- **Spike finding (lev06):** PIN undirected edges ~77% same-oblast vs ~53%
  same-basin (finer than oblast). Control water pair Галицька↔Дубовецька
  shares a basin; Дністровський каньйон (reg#721, 22 parties) spans **5**
  basins / 4 oblasts. Theme `water` (ЖКГ utilities) is **not** the same as
  basin-management IMC — do not fold `same_basin` into v7 `score`.
- **Product use:** optional PIN-map underlay «Підкладка · водозбори»
  (`yarn graph-pin-matching`); discovery context only, never `known: true`.

### Parsing registry titles → themes (map filter)

Registry XLSX has no theme column — we score `Назва`+`Форма` with
`mss_suggest.classify_registry_theme` (same patterns as candidate packaging).

**Why ~40% stay `other`:** many rows are legal boilerplate only («реалізація
спільного проекту» / делегування без предмета). Expanding patterns recovered
gaps that *do* have subject text in quotes (ПМСД, трудовий архів, спорт,
дамби, теплопостачання…). Honest residual: leave as `other`; do not invent
themes from party geography alone.

**Map:** sidebar «Теми угод МСС» filters PIN / pin∩corpus edges by `theme_ids`
(not the five legal forms — form filter remains secondary).