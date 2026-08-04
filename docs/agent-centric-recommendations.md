# Agent-centric recommendations vs global score

**Product unit stays the same:** candidate МСС agreement =
partner · package (theme · one of five Law 1508-VII forms) · 1–3 signal chips ·
short «чому це вам допомагає». Discovery signals ≠ legal forms.

## Two layers

| Layer | Role |
| ----- | ---- |
| **Global v7.1 score** (`0.60·goals + 0.25·geo + 0.15·mss_network`) | Lab / known-pair recovery baseline. Keep for `yarn test-known-pairs` and PIN∩corpus rank reports. **Not** the stakeholder UX claim. |
| **Agent-conditioned policy** | When municipality **A** opens the tool, re-rank *A’s* candidate edges by motivation / job-to-be-done. Output cards for A — never «у вас високий score». |

`mss_network` in the lab score is partly circular for registry recovery — fine for
validation. In agent UX it is only a **signal chip** («мережа МСС»), not proof.
Complementary / DREAM may inform agent policies; they are **not** folded into
v7.1 `score`. HydroBASINS / `same_basin` stays map context for water motivation —
never lab score, never `known: true`.

## Motivations v0

| `motivation` | Boost | Typical package hint |
| ------------ | ----- | -------------------- |
| `cut_costs_service` | geo (+ network as signal); theme ЦНАП / ЖКГ / пожежа… | ЦНАП — делегування / спільне утримання |
| `water_basin` | geo + complementary; water theme boost | вода — спільний проєкт |
| `tourism_cluster` | goals-first; geo optional | туризм — спільний проєкт |
| `general` (default) | balanced signal blend for seed A | existing package on the edge |

Rules-first weights live in
[`scripts/analysis/recommend_for.py`](../scripts/analysis/recommend_for.py)
(`MOTIVATIONS`). No learned weights in MVP.

## CLI / data flow

```text
data/releases/matching-edges.json
data/releases/matching-edges.complementary.json   (optional merge)
data/releases/hromadas.json                       (seed resolve by Name / KATOTTG)
        │
        ▼
  recommend_for(seed, motivation) → top-K cards
        │
        ├── yarn recommend-for --seed "Галицька" --motivation water_basin
        └── yarn build-recommend-preview → docs/assets/recommend-for-preview.json
                                              └── matches.html «Для цієї громади»
```

Does **not** rematch the corpus. Does **not** change `KNOWN_PAIRS` or v7.1
weights. Packages remain hypotheses unless `known: true` (curated only).

```bash
yarn recommend-for --seed "Галицька" --motivation water_basin
yarn recommend-for --katottg UA26020030000088465 --motivation cut_costs_service -k 8 --json
yarn recommend-for --list-motivations
yarn test-recommend-for
yarn build-recommend-preview
```

## UI

On [matches.html](matches.html): pick a Goals hromada + motivation → cards
(partner · package · chips · why). Global top / known / PIN tables stay for
method transparency and validation.

## Out of scope (MVP)

Training weights on the full MSS registry; multi-agent simulation; replacing
v7.1; setting `known: true` from packages.
