# References

Theoretical grounding for why this project's core bet — that cooperation between
local governments is a structural/network phenomenon that can be surfaced from
text and topology, not just discovered through personal relationships — is a
reasonable one, and where its limits are likely to sit.

## Ukraine / decentralization context

Empirical notes on the Ukrainian МСС registry, DOBRE survey (partner-search
bottleneck), «light» joint-project procedure, and ЗП 11412 live in
[docs/mss-cooperation-research.md](docs/mss-cooperation-research.md) — use that
file for stakeholder framing; keep this list for the theoretical stack.

1. **OECD — *Rebuilding Ukraine by Reinforcing Regional and Municipal Governance*.**
   Direct policy framing for why municipal-governance capacity (of which
   inter-municipal cooperation is one lever) matters specifically for Ukraine's
   reconstruction, not decentralization in the abstract. Large volume — for this
   project, read surgically: Ch.1 Assessment & recommendations (IMC bullets) and
   the IMC subsection of Ch.6; skip fiscal/amalgamation depth unless doing
   separate policy work.

2. **OECD — *How to Make Inter-Municipal Co-operation Work* (2026).**
   Practitioner-facing OECD guidance on IMC design choices (voluntary vs.
   mandated, single-purpose vs. general-purpose, funding models) — a check against
   which of the collaboration types this project's matching method can plausibly
   detect (thematic/strategic overlap) versus which it can't (administrative/
   back-office arrangements — see the "Methodology notes" section in the
   [README](README.md)). Read this before the large 2022 Ukraine volume; the
   typology and enabling conditions map directly onto our two product tracks
   (below).

2a. **USAID DOBRE — міжмуніципальне співробітництво ТГ: результати дослідження
   (2024).** Survey of 546 hromadas + analysis of 429 post-2020 registry
   contracts. Key product-facing finding: hardest IMC stage is **partner search
   & communication (30%)**, not legal form; finance dominates drafting (31%).
   Presentation PDF on decentralization.ua (attachment/document/1442). Feeds
   legislative concept → bill **№11412**.

2b. **DECIDE — аналіз реєстру договорів МСС (2023).** Why ~61% of deals use
   joint projects (Law art. 11 simplified procedure). 
   https://www.decentralization.ua/news/16570

## How IMC typologies map onto this project's method

Two OECD / network-governance ladders sit behind the split already shipped as
`схожа стратегія` (thematic) vs `зручний сусід` (operational). They are not
competing frameworks — one describes **depth of the arrangement**, the other
**who runs it**.

### Ladder A — depth of cooperation (OECD IMC 2026)

| Form | What it is | Example in our corpus | Which signal finds it |
|------|------------|------------------------|------------------------|
| Handshake / ad hoc | Informal coordination, no contract | Peer learning Дніпро↔Львів (innovation institution) | Soft thematic; not in МСС registry |
| Single-purpose | One shared service or asset | Слобожанська↔Обухівська (shared ЦНАП); planned water network Галич–Бурштин–Маріямпіль | Mostly **geo / neighbourhood** (`зручний сусід`); text only if the strategy names the shared asset |
| Multi-purpose / thematic cluster | Several linked products or a joint development agenda | Tourism: Ніжин–Батурин–Козелець («Місцями козацької сили»); candidate Ужгород↔Мукачево | **Goals-cosine** (`схожа стратегія`); geo optional — can be same corridor, not always next door |
| NAO-like / dedicated body | Separate admin entity for the network | Асоціація «Львівська агломерація»; large multi-party PIN deals (Дністровський каньйон, 22 parties) | Matching finds *candidates*; Provan & Kenis (below) says what governance form should follow |

**Tourism** sits high on this ladder: rare in the registry (~0.6% of titled agreements) but where NLP adds the most — multi-party, sometimes cross-oblast, vision written into Goals. Sell as joint route / DMO / grant, not as “you are neighbours.”

**Water / waste / fire / CNAP** sit low on the ladder: natural single-purpose sharing with **adjacent** hromadas. Strategies rarely describe them; when they do (Дубовецька names the Галич water project), text confirms an operational neighbour, it does not replace geography. Sell as `зручний сусід`, not as strategy twin.

