# Proposal: Interreg as the first EU instrument (decision draft)

**Status:** decision-ready proposal · 2026-09-16  
**Builds on:** [eu-transfer-one-pager.md](eu-transfer-one-pager.md) ·
[project-strategy-future-backwards.md](project-strategy-future-backwards.md)
Brief 3 · existing `yarn interreg` → `data/releases/interreg-partners.json`  
**Not public:** keep in `internal/` until an outreach target is chosen.

---

## Decision (lock these three)

| Axis | Choice | Why |
|------|--------|-----|
| **Instrument** | **Interreg** (NEXT CBC + related programmes covering UA; Interreg Europe as secondary track later) | Funded, multi-year, application-based — closest structural analogue to Law 1508 МСС among EU instruments. Validation dataset already exists ([keep.eu](https://keep.eu)). |
| **Product** | **(b)** UA hromada → EU partner / Interreg readiness — *not* (a) EU↔EU municipal matching | Bridge data already in-repo (SKEW/C4C twinning + Interreg partners). (a) needs a new EU corpus + agreement registry; defer. |
| **Role of UA work** | Domestic МСС = **validation experiment** for the method; Interreg = **programme-shaped product** for border / eligible hromadas | Matches prior lean (funding form = embedded in a real programme, not standalone Ukraine-only research). |

**Explicit non-goals for v1**

- Do not fold Interreg into v7 combined `score`.
- Do not set `known: true` on Interreg edges (flag stays domestic curated МСС).
- Do not sell “AI finds your EU twin” — pitch is **eligibility · theme · existing partners · concrete ask**, with brokerage (JSCs / national contact / associations) still required.
- Do not conflate Interreg with municipal twinning (SKEW/C4C) or domestic МСС — three separate layers.

---

## What we already have (evidence, not vapour)

| Asset | Fact (as of 2026-09-15 manifest) | Honest use |
|-------|-----------------------------------|------------|
| `yarn interreg` / keep.eu | 1,553 projects scanned; 100 hromadas town-matched; **43 hromadas / 57 partnerships** with `organisation_type == Local public authority` | Treat **43 / 57** as the Interreg analogue of SKEW edges — not the 100 town-hits |
| Historical 2000–2020 | Expands counts but `organisation_type` is null → no extra *confirmed* LPA ties | Use for context only |
| Programmes in scope | PL–UA, HU–SK–RO–UA, RO–UA, Danube, Black Sea Basin | Eligibility geography is western / basin — not all-Ukraine |
| Twinning layer | Separate node highlight | Complements Interreg (people channel vs project channel) |
| Strategy corpus + themes + explicit ask | Domestic NLP already running | Reuse for **UA-side Interreg pitch card**, not for EU↔EU cosine yet |

---

## Product shape (MVP → pilot)

### MVP (build from existing releases — weeks, not a new matcher)

**Interreg readiness card** per eligible hromada:

1. **Eligible?** — oblast / programme territory gate (NEXT PL–UA etc.)
2. **Themes** — map goals/challenges → programme-friendly buckets (environment, health, accessibility, borders, resilience, water, energy…)
3. **Already in Interreg?** — LPA-confirmed keep.eu partners + project names (filter `is_local_authority`)
4. **EU people channel** — SKEW/C4C twins if any (often the warm intro *into* a later Interreg concept)
5. **Concrete ask** — one sentence from challenges / DREAM / international-coop language (not “looking for a partner”)
6. **Win-win line** — what the UA side offers (wartime service continuity / basin / border practice)

UI: block on map/card + short export for brokers. Label: discovery evidence, not a grant award.

### Phase 2 (only if MVP used by a real broker / JTS / association)

- Shortlist **EU co-applicants** for a named call (needs EU partner profiles — start from keep.eu partners on past projects in the same programme + theme, not from inventing EU strategy cosine).
- Optional: Poland `strategia rozwoju gminy` corpus later — for (a) or for PL–UA pair hypotheses — gated on Phase 2 demand.

### Phase 3 (do not open in parallel)

- Full EU↔EU matching / EGTC / LEADER — separate instruments, separate validation.

---

## Audience & ask (pick one primary)

| Audience | Pitch in one line | Ask |
|----------|-------------------|-----|
| **Primary: Interreg NEXT national / JTS / programme side (PL–UA first)** | We turn open keep.eu + UA strategies into hromada-level readiness cards so eligible municipalities enter calls with a clearer partner ask | Pilot on N eligible western hromadas; feedback on whether cards help pre-call matchmaking |
| Secondary: ВА ОТГ / ВАГ (western oblasts) | Same cards for association warm intros | Warm intros to 5–10 heads, not cold blast |
| Secondary: GIZ / SKEW bridge | Twinned hromadas → Interreg concept track | Co-brand a small batch where twinning already exists |
| Not first: АМУ / all-Ukraine CDTO | Wrong geography and wrong instrument framing for CBC | — |

**Message discipline (Tkachuk):** motivation and benefit clarity > venue; AI lowers search cost, does not replace trust or Monitoring Committee rules.

---

## Success criteria (go / no-go)

| Horizon | Signal |
|---------|--------|
| 30 days after cards live | ≥1 programme/association actor uses cards in a real conversation |
| 90 days | ≥3 hromadas draft or refine an Interreg project concept using the card (exploratory rung — not signed grant) |
| No-go | Cards unused after outreach round → keep Interreg as **data layer only**, do not expand to EU cosine matching |

Do **not** claim predictive validity on Interreg until a forward-test is pre-registered against LPA-confirmed keep.eu edges (same spirit as AIM-CC / Brief 2). Domestic Brief 2 still preferred before a big EU funder pitch.

---

## Sequencing vs other briefs

1. Keep publishing domestic multi-signal packages (current product).
2. Ship Interreg **MVP cards** from existing `interreg-partners` + themes (this proposal).
3. Brief 2 (predictive validity) remains the gate for a large “EU platform” claim.
4. Do not open product (a) EU↔EU until (b) has a broker using it.

---

## One-paragraph external blurb (EN)

> We map Ukrainian hromada development strategies to Interreg NEXT cooperation.
> Using the public keep.eu project database and our structured strategy corpus,
> we publish readiness cards: programme eligibility, thematic fit, confirmed
> local-authority Interreg history, and a concrete cooperation ask — separately
> from domestic inter-municipal agreements and from sister-city twinning.
> The aim is to lower partner-search cost for eligible border municipalities
> before a call, not to replace programme rules or personal brokerage.

---

## Decision log stub

- **Proposed 2026-09-16:** lock Interreg + product (b) + MVP readiness cards as above.
- **Accepted / amended / deferred:** _(fill when Max decides)_
