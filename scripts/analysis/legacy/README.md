# Legacy matching passes (do not run)

Archived one-off scripts from Pass 1–5 / early embedding experiments.
Provenance for [docs/project-history.md](../../../docs/project-history.md);
inputs live under `data/research-log/`.

**Canonical matcher:** [`../match.py`](../match.py) (v7.1) via `yarn match`,
then `yarn export-matching-edges`.

| Files | Era |
|-------|-----|
| `matching.py`, `matching13.py`, `matching23*.py`, `matching30.py` | TF-IDF / early cosine passes |
| `embed_matching.py` … `embed_matching_v5.py` | embedding iterations before v6/v7 |
| `final_matching.py`, `clusters30.py`, `goal_overlap.py` | scratch / cluster experiments |
| `match_existing.py`, `build_hromadas.py`, `insert_nizhyn.py` | hard-coded scratchpad / NocoDB paths |

Do not wire these into `package.json`. To replay historically, use a scratch dir
with symlinks into `data/research-log/` (see root `AGENTS.md`).
