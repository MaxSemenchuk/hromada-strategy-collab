# Data license

Everything under [data/releases/](data/releases/) is licensed under
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)** — free to use,
share, and adapt, including commercially, as long as you credit the source.

Material under [data/research-log/](data/research-log/) (dated pilot snapshots,
kept for provenance) carries the same license but is explicitly **not**
maintained as a stable dataset — see its own README before building on it.

## Attribution

If you use this data, credit:

> Hromada Strategy Collaboration Mapping (W3I), derived in part from
> data.gov.ua (CC BY 4.0), the DREAM public API, and the Мінрегіон
> inter-municipal cooperation (МСС) agreement registry.

Upstream sources this data draws on:

- **[data.gov.ua](https://data.gov.ua)** — CKAN open-data portal, CC BY 4.0.
  Source for hromada development-strategy documents.
- **[DREAM](https://dream.gov.ua)** (`public-api.dream.gov.ua`) — public
  reconstruction-project registry.
- **МСС (inter-municipal cooperation) agreement registry** — dataset
  `912c1ea4-38ea-4648-8306-59fc1df8b51b` on data.gov.ua.

The `Goals`, `Projects`, `Strengths`, `Challenges`, `PartnersMentioned`, and
`MSSAgreements` fields are LLM extractions from the primary strategy
documents, not verbatim reproductions — treat them as a research aid, not a
substitute for the source PDF (linked in `StrategyUrl` where known).

## What this license does *not* cover

- `internal/` — draft outreach copy, not part of the dataset.
- `docs/hromada-project-passport.html` — a stakeholder brief, not a data
  file; reuse it as you would any other document on this repo (MIT-adjacent,
  ask first for anything beyond quoting).
