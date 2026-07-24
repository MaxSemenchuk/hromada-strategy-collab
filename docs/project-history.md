# Project history

Chronological record of methodology decisions, validation results, and honest
negative findings. Migrated from Claude Code project memory
(`project_hromada_strategy_collab.md`, w3i-network phase) on spin-out
(2026-07-23) and updated through KSE integration and the 2026-07-24 МСС
registry geography/types read. **Prefer this file over Claude memory** — it
stays in-repo and tracks post-spin-out work.

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
| 2026-07-22 | `structure-hromada-strategy.ts` — external LLM structuring tried (Groq then Gemini); both dropped |
| 2026-07-23 | Structuring is in-session only; yarn script persists `--json` to NocoDB |
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

**PIN ∩ corpus (broader KSE check, not hard regression):** every matching edge
with `mss_network>0` (both sides have Goals). Curated `known: true` stays a
subset. Soft report: `yarn report-pin-corpus` →
`data/releases/matching-edges.pin-corpus.json`. Map layer **PIN ∩ корпус**
(coral) vs gold known. Score already includes 15% `mss_network` — ranks are
partly circular; use this as coverage diagnostics, not as a second known set.

**Corpus growth for more overlap:** `yarn priority-corpus-growth` lists PIN
neighbours of the Goals corpus that still lack strategy text
(`data/releases/corpus-growth-priority.json`). Distinct from low-МСС oblast
prioritisation for *discovery* whitespace (see § Practical conclusions).

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

## МСС registry geography & types → matching implications (2026-07-24)

One-off read of the official registry (Мінрегіон XLSX via `yarn fetch-mss-registry`,
899 agreements as of Dec 2022) joined with KSE
`partnerships-hromadas(-network).csv` (~2.4k edges; 614/1,469 hromadas with ≥1
agreement). Purpose: what the real agreement stock looks like, and what that
means for strategy-text matching.

### What the registry actually contains

**Legal forms (Law 1508-VII):** ~57% joint projects, ~25% joint financing /
shared upkeep of institutions, ~14% task delegation, &lt;3% joint municipal
enterprises or joint governing bodies.

**Themes (keyworded titles; ~half of titles are form-templates with no topic):**
CNAP/admin services ~11%; health + social services + education ~20%; waste +
fire + archbud ~10%; **tourism only ~5 named agreements (~0.6%)** — but those
few include the largest multi-party deals.

**Party structure:** bilateral dominates (~520), but **one-third have 3+
parties** — a distinct class (clusters / shared utilities), not noise.

**Geography (KSE network, reliable join on KATOTTG):**
- ~82% of edges same-oblast; of those, ~78% same-raion.
- Cross-oblast ~18% — almost all along natural corridors (Dnister canyon
  IF–Chernivtsi; Carpathian / Hutsul ethnos), not random long-range pairs.
- Coverage uneven: Poltava ~90% of hromadas have ≥1 МСС, Lviv ~85%, Vinnytsia
  ~75% vs Odesa ~18% and frontline oblasts in single digits.
- High-degree “hubs” are often members of **one large multi-party agreement**,
  not star brokers: e.g. reg#721 «Дністровський каньйон» (22 parties), #696
  «Гуцул етнос» (14), #659 waste-sorting plant (15), #752 «Місцями козацької
  сили» (5 — Nizhyn cluster plus Сухополов’янська and Парафіївська).

### Practical conclusions (plain language)

**1. “Similar strategies” ≠ “good CNAP neighbours.”**  
Most real МСС is operational back-office next door (CNAP, fire, waste, shared
school/social facility). Strategies rarely describe that. Goals-cosine targets
a rarer class: shared *development vision* (tourism, clusters). Do not sell one
score as answering both questions.

**2. v6 combined score often praises people we already know.**  
`0.60×goals + 0.25×geo + 0.15×mss_network` pushes same-oblast / already-linked
pairs up. Top combined ranks (Галицька↔Дубовецька↔Бурштинська) sit inside
reg#721; high score with goals ~0.05–0.07 is network+geo recognition, not a
new strategy discovery. Empirically on the pilot edges: top-50 by goals → only
1/50 same-oblast and 0/50 already in KSE network; top-50 by combined → 36/50
same-oblast and 9/50 already linked.

**3. Ship two ranked lists, not one.**  

| List | Signal | Use |
|------|--------|-----|
| **A — thematic** | high goals, geo can be low | cold-start vision partners; W3I outreach |
| **B — operational** | high geo / neighbourhood, goals may be low | CNAP / utilities / shared institutions |

