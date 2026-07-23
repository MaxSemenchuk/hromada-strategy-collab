# External Data Sources — Knowledge Base

Findings on external repositories/datasets reviewed as potential sources of
hromada-level covariates or comparison data for this project. One dated section
per source. Not yet integrated into the `Hromadas` NocoDB table unless noted.

---

## KSE-Loc-Data-Hub

> **Synergy doc:** how this project uses KSE without duplicating it — join key,
> consumed files, edem caveats, and what we contribute back —
> [kse-synergy.md](kse-synergy.md). Draft cross-link issue for the KSE repo:
> [kse-issue-draft.md](kse-issue-draft.md).

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

Candidate enrichment covariates for the `Hromadas` table if/when the project
moves past pilot stage:

- `geography.csv` — distance-to-border/frontline, travel time to oblast
  center — plausible proximity-signal input alongside the existing
  oblast/rayon-adjacency term (see the weighted-matching note in
  [README.md](../README.md#methodology-notes)).
- `edem_total` / `partnerships-hromadas.csv` — possible weak-signal proxies
  for civic-tech maturity or existing inter-municipal cooperation, useful as
  a validation check against this project's own МСС candidates (subject to
  the missingness caveat above).
- `minregion-war-status.csv` — occupation/frontline status, relevant context
  for interpreting why some hromadas have no findable strategy document.

Not yet pulled into NocoDB or the matching pipeline — this section is a
research note, not an integration decision. For the integration plan and W3I
outreach use case, see [kse-synergy.md](kse-synergy.md).
