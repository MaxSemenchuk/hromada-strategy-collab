# Project history

Chronological record of methodology decisions, validation results, and honest
negative findings. Migrated from Claude Code project memory
(`project_hromada_strategy_collab.md`, w3i-network phase) on spin-out
(2026-07-23) and updated through KSE integration. **Prefer this file over
Claude memory** — it stays in-repo and tracks post-spin-out work.

For current status and setup, see [README.md](../README.md). For field schema,
see [hromadas-schema.md](hromadas-schema.md). For KSE division of labor, see
[kse-synergy.md](kse-synergy.md).

---

## Origin (2026-07-20/21)

Exploring corpus-level NLP on Ukrainian hromada **development strategies** to
surface МСС (inter-municipal cooperation) candidates and hromada↔W3I alignment
— instead of ad-hoc, relationship-based matchmaking.

**Prior-art check:** no public product does corpus-level strategy-text matching.
Adjacent work: U-LEAD single-hromada dashboards, manual МСС matchmaking (~762
registered agreements as of Jan 2026).

**Confirmed data sources:**

- data.gov.ua CKAN (`package_search`) — real strategy PDFs exist but the "123
  datasets" headline is mostly noise (~95% unrelated admin datasets; maybe 2–5
  usable strategy docs in that result set).
- DREAM public API — reconstruction/development project proxy.
- МСС registry (data.gov.ua) — ground truth for validation.
- No centralized machine-readable strategy repository — retrieval stays partly
  manual; strategies follow a standard Мінрегіон/SURGe template.

**NocoDB:** `Hromadas` table (`mjtetfuixggp5lg`), shared with w3i-network.
`Sectors` links to `Tags` (16 sector tags under `Category="Hromada Sector"`).

---

## Matching passes (chronological)

### Pass 1 — 7 hromadas, TF-IDF (2026-07-21)

**Selection:** Nizhyn/Baturyn/Kozelets (real registered МСС tourism cluster
ground truth) + Kryvyi Rih/Dnipro/Ternopil/Uzhhorod (top Мінцифри digital-index
hromadas).

**Result:** known МСС trio ranked **#1/#2/#3** of 21 pairs by goals-cosine.
Concept validated — model rediscovered real collaboration from goal text alone.

**Negative finding:** sector-tag Jaccard is useless — every pair scores 0.75–1.0
because the standard template touches nearly all sectors.

### Pass 2 — 13 hromadas (2026-07-21)

Added Kamianske/Novomoskovsk (Dnipro names them as agglomeration partners),
Chernihiv city + Yaremche (controls), Mukachevo/Nikopol (wild cards).

