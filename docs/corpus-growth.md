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
   (optional `--write` for NocoDB sync)
4. If hierarchy curated: add to `data/sources/goals-hierarchy-overrides.json`
5. `yarn build-goals-hierarchy && yarn extract-mss-intents && yarn match && yarn export-matching-edges && yarn test-known-pairs && yarn complementary-match && yarn graph-pin-matching && yarn build-matches-preview`

## Target (pilot)

- **+30–50** full/partial Goals (toward ~100–120 with text), prioritizing:
  - high `corpusPinLinks` in `corpus-growth-priority.json`
  - low-МСС / under-sampled oblasts
  - сільські / селищні (міські зараз надпредставлені)

## Status

Tooling is ready; bulk structuring remains manual (in-session). Do not claim
full 1 469 coverage.
