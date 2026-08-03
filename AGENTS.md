# AGENTS.md

## Cursor Cloud specific instructions

This repo is a **CLI-driven research pipeline** (no web app, no long-running server, no
dev/build/lint/test scripts). See `README.md` for the product overview and the canonical
command list; only non-obvious environment caveats are documented here.

### Services / components
- **TypeScript CLI scripts** (`scripts/*.ts`, run via `tsx`) — corpus write path:
  `yarn structure-hromada … --write-release`, optional `yarn export-hromadas` from a
  research-log snapshot (commands in `README.md`).
- **Python analysis scripts** (`scripts/analysis/*.py`) — offline corpus matching;
  canon is `yarn match` → `match.py` v7.1.

### Node / yarn gotchas
- The active `node` is `/exec-daemon/node` (v22.x) and cannot be robustly overridden
  (it precedes nvm in `PATH`). `package.json` declares `engines.node = "20.x"`, so yarn's
  engine check fails. A committed `.yarnrc` (`--ignore-engines true`) disables that check
  for all yarn commands; the scripts run fine on node 22 via `tsx`. The update script
  installs deps with `yarn install --ignore-engines`.
- There is **no lint/test/build script**. `yarn tsc --noEmit` may report strict-type
  noise; this is not wired into any script and does not affect runtime, because `tsx`
  executes TypeScript without type-checking.

### Credentials
- **No remote DB.** Canonical data is `data/releases/`. Do not call archived NocoDB
  scripts under `scripts/legacy/nocodb/` unless intentionally restoring CRM sync.
- `structure-hromada --write` / `--update` are removed (exit with a pointer to
  `--write-release`).

### Python analysis (optional, runs offline — no secrets needed)
- Deps are in `requirements.txt`. Set up once: `python3 -m venv .venv && . .venv/bin/activate
  && pip install -r requirements.txt` (`sentence-transformers` pulls a large `torch`; the
  embedding scripts also download `intfloat/multilingual-e5-small` from HuggingFace on first run).
  Legacy research scripts under `scripts/analysis/legacy/` may additionally need `scipy`,
  `networkx`, and `openpyxl`.
- **Canonical commands** (self-contained — they resolve their own paths, no scratch dir needed):
  `yarn match` (v7.1 scoring → `data/releases/matching-edges.json`) and `yarn test-known-pairs`
  (regression check that the known МСС pairs rank well). Use these as the hello-world.
- **Legacy scripts** live in `scripts/analysis/legacy/` (e.g. `matching23.py`,
  `embed_matching_v5.py`). They read/write hard-coded, CWD-relative filenames and expect
  input snapshots in the current directory. Those snapshots live in `data/research-log/`.
  Run them from a scratch dir with inputs symlinked in so outputs don't clobber tracked
  files, e.g.:
  `mkdir -p /tmp/run && cd /tmp/run && ln -sf /workspace/data/research-log/hromadas_full23.json .
  && ln -sf /workspace/data/research-log/hromada_sectors23.jsonl . && python /workspace/scripts/analysis/legacy/matching23.py`