**Result:** known trio still top-3. Controls behaved correctly (Chernihiv low
despite same oblast; Yaremche low despite shared "Туризм" tag). **New candidate:**
Uzhhorod↔Mukachevo (#4, same oblast, no known agreement).

**Limitation:** Dnipro↔Kamianske/Novomoskovsk scored low despite being named
partners in Dnipro's text — declared partnerships ≠ goals-language overlap.

### Pass 3 — 23 hromadas (2026-07-21)

Added Slobozhanske↔Obukhivka (real МСС: shared CNAP / archbudcontrol) + 8 oblast
capitals.

**Result:** tourism trio still #1/#2/#4. **Honest failure:** Slobozhanske↔Obukhivka
ranked **#132 of 253** (cosine 0.06). Operational back-office cooperation does not
appear in Goals sections; Obukhivka had thin proxy-only source text.

**Scope conclusion:** goals-cosine finds **thematic** collaboration candidates,
not **operational** neighbor-resource sharing (CNAP, fire, waste).

### Pass 4 — 30 hromadas + proximity signal (2026-07-21)

Added weighted combination: **60% goals-cosine + 40% proximity** (rayon/oblast
adjacency). Recovered Slobozhanske↔Obukhivka to combined rank **#6**.

**Caution:** Poltava↔Zhytomyr topped new-candidate list (0.374) — likely
"comprehensive long document" hub effect, not genuine vision match.

### Pass 5 — 44–54 hromadas, embeddings (2026-07-22)

Upgraded to `intfloat/multilingual-e5-small`, sub-goal level, mean-centered.

**Raw embeddings failed** (0.89–0.97 band, known cluster fell to ~#24). **Fix:**
subtract corpus-mean sub-goal vector before comparing — strips shared bureaucratic
register.

**Template collision false positive:** Hannivska↔Tulchynska scored 0.902 —
near-verbatim identical goal titles from same consulting template. Corpus-wide
statistical reweighting over-corrected and buried the real cluster. **Final fix:**
keep scorer unchanged; add transparent flag for subgoal-line duplicates
(difflib ratio ≥0.98).

**Surviving new candidates after scrutiny:**

- **Halytska↔Dubovetska (0.382)** — same rayon, explicit planned shared water
  network in source text.
- **Novomoskovsk↔Zaporizhzhia (#1 of 1035 at 46-hromada stage, 0.571)** —
  industrial/recovery similarity; unverified hypothesis.

### Pass 6 — stratified random sample (2026-07-22)

Curated sample was NOT representative (mostly miska; rural silska absent). Drew
17 hromadas stratified from KATOTTG (seed=42). ~30% honest not-found rate on
random small hromadas vs near-100% on curated sample.

---

## Infrastructure milestones

| Date | Milestone |
|------|-----------|
| 2026-07-22 | `structure-hromada-strategy.ts` — Groq default (`llama-3.3-70b-versatile`); Gemini region-gated for this account |
| 2026-07-22 | Cost lesson: split retrieval (in-session) from structuring (cheap external LLM); ~60–150k tokens per full Agent extraction |
| 2026-07-23 | KATOTTG + population bulk import — **1,469 mainland hromadas** metadata in NocoDB |
| 2026-07-23 | `DonorsPrograms` field — 174/1469 (12%) tagged; floor not ceiling |
| 2026-07-23 | Spin-out from `w3i-network` into this repo; NocoDB still shared |
| 2026-07-23 | KSE-Loc-Data-Hub review; `kse-pin.json`, `enrich_from_kse.py`, `match.py` v6 |
| 2026-07-23 | Public dataset: `data/releases/hromadas.json`, `matching-edges.json` |

---

## Spin-out (2026-07-23)

Code moved to `hromada-strategy-collab` as its own MIT-licensed repo. Dataset in
`data/releases/` is CC BY 4.0. NocoDB base remains shared with w3i-network
(deliberate temporary choice).

Retrieval batch workflow added under `scripts/retrieval/` (CKAN search →
batch queue → structure → export → match).

---

## KSE integration (2026-07-23)

[KSE-Loc-Data-Hub](https://github.com/kse-ua/KSE-Loc-Data-Hub) covers the same
1,469 hromadas with ~130 covariates; we join on **KATOTTG** at analysis time.

**We consume:** geography (proximity), edem (`edem-data.csv` only — not
`full_dataset.csv` where NA→0), partnerships network, war status.

**We contribute back:** strategy extractions, matching-edge hypotheses,
retrieval nulls.

**Matching v6** (`scripts/analysis/match.py`):

```
combined = 0.60 × goals_cosine + 0.25 × geo_score + 0.15 × mss_network
```

Goals scorer: mean-centered sub-goal embeddings + document-frequency downweight
on highly shared subgoal lines. KSE covariates fetched lazily via
`enrich_from_kse.py` — not vendored in repo.

---

## Ground-truth validation pairs

| Pair | Type | Expected behavior |
|------|------|-------------------|
| Nizhyn ↔ Kozelets ↔ Baturyn | Registered МСС tourism cluster | Top ranks on every pass |
| Slobozhanske ↔ Obukhivka | Registered operational (CNAP) | Low on pure cosine; recovered with geo weight |
| Dnipro ↔ Kamianske/Novomoskovsk | Named in strategy text | Low cosine — limitation, not bug |

Run `yarn test-known-pairs` after changing the matcher.

---

## Methodology guardrails (do not regress)

1. **Sector tags:** browsing/filtering only — never the primary matching signal.
2. **Matching scores:** unverified hypotheses unless `known: true` against registry.
3. **Template collisions:** flag near-verbatim subgoal duplicates; do not apply
   corpus-wide reweighting on small N.
4. **edem_total:** missing ≠ zero; use `edem-data.csv` only.
5. **CKAN "123 strategies":** do not cite as coverage estimate.
6. **DonorsPrograms:** absence means "not found in pass," not "no program."
7. **Cost:** do not run full Agent retrieval+structuring for batch growth — use
   `scripts/retrieval/` + `yarn structure-hromada`.

---

## Open threads (as of 2026-07-23)

- [ ] File cross-link issue on KSE repo ([kse-issue-draft.md](kse-issue-draft.md))
- [ ] Re-scrutinize `internal/outreach-messages.md` for overclaims
- [ ] Resolve 5–7 snowball retrieval targets or accept ~57-hromada pilot cap
- [ ] Length-normalization / hub-hromada handling (Poltava-Zhytomyr-type risk)
- [ ] Product/graph layer decision still pending — pilot validation stage
- [ ] Split NocoDB base if project grows into standalone product

---

## Stakeholder artifacts (Claude Code)

- [Матчинг громад за стратегіями розвитку](https://claude.ai/code/artifact/6913283b-0450-477b-88fa-bcc0ed3775e9) — Ukrainian brief
- [Паспорт проєкту](https://claude.ai/code/artifact/f67810d5-dc4e-4291-937e-c3db24e452c5) — confidence-tiered findings

Local HTML copies: [hromada-project-passport.html](hromada-project-passport.html),
[mss-graph-mvp.html](mss-graph-mvp.html).
