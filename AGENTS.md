# AGENTS.md

## Cursor Cloud specific instructions

This repo is a **CLI-driven research pipeline** (no web app, no long-running server, no
dev/build/lint/test scripts). See `README.md` for the product overview and the canonical
command list; only non-obvious environment caveats are documented here.

### Services / components
- **TypeScript CLI scripts** (`scripts/*.ts`, run via `tsx`) — the core pipeline:
  `yarn setup-hromadas`, `yarn structure-hromada`, `yarn import-hromadas` (commands in `README.md`).
- **Python analysis scripts** (`scripts/analysis/*.py`) — OPTIONAL, offline corpus matching.

### Node / yarn gotchas
- The active `node` is `/exec-daemon/node` (v22.x) and cannot be robustly overridden
  (it precedes nvm in `PATH`). `package.json` declares `engines.node = "20.x"`, so yarn's
  engine check fails. A committed `.yarnrc` (`--ignore-engines true`) disables that check
  for all yarn commands; the scripts run fine on node 22 via `tsx`. The update script
  installs deps with `yarn install --ignore-engines`.
- There is **no lint/test/build script**. `yarn tsc --noEmit` reports **pre-existing**
  strict-type errors (`res.json()` typed as `unknown`); this is not wired into any script
  and does not affect runtime, because `tsx` executes TypeScript without type-checking.

### Credentials (required for the core TS pipeline)
- `setup-hromadas` / `import-hromadas` need `NOCODB_TOKEN` + `NOCODB_BASE_ID`; `structure-hromada`
  needs `GEMINI_API_KEY`. Without these the scripts exit early with a clear "Missing ..." message
  (still proves the runtime works). `NOCODB_TOKEN` / `NOCODB_BASE_ID` are provided via the Secrets
  panel (injected as env vars on VM startup).
- **Non-obvious:** `NOCODB_URL` is NOT an injected secret, and `setup-hromadas` defaults to
  `http://localhost:8080`. Create a local `.env` (gitignored) with the shared instance URL from
  `.env.example` (`NOCODB_URL=https://nocodb-production-9ea4.up.railway.app`). `dotenv` does not
  override already-set env vars, so the injected `NOCODB_TOKEN` / `NOCODB_BASE_ID` still win.
- The NocoDB base is **shared production** (same base as `w3i-network`). `setup-hromadas` is
  idempotent/read-only-safe (skips existing tables/columns). Avoid `import-hromadas` and
  `structure-hromada --write` unless you intend to mutate real rows.

### Python analysis (optional, runs offline — no secrets needed)
- Deps are in `requirements.txt`. Set up once: `python3 -m venv .venv && . .venv/bin/activate
  && pip install -r requirements.txt` (`sentence-transformers` pulls a large `torch`; the
  embedding scripts also download `intfloat/multilingual-e5-small` from HuggingFace on first run).
  Legacy research scripts under `scripts/analysis/` may additionally need `scipy`, `networkx`, and
  `openpyxl`.
- **Canonical commands** (self-contained — they resolve their own paths, no scratch dir needed):
  `npm run match` (v6 scoring → `data/releases/matching-edges.json`) and `npm run test-known-pairs`
  (regression check that the known МСС pairs rank well). Use these as the hello-world.
- **Legacy scripts** (e.g. `matching23.py`, `embed_matching_v5.py`) read/write hard-coded,
  CWD-relative filenames and expect their input snapshots in the current directory. Those snapshots
  now live in `data/research-log/` (moved from `data/snapshots/`). Run them from a scratch dir with
  inputs symlinked in so outputs don't clobber tracked files, e.g.:
  `mkdir -p /tmp/run && cd /tmp/run && ln -sf /workspace/data/research-log/hromadas_full23.json .
  && ln -sf /workspace/data/research-log/hromada_sectors23.jsonl . && python /workspace/scripts/analysis/matching23.py`