### Ladder B — who governs the network (Provan & Kenis 2008)

| Mode | Fit when | Ukraine-flavoured example |
|------|----------|---------------------------|
| Shared participant | Small N, high trust, high goal consensus | Bilateral ЦНАП or two-hromada utility |
| Lead organization | One capable hub + smaller partners | Oblast-centre or large miska anchoring a corridor |
| Network administrative organization (NAO) | Large N, need network-level competence | Tourism / canyon / ethnos clusters with 5–22 parties |

Contingencies that decide the mode: trust density, network size, goal consensus,
need for network-level skills. Matching does not pick the mode — it only surfaces
who should be in the room.

### Enabling conditions (OECD) → product implications

- **Trust / incremental path** — start with a narrow shared service, expand later;
  or for cold-start vision pairs, start with a joint grant/route before a legal
  multi-purpose body.
- **Data & monitoring** — our open edges + PIN overlay are exactly the “reliable
  data / monitoring” enabling condition OECD lists; keep hypotheses labeled, do
  not present combined `score` as one “strategy match.”
- **Sector fit** — capital-intensive networks (water, waste, transport) and
  cross-boundary development (tourism, spatial planning) are where IMC is
  “natural”; do not oversell generic sector-tag overlap (already useless as a
  matching signal in this corpus).

### One-line method reminder

**Goals text → like-minded partners (tourism / clusters). Geography + existing
PIN → service co-sharers next door (water, ЦНАП, waste). v6 mixes both — strong
combined signal, easy to mis-sell.**

## Institutional and network-governance theory

3. **Elinor Ostrom — *Understanding Institutional Diversity*.**
   The foundational case that polycentric, overlapping local-government
   arrangements are not inefficient duplication but a legitimate institutional
   form in their own right — the theoretical license for treating hromada-to-hromada
   cooperation as worth mapping systematically, rather than as something a single
   optimal administrative boundary would make unnecessary.

4. **Provan & Kenis (2008) — *Modes of Network Governance: Structure, Management,
   and Effectiveness*.**
   A typology (participant-governed, lead-organization, network administrative
   organization) for what a discovered hromada cluster could actually become
   organizationally once a candidate collaboration is confirmed — matching finds
   candidates, this is about what governance form should follow.

5. **Hulst & Van Montfort (eds.) — *Inter-Municipal Cooperation in Europe*.**
   Comparative empirical grounding on how IMC actually functions across European
   systems — a reality check on how much of real-world IMC is thematic/strategic
   (findable via this project's method) versus purely operational cost-sharing
   (which the project's own findings suggest text-similarity is poorly suited to).

## Network structure

6. **Ronald Burt — *Structural Holes: The Social Structure of Competition*.**
   The concept most directly relevant to the project's actual value proposition:
   value sits in bridging positions between otherwise-unconnected clusters, not
   just in dense clusters themselves. Frames why an *undiscovered* candidate pair
   (like Новомосковськ↔Запоріжжя) can matter as much as confirming known ones —
   the interesting cases are the missing edges.

7. **Albert-László Barabási — *Network Science*.**
   General reference for the graph-theoretic vocabulary and structural measures
   (centrality, clustering, community detection) relevant once matched pairs are
   assembled into an actual hromada collaboration graph — not yet built, but the
   natural next layer over the current pairwise-matching output.

## Multi-level governance

8. **Hooghe & Marks — work on Multi-Level Governance** (e.g. *Multi-Level
   Governance and European Integration*; "Unraveling the Central State, but How?
   Types of Multi-Level Governance").
   Places hromada-to-hromada cooperation within the larger vertical stack
   (hromada ↔ oblast ↔ state ↔ donor/international programs) that this project's
   own data already surfaces informally through the `DonorsPrograms` and
   `PartnersMentioned` fields — a reminder that horizontal (Type II) cooperation
   and vertical donor/state relationships are entangled, not separate layers.
