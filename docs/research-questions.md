# Candidate new research questions (2026-08-09)

Brainstorm list — not yet scoped or committed. Distinct from the action-item
checklist in [project-history.md § Open threads](project-history.md#open-threads-as-of-2026-08-03):
these are new *questions to investigate*, not agreed next steps. Promote an
item to project-history.md once it has a concrete plan and starts moving.

## 1. Predictive validity (method is currently retrospective-only)

- **Forward-test**: take an earlier snapshot of the МСС registry and check
  whether pairs the model would have matched *then* went on to sign an
  agreement *later*. Does `goals_cosine` / combined `score` have predictive
  power, or only retrospective pattern-matching on already-known pairs?
- Temporal precedence: do pairs with `explicit-ask` language in their
  strategy text sign a МСС *sooner* than pairs without it? Checkable against
  strategy publication dates vs registry registration dates.

## 2. Frozen elections / head-tenure dynamics

- Does **head tenure length** (years without local elections — "sticky
  head") correlate with МСС signing frequency/speed? Turns the hypothesis in
  [mss-cooperation-research.md § frozen elections](mss-cooperation-research.md#frozen-elections-otg)
  into a testable regression.
- "Fragile heads" risk score: can we predict which existing partnerships are
  most exposed to a future change of head — i.e. which relationships most
  need institutionalizing into a formal МСС now, before relying further on
  personal trust?

## 3. Multi-party clusters (method is currently pairwise-only)

- Community detection (Louvain/Leiden) over goals-embeddings + geo instead
  of pairwise ranking — does a graph approach surface clusters like
  Дністровський каньйон (22 parties) or the Nizhyn-5 *before* they actually
  form, not just after?
- Is there a structural signal (shared PIN-graph neighbor + similar text)
  that predicts a bilateral agreement expanding into a multi-party one?

## 4. Water/basin thematic focus (flagged as "next" by Tkachuk)

- Direct test: among registered water-themed МСС, what share of pairs share
  a HydroBASINS lev06 basin — is that a stronger signal than the
  rayon/oblast adjacency already in `geo_score`?
- Can a "basin urgency" variable (shared water body + explicit-ask in text)
  outperform the current generic `complementary` layer?

## 5. Donor synergy as a natural experiment

- Does shared participation in one donor program (DOBRE/GIZ/U-LEAD/…) act
  as an instrument that lowers transaction costs — i.e. do pairs with a
  shared donor sign МСС faster/more often than pairs with equal
  `goals_cosine` but no shared donor? Operationalizes Tkachuk's "AI lowers
  uncertainty, doesn't replace trust" claim.

## 6. Methodology questions on the model itself

- Template collisions are currently just flagged — does using the same
  consulting template correlate with actual governance weakness (e.g. low
  edem/DFRR from KSE), or is it a purely technical artifact with no
  substantive signal?
- How sensitive is the v7.1 document-centroid blend to corpus size — do top
  ranks stay stable as the corpus grows from 77 toward ~150 hromadas, or
  does the list drift?

## 7. Domain extension

- The parked idea in
  [internal/university-cooperation-idea.md](../internal/university-cooperation-idea.md) —
  does the same product class (pair · theme · form + signals) transfer to
  university↔hromada cooperation, and is there an analog of "explicit ask"
  in that text?
- UA–EU twinning × domestic МСС: do hromadas with an active sister-city
  partnership (SKEW/C4C) have a higher rate of domestic МСС on the same
  theme (external cooperation experience lowering the barrier to internal
  cooperation)?

## 8. EU positioning — Ukraine rollout as the validation experiment (2026-08-10)

- Reframe: pitch the matching system as built for EU cooperation instruments
  (Interreg/EGTC/LEADER, or UA–EU twinning), with the Ukraine rollout
  positioned as the pilot/validation experiment rather than the target
  market. This also resolves a stats problem in the
  [AIM-CC field experiment](../internal/aim-cc-field-experiment-prereg.md):
  its pilot sample is self-selected/initiative-taking hromadas — too small
  and non-random to support a "our data creates market value in Ukraine"
  claim, but a fine basis for "mechanism validated on live cases," which is
  what an EU pitch actually needs.
- Existing bridge asset: the [UA–EU twinning layer](ua-eu-twinning.md)
  (176 nodes via SKEW/C4C) already reaches across the border — closer to
  shovel-ready than a new EU-only product built from nothing.
- What has to hold up before the claim survives scrutiny (which parts of the
  method are universal vs Ukraine-specific plumbing, which EU instrument to
  target first, what validation dataset would play the KSE-PIN-registry
  role): [internal/eu-transfer-one-pager.md](../internal/eu-transfer-one-pager.md).
- Follow-on for **#1** (predictive validity): if this direction is pursued,
  the retrospective forward-test should eventually run against whichever EU
  dataset gets picked too, not just the UA registry — same logic ("did the
  score predict what people did anyway") applies there.
