# 5-min presentation — speaking notes

Deadline: upload slides by Aug 15, 1pm. Present Aug 15 (check your group's slot: 2:00pm batch vs 3:40pm batch). ~5 min talk + 1 question.

Pacing target: ~150 words/min → ~750 words total. Notes below are bullets, not a script — talk from them.

---

## 1. Research question (~30-40s)

- Among Ukrainian *hromadas* (municipalities) with structured development-strategy documents, can text-derived matching **causally increase** inter-municipal cooperation (МСС) — not just correlate with it?
- Framed as three matching *signals* competing head-to-head: **thematic** (strategy-goal similarity) vs **operational** (geographic proximity) vs **random control**.
- Working paper title: *"Collaboration Matchmaking by Public Strategies: Evidence from a Field Experiment with Ukraine's Municipalities."*

## 2. Design & data (~60-75s)

- **Study 1 (retrospective, done)**: pooled MPLE tie-formation model over 316 real cooperation-agreement events (KATOTTG-joined registry + PIN corpus). Static/cross-sectional — the corpus only has one real network transition (2020→2021), not enough time-slices for anything temporal.
- **Study 2 (the headline evidence, pre-registered)**: parallel-arm field experiment, pair-level randomization, blocked by oblast × population tertile. Sampling frame: 100 municipalities with usable strategy Goals text, ~4,950 candidate pairs (455 thematic, 150 operational, rest mixed/control-eligible).
- Pilot target: 8–20 pairs/arm (24–60 pairs total) — explicitly underpowered for a definitive claim; goal is feasibility + effect-size estimate to power a full trial.
- Primary outcome: reply within 21 days. Secondary ladder: both-sides-reply → call scheduled → call held → agreed next step → (12mo exploratory) new registry entry.

## 3. Key findings so far (~60-75s)

- From Study 1 (the retrospective covariate model — cite as background, not the centerpiece):
  - **`geo_score` confirmed**, strong and precise: point estimate +9.3, 95% CI [+8.1, +11.2].
  - **`donor_overlap` tentatively confirmed**: +1.4, 95% CI [+0.05, +2.3] — barely excludes zero, second candidate signal.
  - Goals-text cosine similarity: **not confirmed** — CI spans zero once multi-party contracts are weighted correctly (one contract = one vote, not one vote per pair inside it).
- Framing point: geography is the strongest observational signal we have — which is exactly why the experiment needs a *thematic* arm distinct from a *geo* arm, to see whether matching on strategy content adds anything geo-proximity doesn't already give you.
- Study 2 has not launched yet — no experimental results to report yet; that's explicitly next.

## 4. What changed / what I developed this week (~90-120s) — this is the "school" section, spend real time here

- **Retired a method that didn't fit the data.** Came in with a TERGM (temporal ERGM) pilot in progress. Consulting with [mentor/Taraktaş-style network-analysis feedback] made clear the corpus only has one genuine time transition — TERGM needs multiple real time-sliced snapshots, this doesn't have them. Decision: archived that branch, kept the valid non-temporal covariate results (geo_score, donor_overlap), moved on rather than force-fitting a temporal model to cross-sectional data. *(Good "what I learned" moment for the question round: knowing when to abandon a method, not just apply one.)*
- **Repositioned the paper** around the field experiment as primary evidence, retrospective analysis as Study 1 support — this is more honest about what's actually been tested vs. hypothesized, and was a direct response to feedback that the original framing over-claimed from correlational data.
- **Built a formal game-theoretic frame for the mechanism**, added this week:
  - The core cooperation decision is a **Stag Hunt / assurance game**, not a prisoner's dilemma — mutual cooperation is payoff-dominant but risk-dominant defection can still win depending on each side's *belief* the other will follow through. This gives a mechanism for *why* the three experimental arms (thematic / geo / control) should differ: they move different combinations of "perceived payoff" and "belief the other side cooperates."
  - Extended this to a **two-layer risk model** (coordination risk *q* vs execution risk *r*) and built a Monte Carlo simulator (`coop_game_sim.py`) over real candidate pairs — reports expected value, probability of loss, and a loss-aversion-adjusted score, to make the shape of a hromada's actual go/no-go decision inspectable even before real experimental rates exist.
  - Framed as a discussion-section tool for interpreting whatever the experiment finds — including how to distinguish a null result caused by "genuinely not useful" vs "right idea, wrong risk layer" (capacity-blocked vs rejected-as-irrelevant vs pure non-response).

## Anticipated question — have an answer ready

- **"Isn't this underpowered / how do you know it'll show anything?"** → Yes, explicitly framed as a pilot for feasibility + effect-size estimation, not a definitive test; pre-registered precisely so a null is informative (and the qualitative post-call coding is designed to distinguish *why* a null happened, not just that it did).
- **"Why drop TERGM instead of collecting more time-slices?"** → Would need multiple years of dated agreement data; not available now. Cross-sectional covariate findings (geo, donor overlap) don't depend on the temporal part and survive the pivot.
- **"What's actually new/yours vs. mentor-suggested?"** → The Stag Hunt formalization + two-parameter (q, r) risk-decomposition + simulator is this week's original contribution; the method-abandonment decision on TERGM was also a call you made after taking in feedback rather than defaulting to "add more complexity."