List A = “who thinks like us.” List B = “who is convenient to share a service with.”

**4. Tourism / cluster МСС is rare in the registry but where NLP adds the most.**  
Few tourism contracts, yet they are the large multi-party (sometimes
cross-oblast) deals. Pairwise matching is enough for bilateral operational МСС;
clusters need multi-way / community view (the Nizhyn “trio” is really five
parties in KSE).

**5. Where the whitespace is.**  
Dense МСС oblasts (Poltava, Lviv, Vinnytsia) mostly yield “already
cooperating.” More matchmaking value in low-coverage oblasts (Odesa, Kyiv
oblast, frontline) — grow the strategy corpus there first.

**6. Near-term product rules.**  
- Do not present a single `score` as “strategy match.”  
- Label outputs `похожа стратегія` vs `зручний сусід`.  
- Keep `known: true` for method validation only — not as “new recommendations.”  
- Surface 3+ clusters, not only pairs.  
- Prioritise retrieval in low-МСС-coverage oblasts.

One line: **strategies find like-minded partners; geography finds service
co-sharers. v6 mixes them — strong signal, easy to misread.**

---


### Manual strategy ingest (2026-07-24)

User downloaded Cloudflare-blocked sources into a local folder and uploaded 13 files.
Mapped and structured in-session:

| Hromada | Change |
|---------|--------|
| Тульчинська | partial → **full-strategy** (Strategy 2030, 4 goals) |
| Лихівська | partial (1 priority) → **full-strategy** (3 priorities) |
| Великогаївська | partial → **full-strategy** (DOBRE DOCX enrich) |
| Батуринська | partial → **full-strategy** (full DOC body) |
| Вінницька | Goals expanded to all 6 Strategy 3.0 priorities |

Also cached (already full in release): Кривий Ріг (broken PDF text layer), Луцьк, Мукачево, Слобожанська, Вижницька (PDF+DOC), Херсон (PESR programme 2026–28, not template strategy). Missing from upload: Зноб-Новгородська, Новомосковська. Inventory: `scripts/retrieval/manual-ingest-2026-07-24.json`.

## Open threads (as of 2026-07-24)

- [ ] File cross-link issue on KSE repo ([kse-issue-draft.md](kse-issue-draft.md))
- [x] Stakeholder site under `docs/` + shared nav (GitHub Pages workflow)
- [x] Re-scrutinize `internal/outreach-messages.md` numbers / overclaims (2026-07-24)
- [ ] Resolve remaining snowball retrieval targets or accept ~77-hromada pilot cap
- [ ] Length-normalization / hub-hromada handling (Poltava-Zhytomyr-type risk)
- [ ] Product decision after first stakeholder conversations (open-data vs matchmaking vs W3I-internal)
- [ ] Split NocoDB base if project grows into standalone product
- [ ] Export `DonorsPrograms` into public `hromadas.json` when ready for donor outreach slices
- [x] Split matcher outputs into thematic vs operational ranked lists
      (`track` on edges + `matching-edges.thematic.json` /
      `matching-edges.operational.json`; scoring unchanged) — 2026-07-24
- [x] PIN map overlay: stop painting combined-score top-N as one
      «hypothesis» layer; show thematic (default ON) and operational
      («зручний сусід», default OFF) separately —
      `yarn graph-pin-matching` / `build_pin_matching_graph.py` — 2026-07-24
- [ ] Densify strategy corpus in low-МСС / under-sampled oblasts so
      operational neighbours are not an artifact of who got text-mined
- [ ] Multi-way / community view for 3+ party clusters (Nizhyn-5, Dnister-22)

---

## Stakeholder artifacts

Canonical leave-behind is the **GitHub Pages site** rooted at [`docs/`](./)
(shared nav: overview · passport · matches · map):

**https://maxsemenchuk.github.io/hromada-strategy-collab/**

| Page | File |
|------|------|
| Overview | [index.html](index.html) |
| Passport (UA brief) | [hromada-project-passport.html](hromada-project-passport.html) |
| Matching candidates | [matches.html](matches.html) |
| PIN map + matching | [mss-pin-matching-graph.html](mss-pin-matching-graph.html) |

Legacy Claude Code artifact URLs (superseded by Pages):

- [Матчинг громад…](https://claude.ai/code/artifact/6913283b-0450-477b-88fa-bcc0ed3775e9)
- [Паспорт проєкту](https://claude.ai/code/artifact/f67810d5-dc4e-4291-937e-c3db24e452c5)
