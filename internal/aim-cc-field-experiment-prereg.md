# Pre-registration (draft) — Field test of NLP match recommendations for Ukrainian hromadas

**Working title:** Do strategy-text match recommendations increase contact between local governments?  
**Status:** Draft for AIM-CC 2026 consultation (not locked). Comments welcome before freeze.  
**Contact:** Max Semenchuk · max.semenchuk@gmail.com · W3I Civic Tech Lab pilot  
**Repo / data:** https://github.com/MaxSemenchuk/hromada-strategy-collab · CC BY 4.0 releases  
**Date:** 2026-07-30 · **Version:** 0.2 (sampling frame refreshed 2026-08-04)

---

## 1. Research question

Among Ukrainian territorial communities (*hromadas*) with structured development-strategy Goals, does sending a **model-selected IMC agreement-package recommendation** (pair · theme · suggested legal form, with evidence) raise the probability of **reply / intro-call / follow-up**, relative to a **geography-only** recommendation and a **control**?

Secondary: does *thematic* (goals-similar) vs *operational* (geo-proximate, weak goals) **discovery signal** produce different follow-up quality?

Note: experiment arms test **signals** (how the pair was found), not legal-form buckets. The treatment message still presents an agreement **package** hypothesis, not a “strategy twin” score.

## 2. Design

- **Type:** parallel-arm field experiment (pilot RCT), pair-level randomization.
- **Unit of randomization:** unordered pair `{hromada_i, hromada_j}` (no existing curated `known: true` МСС between them).
- **Blocking (preferred):** oblast band × population band (tertiles), then randomize within blocks.
- **Blinding:** recipients are not told the arm; messengers use a fixed template skeleton. Analysts coding outcomes from email/CRM are blind to arm if staffing allows.

## 3. Arms (3)

| Arm | Selection rule (from current matcher v7 release) | Rationale |
|-----|--------------------------------------------------|-----------|
| **A — Thematic** | Pair labeled `track=thematic` (or top goals-rank within seed’s candidate list, geo not required) | Tests text-similarity as collaboration cue |
| **B — Operational** | Pair labeled `track=operational` (`geo_score` high, goals weak) | Tests “convenient neighbour” baseline common in practice |
| **C — Control** | Random pair from same Goals-ready corpus, **excluding** A/B eligible edges and known МСС; same oblast preferred when available | Isolates outreach effect of *any* intro vs model ranking |

**Sampling frame (pilot corpus, 2026-08-03 release):** **100** municipalities with Goals; **455** thematic / **150** operational / **4,345** mixed edges in `matching-edges.json` (4,950 pairs total). PIN∩corpus = **246**. Exclude pairs already in registry-confirmed `known: true`. Prefer seeds with working contact channel (email / PIN partner / prior W3I touch).

## 4. Target N (pilot)

| Plan | Pairs per arm | Total pairs | Notes |
|------|---------------|-------------|-------|
| **Minimum viable** | 8 | 24 | Enough for consultation + directional rates |
| **Preferred pilot** | 12 | 36 | Still feasible cold-outreach load |
| **Stretch** | 20 | 60 | Only with partner org (U-LEAD / PIN / association) |

This is an **underpowered** pilot for small effects; primary goal is **feasibility + effect-size estimate**, not definitive policy claim. Formal power analysis after first 12 replies (adaptive stop only for logistics, not peeking on H1).

## 5. Intervention (identical logistics across arms)

1. **Message (UA):** short email/Telegram — hypothesis language, not “AI matched you as perfect partners.” Include: (a) 2–3 quoted goal fragments motivating the pair, (b) one concrete joint-project sketch, (c) ask for 30-min intro call within 14 days.  
2. **Timing:** send to both sides same day; one reminder at day 7 if no reply.  
3. **Facilitation:** optional W3I-hosted call; same script checklist for all arms.  
4. **Generation rule (pre-commit):** either (i) **fixed human template** filled from stored Goals snippets, or (ii) **LLM-drafted** then human-edited — choose **one** before launch; if both are of interest, nest as 2×2 only after N≥36 (Bessudnov consult).

## 6. Outcomes

**Primary (pre-registered):** binary **replied within 14 days** by ≥1 side (email/TG).

**Secondary (ordered ladder):**  
1. both sides replied · 2. intro-call scheduled · 3. intro-call held · 4. agreed next step (doc exchange / joint concept) within 30 days · 5. (exploratory, 12 months) new entry in public МСС registry / KSE PIN edge.

**Moderator (exploratory):** seed has explicit МСС language in strategy (`mss-intents.json`); `edem_total` civic-tech proxy; same-rayon vs cross-rayon.

## 7. Hypotheses

- **H1:** P(reply | A) > P(reply | C)  
- **H2:** P(reply | B) > P(reply | C)  
- **H3:** P(call held | A) ≥ P(call held | B) among pairs that reply *(thematic converts “interest” to “meeting” at least as well as geo)*  
- **H4 (moderation, exploratory):** explicit-ask seeds show larger A−C gap than non-ask seeds  

**Null of interest:** A ≈ B ≈ C on reply → recommendation content does not beat cold outreach / random intro in this channel.

## 8. Analysis plan

- **Main:** difference in primary reply rates A vs C and B vs C; Fisher exact or Barnard (small N); report risk difference + Wilson CI.  
- **No covariate fishing:** adjust only for pre-registered blocks (logistic / CMH if sparse).  
- **Multiple arms:** H1/H2 primary family; H3/H4 secondary — no claim of confirmatory success on secondary alone.  
- **Attrition:** undeliverable contacts coded separately; primary analysis ITT among successfully delivered sends.  
- **Qualitative:** short post-call code — “recognized shared priority / rejected as irrelevant / capacity blocked.”

## 9. Ethics & transparency

- Scores presented as **hypotheses**, never as verified compatibility.  
- Informed opt-in to continue after first reply; easy opt-out.  
- No targeting of communities without administrative capacity / security constraints.  
- Public materials: aggregate rates only; no naming non-consenting hromadas.  
- Open methods/data already under MIT + CC BY 4.0; experiment protocol frozen in this doc + dated git tag when launched.

## 10. What we ask AIM-CC mentors

| Mentor lens | Ask |
|-------------|-----|
| **Yasseri** | Lock outcomes, clustering (pair vs seed), and whether waitlist-control is cleaner than random-pair control |
| **Smirnov** | Human rating of message quality / pair plausibility as manipulation check |
| **Taraktas** | Keep network prior out of treatment assignment (assign from goals/geo layers only) |
| **Bessudnov** | Template vs LLM message — confound vs separate factor |
| **Koltsova** | Is strategy-text isomorphism a threat (template copy across hromadas)? |

## 11. Deviations log

*(Empty until launch. Any change after freeze → dated note here; do not silently edit §6–7.)*
