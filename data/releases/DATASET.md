# Dataset card — Hromada Strategy Collaboration Mapping

Open data on Ukrainian territorial communities (hromadas): their development
strategies, digital-democracy activity, reconstruction-project priorities,
international partnerships, and candidate inter-municipal cooperation (ММС)
links. License **CC BY 4.0** ([DATA-LICENSE.md](../../DATA-LICENSE.md)); cite via
[CITATION.cff](../../CITATION.cff) / Zenodo DOI
[10.5281/zenodo.22552879](https://doi.org/10.5281/zenodo.22552879).

## Read this first

- **The universe is complete, the content is not.** `hromadas.json` has all
  1,463 hromadas with metadata, but strategy-derived fields (`Goals`,
  `Projects`, `Challenges`, …) exist for only **394 (27%)**, and that subset is
  **not a random sample** — it over-represents Poltava, Rivne, Kyiv,
  Dnipropetrovsk and Zakarpattia, and has 1–3 rows for Luhansk and Zhytomyr.
  Do not generalise strategy findings to the whole country.
- **Snapshots, not a panel.** Each layer is dated (see its `*.manifest.json`);
  layers were generated on different days.
- **Extracted fields are model-assisted.** Strategy fields were extracted from
  source PDFs by an LLM pipeline; quotes in `mss-intents.json` are hypotheses
  to verify against the source before outreach.
- **Matching output is hypotheses.** Nothing in `matching-edges*.json` or
  `mss-candidates.json` is a verified agreement unless `known: true` /
  `status: registry_known`.
- **Absence ≠ none.** An empty `DonorsPrograms`, `PartnersMentioned` or
  twinning entry means "not found by our passes", a floor on coverage.

## Join key

`Katottg` (КАТОТТГ code, e.g. `UA74040250000063494`) — present and unique on all
1,463 `hromadas.json` rows. Layers use `katottg` (lower-case). Hromada **names
are not unique** (several `Вишнівська`, `Жданівська`…) — always join on the code.
Some hromadas were renamed after 2022 (e.g. Червоноградська → Шептицька,
Новоград-Волинська → Звягельська); release names follow the current official
name and codes come from the KSE admin map
([katottg-overrides.json](../sources/katottg-overrides.json)).
27 rows are in occupied territory and have no `Rayon`/`Population` from the
current pipeline unless taken from KSE 2022.

## Files

CSV mirrors are in [`csv/`](csv/) (UTF-8 with BOM, lists joined by `; `).
JSON is canonical.

| File | Unit | Rows | Coverage / notes |
|------|------|------|------------------|
| `hromadas.json` | hromada | 1,463 | metadata complete; Goals 394, Projects 363, Challenges 379, StrategyUrl 329, DonorsPrograms 185, PortalUrl 36. Schema: [docs/hromadas-schema.md](../../docs/hromadas-schema.md) |
| `edem-barometer.json` | hromada | 1,424 | live e-dem.ua API snapshot (2026-09-01); 599 hromadas connected to any platform; absolute and per-capita scores |
| `dream-priorities.json` | hromada | 1,027 | revealed priorities from 14,782 non-cancelled DREAM projects (2026-07-29); sectors via controlled vocabulary |
| `twinning-partners.json` | hromada | 374 | UA–EU partnerships: SKEW (DE), AFCCRE (FR) registries; Cities4Cities and strategy mentions are weaker hypotheses (`confidence` field) |
| `intl-agreements.json` | hromada | 107 | 197 agreements from the Law 3668-IX register; heuristic themes |
| `mss-intents.json` | hromada | 218 | explicit ММС language quoted from strategies |
| `goals-hierarchy.json`, `strategy-entities.json` | hromada | – | strategic/operational goal hierarchy; named objects and neighbours |
| `hromada-resources.json`, `donor-synergy.json`, `plich-o-plich.json`, `partnership-map.json`, `interreg-partners.json` | various | – | covariate and network layers |
| `matching-edges*.json`, `mss-candidates.json` | pair | – | v7.3 candidate ranking (see [MANIFEST.md](MANIFEST.md)); hypotheses |

## Known issues

- `Sectors` was removed from `hromadas.json` (it was never populated). For
  sector signal use `dream-priorities.json` (`sector_counts`); a strategy-based
  sector tag is a future extraction.
- `hromadas.json` `Rayon` values mix pre- and post-2020 spellings.
- `PortalUrl` is only set where it could be derived from the strategy host.
- Upstream licenses differ per source; see DATA-LICENSE.md.

## Regenerate

```bash
yarn apply-hromada-fixes   # key/Oblast hygiene on hromadas.json
yarn export-csv            # data/releases/csv/*.csv from the JSON
```

Per-layer builders are listed in [MANIFEST.md](MANIFEST.md).
