# Priority corpus growth

Grow strategy text where it adds **PIN ∩ corpus** validation pairs (KSE МСС
neighbours of hromadas that already have `Goals`).

## Commands

```bash
yarn priority-corpus-growth   # → data/releases/corpus-growth-priority.json
```

Then for each candidate:

1. Find strategy PDF (portal / CKAN / Wayback) → add to `scripts/retrieval/batch-queue.json`
2. `yarn download-raw` (or manual download into `scripts/retrieval/raw/`)
3. In-session structure with **hierarchy** (`strategic_goals`, `operational_goals`,
   `mss_intents`) → `yarn structure-hromada --json … --write-release`
4. If hierarchy curated: add to `data/sources/goals-hierarchy-overrides.json`
5. `yarn build-goals-hierarchy && yarn extract-mss-intents && yarn match && yarn export-matching-edges && yarn test-known-pairs && yarn complementary-match && yarn graph-pin-matching && yarn build-matches-preview`

## Target (pilot)

- **Done (GISRR 2026-08 + 2026-09-15 + thin-oblast + UA-VPN PIN 2026-09-16):**
  ~394 Goals in release (GISRR catalog 315 ТГ; second fold-in upserted 87
  new; then Боратинська + Рожищенська + Леськівська; then UA-VPN pack
  Колочава / Міжгір’я / Синевир / Поляна / Ківерці / Маневичі / Воловець /
  Неліпино / Надвірна). Next prioritize:
  - high `corpusPinLinks` in `corpus-growth-priority.json` (remaining western
    PIN hubs without a public strategy: Слобідсько-Кульчієвецька,
    Китайгородська, Іване-Пустенська). Жденіївська / Пилипецька still
    drafting or without a portal PDF.
  - still-thin oblasts (Волинська 6/53, Черкаська 4/66, Житомирська 3/65,
    Хмельницька 3/60)
  - сільські / селищні (міські зараз надпредставлені)

## Status

Tooling is ready; GISRR is the cheap bulk path. Remaining PIN-neighbour
growth is still partly in-session (portal PDFs). Do not claim full 1 469
coverage.
