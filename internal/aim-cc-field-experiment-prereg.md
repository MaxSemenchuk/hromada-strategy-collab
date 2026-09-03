# Pre-registration (draft) — Field test of NLP match recommendations for Ukrainian hromadas

**Working title:** Do personalized strategy-match reports drive engagement and unprompted follow-up among Ukrainian local governments?
**Status:** Draft for AIM-CC 2026 consultation (not locked). Comments welcome before freeze.
**Contact:** Max Semenchuk · max.semenchuk@gmail.com · W3I Civic Tech Lab pilot
**Repo / data:** https://github.com/MaxSemenchuk/hromada-strategy-collab · CC BY 4.0 releases
**Date:** 2026-09-03 · **Version:** 0.5 (primary design pivoted to hromada-level report+engagement — see §12 Deviations log; original pair-based design kept as Appendix A)

---

## 1. Research question

Among Ukrainian territorial communities (*hromadas*) with structured development-strategy Goals, does a hromada that receives a personalized report containing a **model-selected partner recommendation** (multi-signal: goals · geo · MSS network · complementary need, via `recommend_for.py`'s "general" policy) show more **engagement and unprompted follow-up** than a hromada that receives a **benchmark-only report with no specific partner** (placebo)?

Secondary / exploratory (demoted from primary in v0.1–0.4 — see Appendix A): does a *thematic* (goals-similar) vs *operational* (geo-proximate) discovery signal produce different follow-up quality? This needs a dedicated geo-only arm, which the primary design below does not carry.

Note: the report presents the recommendation as a **hypothesis** ("here's a partner worth exploring, and why"), never as "AI matched you as perfect partners" or a verified compatibility score.

## 2. Design

- **Type:** parallel-arm field experiment (pilot RCT), **hromada-level randomization** — unit of randomization is **one hromada**, not a pair. This is the key structural change from v0.1–0.4 (see §12): it removes the pair/no-reuse corpus ceiling that hard-capped the old design at 146 pairs total, independent of how N was split across arms.
- **Delivery mechanism — portal view, not cold email.** The report (or placebo) renders as soon as the hromada representative visits the tool — e.g. during/after an existing touchpoint such as the ВАОТГ webinar, or via a link already embedded in an outreach channel the hromada checks for other reasons — rather than being sent cold and possibly never opened. This removes "did they even open it" as an independent, lossy funnel step; the funnel starts at engagement-with-content, not at delivery.
- **Blocking (preferred):** oblast macro-region × population band (tertiles), then randomize within blocks — same principle as v0.1–0.4 §2, now applied per hromada instead of per pair.
- **Blinding:** the hromada is not told which report type it received. Analysts coding outcomes are blind to arm if staffing allows.

## 3. Arms (2, primary)

| Arm | Content | Rationale |
|-----|---------|-----------|
| **R — Recommendation report** | Own Goals/context summary + the top model-selected partner pick from `recommend_for.py` (motivation="general": goals 45% + geo 25% + MSS-network 15% + complementary 15%) — partner, package (theme + suggested Law 1508-VII form), 1–3 signal chips, short "чому це вам допомагає" | Tests whether a real, multi-signal match recommendation drives engagement/follow-up beyond just being paid attention to |
| **B0 — Benchmark placebo** | Same personalized framing (own Goals summary, civic-tech barometer score from `edem-barometer.json`, population/oblast peer context) but **no specific partner named** | Isolates the effect of the recommendation itself from "someone made me a personalized report" — a real control, not a null/junk page (§9) |

The original 3-arm pair-based design (Arms A/B/C, testing thematic vs operational vs random-pair control) is retained as **Appendix A** — not deleted, demoted from primary scope. Its H2/H3 (does a geo-specific arm convert differently than a thematic one) become exploratory future work, since Arm R here blends goals+geo+network rather than isolating one signal.

**Sampling frame (current corpus):** **293** hromadas have parsed Goals text (`hromadas.json`, `Goals` field non-empty) — the pool Arm R draws from, since it needs a `recommend_for.py` card. Arm B0 does **not** structurally need Goals-matched hromadas (no recommendation to generate) — see the open item in §4.

## 4. Target N (pilot)

Corpus ceiling: Arm R is capped by the 293 goals-ready hromadas; with no hromada reused across arms, R+B0 combined can't exceed that pool without growing it or relaxing the reuse rule.

| Plan | Hromadas/arm | Total | Notes |
|------|--------------|-------|-------|
| **Pilot** | 125 | 250 | power(inbound-follow-up@30d) ≈ 32% at the elicited priors below — enough for consultation + a directional rate |
| **Full corpus** | 146 | 292 | ≈ 40% power — today's hard ceiling for a Goals-matched Arm R without new data collection |
| **Adequately powered** | ~300 | ~600 | ≈ 80% power — needs corpus growth beyond today's 293, or the open item below |

**Open item (not yet decided):** since Arm B0 doesn't need a Goals match, sourcing it from the full 1,463-hromada base instead of the 293 goals-ready pool would let Arm R alone use most of the 293-pool, materially raising achievable total N without any new data collection. Flagged here as the next design question, not yet implemented in the synthetic dry-run or committed as protocol.

This remains an **underpowered pilot** for small effects at the "Pilot" and "Full corpus" rows; primary goal there is feasibility + directional effect-size, not a definitive claim. Formal power analysis before scaling past the pilot (adaptive stop only for logistics, not peeking on H1).

## 5. Intervention

1. Every sampled hromada gets **one** report, per its arm assignment (R or B0), rendered on first portal visit — no separate "send" step with independent delivery risk (§2).
2. **Windows:** replied-to-the-report within 21 days (secondary); **unprompted inbound request for an intro/consult within 30 days** (primary) and within 90 days (secondary, cumulative).
3. **Facilitation:** same as v0.1–0.4 — once a hromada reaches out, an optional W3I-hosted call, same script checklist for both arms.
4. **Generation rule:** report content generated the same way for both arms — Goals snippets + `recommend_for.py` output for R, Goals snippets + benchmark stats for B0. Human-reviewed before the pilot launches (no unreviewed LLM output shown live).

## 6. Outcomes

**Primary (pre-registered):** binary **unprompted inbound request for an intro/consult within 30 days** of first portal view — the strongest, least-obligated signal: not a forced reply to an ask, but the hromada choosing to come back to us.

**Secondary (ordered ladder):**
1. clicked into the recommendation section (Arm R only) · 2. replied to the report at all, within 21 days · 3. inbound request within 90 days (cumulative, includes the 30-day ones) · 4. (exploratory, 12 months) new entry in the public МСС registry / KSE PIN edge.

**Moderator (exploratory, carried over from v0.1–0.4 §6):** seed has explicit МСС language in strategy (`mss-intents.json`); `edem_total` civic-tech proxy; same-rayon vs cross-rayon; confirmed EU twin (SKEW/C4C), per [docs/ua-eu-twinning.md](../docs/ua-eu-twinning.md).

## 7. Hypotheses

- **H1 (primary):** P(inbound request @30d | R) > P(inbound request @30d | B0)
- **H2 (secondary):** P(clicked-and-replied | R) > P(replied | B0) — engagement without the follow-up ask
- **H3 (moderation, exploratory):** explicit-ask seeds show a larger R−B0 gap than non-ask seeds
- **H4 (exploratory future work, from Appendix A):** does a thematic-only vs geo-only recommendation change follow-up conversion? Needs its own arm, not tested by the primary R/B0 design.

**Null of interest:** R ≈ B0 on inbound follow-up → a real, multi-signal recommendation adds nothing over a generic personalized report; the value people respond to is "someone made this for me," not the match itself.

## 8. Analysis plan

- **Main:** difference in primary inbound-@30d rates R vs B0; Fisher exact or Barnard (small N); report risk difference + Wilson CI.
- **No covariate fishing:** adjust only for pre-registered blocks (logistic / CMH if sparse).
- **Attrition:** portal-technical failures (broken link, page didn't render) coded separately from "viewed but didn't engage"; primary analysis ITT among successfully viewed reports.
- **Qualitative:** short code per hromada that reaches out — "asked intro to recommended partner / asked general consult / asked about own strategy only" (carried over in spirit from v0.1–0.4's post-call code).
- **Selection-bias caveat (H2):** "clicked-and-replied" conditions on engaging with content in the first place, which the design doesn't force — same caveat as v0.1–0.4's H3: report with the caveat, don't attempt a Heckman-style correction at pilot N.

## 9. Ethics & transparency

- Recommendations presented as **hypotheses**, never as verified compatibility.
- **B0 must still be a real placebo, not a null page:** every hromada gets genuine, honest, personalized value (its own Goals summary + civic-tech benchmark) — withholding a partner suggestion is the manipulation, not withholding effort or respect.
- Informed opt-in to continue after first inbound contact; easy opt-out.
- No targeting of communities without administrative capacity / security constraints.
- Public materials: aggregate rates only; no naming non-consenting hromadas.
- Open methods/data already under MIT + CC BY 4.0; experiment protocol frozen in this doc + dated git tag when launched.

## 10. What we ask AIM-CC mentors

| Mentor lens | Ask |
|-------------|-----|
| **Yasseri** | Hromada-level vs pair-level randomization — any hidden clustering/interference concern (e.g. two sampled hromadas being each other's real-world neighbours) we should block on? |
| **Smirnov** | Is "benchmark-only" a defensible placebo, or does it still read as a weak treatment rather than a true control? |
| **Taraktas** | Keep network prior out of treatment assignment (assign candidates from goals/geo/complementary layers only, per Arm R's motivation weights) |
| **Bessudnov** | Portal-view delivery assumption — how to actually secure "guaranteed view" in practice (webinar embed? existing dashboard?) without it becoming a selection filter on engaged hromadas only |
| **Koltsova** | Is report-template isomorphism a threat (same benchmark phrasing across many B0 hromadas reads as obviously generic)? |

## 11. Sizing note

Numbers in §4 come from a synthetic (no hromada contacted) Monte-Carlo dry-run — `scripts/analysis/aim_cc_synthetic_experiment.py --design report --guaranteed-view` — using elicited, illustrative funnel priors (open/reply/inbound rates), not real data; see `internal/aim-cc-synthetic-experiment-results.json` for the full run and `internal/aim-cc-synthetic-report-engagement-log.csv` for one simulated per-hromada log. Re-run before quoting any N or power number for a real launch decision — the goals-ready corpus size (293) and the priors are exactly the kind of thing that drifts.

## 12. Deviations log

**2026-09-03 (v0.5) — primary design changed.** From pair-level intro RCT (Arms A/B/C: thematic vs operational vs random-pair control, §1–8 through v0.4) to hromada-level report+engagement RCT (Arms R/B0: recommendation report vs benchmark placebo). Reason: a synthetic dry-run of the v0.4 design (`scripts/analysis/aim_cc_synthetic_experiment.py`) showed its no-hromada-reuse rule hard-caps total reach at **146 pairs** (293 goals-ready hromadas ÷ 2) *combined across every arm*, regardless of how N is split — the §4 "stretch" target of reaching hromadas via a partner association could not exceed that ceiling no matter the association's reach. Switching the randomization unit to one hromada removes the pairing constraint entirely; assuming a "guaranteed portal view" delivery (report renders on visit, no independent email-open funnel step) further raised simulated power at fixed N by roughly 2–3× versus a cold-email delivery of the same design (e.g. ≈13% → ≈40% power at the same 292-hromada ceiling). The old A/B/C design is retained as Appendix A, not deleted; its H2/H3 (geo vs thematic conversion) are demoted to exploratory future work since the primary design's Arm R blends signals rather than isolating one. All supporting power/rate numbers are from elicited-prior synthetic simulation, not observed funnel data.

*(Further changes after freeze → dated note here; do not silently edit §6–7.)*

---

## Appendix A — original pair-based design (v0.1–0.4, superseded as primary 2026-09-03)

Kept for reference and for the exploratory thematic-vs-geo question (H4 in §7 above). Not the active protocol.

### A.1 Design

- **Type:** parallel-arm field experiment (pilot RCT), pair-level randomization.
- **Unit of randomization:** unordered pair `{hromada_i, hromada_j}` (no existing curated `known: true` МСС between them).
- **Blocking (preferred):** oblast band × population band (tertiles), then randomize within blocks.
- **Blinding:** recipients are not told the arm; messengers use a fixed template skeleton. Analysts coding outcomes from email/CRM are blind to arm if staffing allows.

### A.2 Arms (3)

| Arm | Selection rule (from current matcher v7 release) | Rationale |
|-----|--------------------------------------------------|-----------|
| **A — Thematic** | Pair labeled `track=thematic` (or top goals-rank within seed's candidate list, geo not required) | Tests text-similarity as collaboration cue |
| **B — Operational** | Pair labeled `track=operational` (`geo_score` high, goals weak) | Tests "convenient neighbour" baseline common in practice |
| **C — Control** | Random pair from same Goals-ready corpus, **excluding** A/B eligible edges and known МСС; same oblast preferred when available | Isolates outreach effect of *any* intro vs model ranking |

**Framing note (2026-08-18):** two channels already drive most real-world МСС cooperation without any semantic/network recommendation at all: **Class 1 — geo-neighbor / personal-contact ties** (Tkachuk's 60–90% figure, `.cursor/rules/hromada-project.mdc` hard rule 9) and **Class 2 — UA↔EU twinning** ([docs/ua-eu-twinning.md](../docs/ua-eu-twinning.md), still under-studied). Arm B *is* this design's control for Class 1 — its purpose is isolating Arm A's thematic-match effect from "just being neighbors," not a side check. Class 2 isn't built into its own arm yet (too little studied to design against) but is tracked as an exploratory moderator.

**Sampling frame (pilot corpus, 2026-08-03 release):** **100** municipalities with Goals; **455** thematic / **150** operational / **4,345** mixed edges in `matching-edges.json` (4,950 pairs total). PIN∩corpus = **246**. Exclude pairs already in registry-confirmed `known: true`. Prefer seeds with working contact channel (email / PIN partner / prior W3I touch). *(Stale snapshot — the current corpus has grown; see the synthetic dry-run for live pool sizes.)*

### A.3 Target N (pilot)

| Plan | Pairs per arm | Total pairs | Notes |
|------|---------------|-------------|-------|
| **Minimum viable** | 8 | 24 | Enough for consultation + directional rates |
| **Preferred pilot** | 12 | 36 | Still feasible cold-outreach load |
| **Stretch** | 20 | 60 | Only with partner org (U-LEAD / PIN / association) |

**Hard ceiling (found 2026-09-03):** no-hromada-reuse across arms means the whole sample, all arms combined, can never exceed **146 pairs** (293 goals-ready hromadas ÷ 2) — the "stretch" row above is achievable, a 400-hromada target is not, without corpus growth. See §12.

This is an **underpowered** pilot for small effects; primary goal is **feasibility + effect-size estimate**, not definitive policy claim.

### A.4 Intervention (identical logistics across arms)

1. **Message (UA):** short email/Telegram — hypothesis language, not "AI matched you as perfect partners." Include: (a) 2–3 quoted goal fragments motivating the pair, (b) one concrete joint-project sketch, (c) ask for 30-min intro call within 21 days.
2. **Timing:** send to both sides same day; one reminder at day 10 if no reply.
3. **Facilitation:** optional W3I-hosted call; same script checklist for all arms.
4. **Generation rule (pre-commit):** either (i) **fixed human template** filled from stored Goals snippets, or (ii) **LLM-drafted** then human-edited — choose **one** before launch; if both are of interest, nest as 2×2 only after N≥36 (Bessudnov consult).

### A.5 Outcomes

**Primary (pre-registered):** binary **replied within 21 days** by ≥1 side (email/TG).

**Secondary (ordered ladder):** 1. both sides replied · 2. intro-call scheduled · 3. intro-call held · 4. agreed next step (doc exchange / joint concept) within 30 days · 5. (exploratory, 3 months) formal project concept/plan drafted · 6. (exploratory, 12 months) new entry in public МСС registry / KSE PIN edge.

**Moderator (exploratory):** seed has explicit МСС language in strategy (`mss-intents.json`); `edem_total` civic-tech proxy; same-rayon vs cross-rayon; confirmed EU twin (SKEW/C4C) on either side.

### A.6 Hypotheses

- **H1:** P(reply | A) > P(reply | C)
- **H2:** P(reply | B) > P(reply | C)
- **H3:** P(call held | A) ≥ P(call held | B) among pairs that reply *(thematic converts "interest" to "meeting" at least as well as geo)*
- **H4 (moderation, exploratory):** explicit-ask seeds show larger A−C gap than non-ask seeds

**Null of interest:** A ≈ B ≈ C on reply → recommendation content does not beat cold outreach / random intro in this channel.

### A.7 Analysis plan

- **Main:** difference in primary reply rates A vs C and B vs C; Fisher exact or Barnard (small N); report risk difference + Wilson CI.
- **No covariate fishing:** adjust only for pre-registered blocks (logistic / CMH if sparse).
- **Multiple arms:** H1/H2 primary family; H3/H4 secondary — no claim of confirmatory success on secondary alone.
- **Attrition:** undeliverable contacts coded separately; primary analysis ITT among successfully delivered sends.
- **Qualitative:** short post-call code — "recognized shared priority / rejected as irrelevant / capacity blocked."
- **Selection-bias caveat (H3):** "call held | replied" conditions on a post-treatment selection step (who replies) that may differ in composition between arms A and B, not just in size — naive comparison can confound arm effect with selection effect. A Heckman-style two-step correction is the textbook fix, but at pilot N (8–20 pairs/arm) it is not identifiable/stable without a strong exclusion-restriction instrument. Report H3 with this caveat rather than attempting the correction on pilot data.
