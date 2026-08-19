# Game-theoretic framing for the МСС cooperation mechanism

**Status:** analytical note, not a method change. Written to give the paper's
mechanism section (Study 2 / AIM-CC) a formal theoretical frame, and to log
which other game-theoretic frameworks fit other parts of the project for
later use. Does not modify
[internal/aim-cc-field-experiment-prereg.md](aim-cc-field-experiment-prereg.md)
— that document is frozen; any design change belongs in its §11 deviations
log, not here.

## 1. The core mechanism as an assurance game (Stag Hunt)

Tkachuk's finding — the tool doesn't replace trust between hromada heads
(60–90% of deals still go through personal contact), it lowers transaction
costs / uncertainty (see `.cursor/rules/hromada-project.mdc` hard rule 9,
also logged in
[project-strategy-future-backwards.md:47-52](project-strategy-future-backwards.md#L47-L52))
— has a direct formalization as a **Stag Hunt / assurance game**, not a
prisoner's dilemma.

For a candidate pair (i, j) deciding whether to invest real effort in
cooperation (attend an intro call, draft a joint concept, commit staff time):

| | j: Cooperate | j: Defect (no follow-through) |
|---|---|---|
| **i: Cooperate** | a, a | 0, b |
| **i: Defect** | b, 0 | b, b |

with `a > b > 0`: mutual cooperation beats the safe status quo, but the side
that invests alone gets nothing back — wasted staff time in a
capacity-constrained administration, plus the political cost of a visibly
failed overture.

This is a coordination game with two pure-strategy equilibria:
(Cooperate, Cooperate) is **payoff-dominant**, (Defect, Defect) is
**risk-dominant** whenever `b > a/2` (Harsanyi–Selten criterion). Which one
gets played is not determined by the actual size of `a` — it's determined by
each side's **belief that the other will also cooperate**. This is the
precise formal content of "the tool lowers uncertainty, not the need for
trust": the tool cannot change `a` or `b` on its own, but it can shift belief
about the other player's move, which is enough to flip equilibrium
selection.

## 2. Mapping the three AIM-CC arms onto the game's parameters

The three arms in
[aim-cc-field-experiment-prereg.md §3](aim-cc-field-experiment-prereg.md#3-arms-3)
are not just three ways of picking a pair — they are three different
interventions on the two things that determine equilibrium selection:
**perceived `a`** (how much is really at stake) and **P(other cooperates)**
(strategic uncertainty about the partner).

- **C — Control (random pair).** Moves neither parameter. No basis to
  believe this partner is unusually promising, no reason to think they're
  more likely to reply than any cold contact. This is the pure "Defect,
  Defect" baseline — the risk-dominant equilibrium with no coordination
  device applied.
- **B — Operational (geo-proximate).** Neighbouring hromadas already have a
  history of small repeated interactions (shared rayon meetings,
  administrative contact) — a repeated-game history that raises
  **P(other responds)** through familiarity, independent of whether the
  actual joint payoff `a` is large. Mechanism: reduces the fear of being
  the sucker, not necessarily the size of the prize.
- **A — Thematic.** The message quotes the recipient's *own* strategy-text
  goal fragments back to them and proposes a concrete joint-project sketch.
  This moves **both** parameters at once: it raises perceived `a` (the
  overlap is verifiable, not asserted), and it raises **P(other
  cooperates)** through a different channel than B — the recipient's own
  words function as a self-binding public commitment, making it harder for
  them to disclaim interest they already put in writing.

## 3. Predictions this framing generates for the pre-registered hypotheses

These are readings of H1–H4 (§7 of the prereg), not new hypotheses — the
assurance-game frame just gives a mechanism for *why* the pattern would show
up, which is useful for the discussion section regardless of which way the
results land.

- **H3 (A ≥ B converting reply → call held among repliers).** If B's
  advantage runs mainly through familiarity (cheap to answer a known
  neighbour), it should show up most at the **shallow** end of the outcome
  ladder (§6: reply) and fade at deeper, costlier stages (call held, next
  step) where a real `a` is needed to sustain investment. A's advantage,
  resting on both parameters, should hold up better across the full ladder.
  A result where B ≈ A on reply but A > B on call-held / next-step would be
  the signature of this distinction — worth checking even though H3 as
  pre-registered only tests the reply→call-held step.
- **H4 (explicit-ask moderator).** A hromada with pre-existing
  `explicit-ask` language in its strategy text has already partially
  resolved its own "am I the only one who wants this" doubt — a
  self-committing public statement made before the experiment ever touched
  it. Arm A's specific-partner suggestion is the missing piece to complete
  coordination for these seeds, which is exactly why H4 predicts a larger
  A−C gap among explicit-ask seeds than non-ask ones.
- **Null of interest (A ≈ B ≈ C).** Under this frame, a null doesn't mean
  "matching is useless" by default — it discriminates between two different
  failure stories, and the existing qualitative post-call coding (§8:
  "recognized shared priority / rejected as irrelevant / capacity blocked")
  already separates them:
  - if outcomes cluster on **capacity blocked**, the barrier isn't strategic
    uncertainty at all — it's a hard resource constraint, a different game
    (closer to a budget-constrained decision than a coordination problem),
    and facilitation tooling won't move it regardless of design.
  - if outcomes cluster on **rejected as irrelevant**, the problem is `a`
    itself being too small even when correctly perceived — a payoff
    problem, not a coordination problem, which argues for better targeting
    (higher-quality candidate pairs) rather than more persuasive
    facilitation.
  - only a null dominated by simple non-response with no qualitative signal
    either way would point at unresolved strategic uncertainty surviving
    treatment — i.e. the assurance-game story itself failing to explain the
    gap.

## 5. Simulating a specific future cooperation decision (two-layer risk model)

Sections 1–3 explain *whether a pair coordinates at all* (reply, meet,
follow through). That's necessary but not sufficient for a real decision
like "should hromada i and j invest in a shared ЦНАП, or a joint water-grant
application" — that decision also depends on whether the underlying project
actually pays off once an agreement exists, which is a separate source of
risk from coordination failure. Conflating the two overstates how much a
matching/facilitation tool alone can move the needle: it acts on
**coordination risk**, not on **execution risk**.

### 5.1 The model

Two risk layers per candidate pair, not one:

- **q** — P(negotiation succeeds, agreement signed). This is the Stag Hunt
  layer from §1–2: driven by trust, reciprocity belief, facilitation.
- **r** — P(the joint project delivers value | agreement signed). This is a
  separate execution/market risk: will the grant actually be awarded, will
  the merged ЦНАП actually cut costs — conditional on the agreement already
  existing.

Expected value to hromada i of attempting cooperation:

```
EV_i = q · [ r·S_i + (1−r)·F_i ] + (1−q)·N_i − c_i
```

- `c_i` — cost of attempting negotiation (staff time, legal review), paid
  regardless of outcome.
- `S_i` — payoff if the project succeeds (ЦНАП savings, grant received).
- `F_i` — payoff if the agreement is signed but the project doesn't deliver
  (sunk implementation cost, application rejected).
- `N_i` — payoff if negotiation itself fails (usually near zero, maybe
  slightly negative — wasted time, minor political cost).

Compare against `EV_i(alone) = r_alone·S_i,alone − c_i,alone` (solo grant
application at a lower success rate, or keeping the ЦНАП unshared).

For multi-party clusters (research-questions.md §3), `c` does not scale
linearly with party count — coordinating N parties costs closer to
`N(N−1)/2` pairwise negotiations before any hub-and-spoke simplification,
which is a candidate structural reason large clusters (e.g. the 22-party
Дністровський каньйон case) are rarer than pairs, independent of match
quality.

### 5.2 Where the parameters come from

- **q** is exactly what the AIM-CC funnel measures (§6 of the prereg):
  reply → call scheduled → call held → next step → signing, split by arm.
  Once the pilot runs, `q` should be re-estimated from real reply/signing
  rates per arm instead of the placeholder priors below.
- **r** is project-type specific: grant success base rates for joint vs
  solo applications (if the donor program publishes them) for grants;
  `edem_total` capacity proxy (already in the corpus, used as an AIM-CC
  moderator) for ЦНАП-type administrative mergers.
- **S** needs real budget data the corpus does not currently have (ЦНАП
  operating cost, grant size) — flagged as a data gap, not filled here.
- **F, N** are hard to observe directly; a reasonable starting default is a
  small negative fraction of `c` (sunk cost + minor reputational cost),
  refined later from practitioner interviews (as with Tkachuk).

### 5.3 Loss aversion

Hromada heads are elected, and failure is visible/personalized while
success is diffuse — the classic asymmetry behind loss aversion. A plain
expected-value ranking likely overstates how much cooperation will actually
happen: officials plausibly weight the downside tail more than its
probability alone would justify. The simulator below reports a
`risk_adjusted` score (`mean EV + loss_aversion × CVaR10`, CVaR10 = mean of
the worst 10% simulated outcomes) alongside raw mean EV specifically to
surface this — a pair can have positive mean EV and still rank low once its
downside tail is heavy.

### 5.4 Simulator

[scripts/analysis/coop_game_sim.py](../scripts/analysis/coop_game_sim.py) —
Monte Carlo over real candidate pairs from `matching-edges.json` (excludes
already-`known` pairs). For each pair, draws `q` from a Beta prior keyed on
`track` (thematic/operational/mixed — proxying the AIM-CC arms), `r` from a
project-type Beta, and `S/F/N/c` from project-type Triangular distributions,
then reports mean EV, P(loss), CVaR10, and the risk-adjusted score.

```
python scripts/analysis/coop_game_sim.py --project cnap --top-n 15
python scripts/analysis/coop_game_sim.py --project water_grant \
    --pair-a "<hromada A>" --pair-b "<hromada B>"
```

**All numeric priors in the script (`TRACK_Q_PRIOR`, `PROJECT_PARAMS`) are
elicited placeholders, not fitted values** — there is no launched AIM-CC
data and no real budget data behind them yet. The script's purpose right
now is to make the *shape* of the decision computable and inspectable (and
to make the loss-aversion point concrete: e.g. the ЦНАП project routinely
shows 50–80% P(loss) even for well-matched pairs at these placeholder
values, while the water-grant project's larger `S` pulls the same pairs to
a positive risk-adjusted score) — not to produce a decision-grade ranking
of which pair to fund. Swap in real AIM-CC funnel rates and real budget
figures before treating output as more than illustrative.

### 5.5 Illustrative run (2026-08-13, seed 0, placeholder priors)

Full output saved at
[internal/coop-game-sim-results.json](coop-game-sim-results.json)
(`python scripts/analysis/coop_game_sim.py --project <cnap|water_grant>
--top-n 10 --seed 0 --samples 20000`, top 10 non-`known` candidates by
existing match `score`). Headline pattern, same candidate pairs both times:

| project | typical q | typical r | mean EV range | P(loss) range | risk-adjusted |
|---|---|---|---|---|---|
| `cnap` | 0.30–0.35 | 0.65 | −17 to +8 (thousand UAH-eq.) | 48–84% | negative for most pairs |
| `water_grant` | 0.30–0.35 | 0.35 | +11 to +79 | 18–56% | positive for most pairs |

Same pairs, same coordination odds (`q`) — the sign of the risk-adjusted
score flips by project type because `S` (grant size) dwarfs `c`
(negotiation cost) while ЦНАП's smaller, more probable `S` does not clear
its own cost + execution-risk bar. This is the numeric basis for the
practical takeaway used in stakeholder framing: a high match `score` alone
does not imply "worth pursuing" — the answer can flip for the same pair
depending on which joint project is being evaluated. Re-run and overwrite
`coop-game-sim-results.json` once real AIM-CC/budget figures replace the
placeholder priors, so this section doesn't go stale silently.

## 6. Other frameworks fitting other parts of the project (for later use)

Logged here so they don't need re-deriving; not scoped as active work.

- **Pairwise-stability network formation (Jackson–Wolinsky).** A
  cross-sectional alternative to the retrospective pooled-MPLE/TERGM
  approach (TERGM itself was archived for lacking longitudinal snapshots —
  [project-strategy-future-backwards.md:413-423](project-strategy-future-backwards.md#L413-L423)).
  Treats an observed tie as one that's individually rational to maintain
  for both sides given `geo_score`/`donor_overlap` as utility inputs — no
  time-series requirement, fits the single-snapshot corpus as-is.
- **Hedonic coalition formation games.** Fits the multi-party cluster
  question in
  [docs/research-questions.md §3](../docs/research-questions.md#3-multi-party-clusters-method-is-currently-pairwise-only)
  (Дністровський каньйон — 22 parties, Nizhyn-5): core-stability for which
  clusters hold together, Shapley value for splitting donor funding fairly
  across a coalition of very different sizes.
- **Signaling games (Spence-style).** Fits explicit-ask language and
  template-collision as capacity signals
  (research-questions.md §6): whether the strategy text is a separating
  signal (informative about real difference between hromadas) or a pooling
  one (everyone copies the same consulting template, signal carries no
  information) is directly the open question about template collisions.
- **Nash bargaining.** Fits the resource-asymmetry hell-risk already named
  in
  [project-strategy-future-backwards.md:126-128](project-strategy-future-backwards.md#L126-L128)
  ("resource asymmetry between a recommended pair is visible to
  everyone") — explains match-quality-high-but-conversion-low pairs as a
  bargaining-power problem downstream of a successful match, not a matching
  failure.
- **Public goods games / commons governance (Ostrom).** Fits shared-resource
  cooperation themes — water/basin (research-questions.md §4), waste
  management, tourism clusters — where the free-rider risk sits on top of
  (not instead of) the assurance problem above.

## 7. Shapley value calculator for real multi-party coalitions

Tries the hedonic-game idea from §6 on a real cluster instead of leaving it
as a one-line future-work note: **register #721 "Дністровський каньйон"**
(22 parties — [docs/external-data-sources.md:263](../docs/external-data-sources.md#L263),
[docs/project-history.md:232](../docs/project-history.md#L232)), pulled
straight from `data/cache/kse/partnerships-hromadas-network.csv`.

### 7.1 What's being estimated and why Monte Carlo here means something different

Same tool (random sampling) as `coop_game_sim.py`, different job. There,
sampling stood in for **economic uncertainty** — q/r/S/F/N/c are genuinely
random. Here `v(S)` (the value a coalition `S` unlocks) is a fixed,
deterministic function once you accept the placeholder formula below — the
problem is purely **combinatorial**: an exact Shapley value needs every
one of `22!` orderings (or all `2^22−1` subsets), which is infeasible.
Instead we sample random orderings and average each member's marginal
contribution; more samples shrink *estimation* error, there's no economic
randomness being modeled in this script.

### 7.2 The placeholder value function

Дністровський каньйон is a real geographic-corridor cluster, not a random
grouping — [docs/mss-cooperation-research.md:185](../docs/mss-cooperation-research.md#L185)
already notes MSS clusters follow corridors, not far-apart pairs. So the
value function uses the corpus's own `geo_score` as a "corridor synergy"
proxy instead of inventing an unrelated number:

```
v(S) = 0                                            if |S| < 2
v(S) = BASE_PER_MEMBER · |S| · (1 + SYNERGY_BONUS · mean_geo_score(S))   otherwise
```

`BASE_PER_MEMBER = 20`, `SYNERGY_BONUS = 1.5` — **placeholders, same status
as `PROJECT_PARAMS` in `coop_game_sim.py`, not fitted to real tourism-grant
or visitor-revenue data.** `mean_geo_score(S)` averages the real `geo_score`
values already computed in `matching-edges.json` over every pair inside
`S`; 3 of the 22 parties aren't in the Goals-ready corpus (no parsed
Goals text), so their pairwise terms fall back to the corpus-wide mean
`geo_score` (≈0.069) rather than a fabricated number.

### 7.3 Calculator

[scripts/analysis/shapley_coalition_sim.py](../scripts/analysis/shapley_coalition_sim.py):

```
python scripts/analysis/shapley_coalition_sim.py --register 721 --samples 6000
```

### 7.4 Illustrative run (2026-08-15, seed 0, placeholder value function)

`v(N) = 703.4` (full 22-party coalition). Efficiency check passed: Shapley
values summed to 703.39 ≈ `v(N)`, as the axiom requires. Top and bottom of
the ranking:

| hromada | Shapley | % of total |
|---|---|---|
| Вікнянська | 41.96 | 6.0% |
| Кадубовецька | 41.65 | 5.9% |
| Юрковецька | 40.98 | 5.8% |
| … | … | … |
| Слобідсько-Кульчієвецька | 12.19 | 1.7% |
| Китайгородська | 12.16 | 1.7% |
| Іване-Пустенська | 12.15 | 1.7% |

The bottom three are exactly the parties missing from the Goals-ready
corpus — they get the conservative corpus-mean synergy fallback rather
than credit for actual corridor adjacency, so their Shapley share (~1.7%
each) is roughly a third of the top members' (~5.5-6%). This is a direct,
mechanical consequence of a real data gap (no parsed Goals text for those
3), not a claim about their real contribution to the corridor — flagged
here so it isn't mistaken for the latter if this ever informs an actual
funding-split conversation.

**Same caveat as §5.4**: this makes the *shape* of a fair-split argument
computable on a real cluster — it is not a decision-grade allocation until
`v(S)` is grounded in real joint-tourism-grant or shared-infrastructure
figures instead of a placeholder formula.
