#!/usr/bin/env bash
# Process batch-queue.json entries with status=downloaded through structure-hromada.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QUEUE="$ROOT/scripts/retrieval/batch-queue.json"

if [[ ! -f "$QUEUE" ]]; then
  echo "Missing $QUEUE"
  exit 1
fi

python3 - <<'PY' "$QUEUE" "$ROOT"
import json, subprocess, sys
queue_path, root = sys.argv[1], sys.argv[2]
raw = json.load(open(queue_path, encoding="utf-8"))
queue = raw["queue"] if isinstance(raw, dict) and "queue" in raw else raw
if not isinstance(queue, list):
    print("batch-queue.json must be a JSON array or {\"queue\": [...]}")
    sys.exit(1)

for item in queue:
    if item.get("status") != "downloaded":
        continue
    name = item["name"]
    raw_path = item.get("raw_text_path")
    if not raw_path:
        print(f"Skip {name}: no raw_text_path")
        continue
    path = raw_path if raw_path.startswith("/") else f"{root}/{raw_path}"
    print(f"Structuring {name}...")
    subprocess.check_call(
        ["yarn", "--ignore-engines", "structure-hromada", "--name", name, "--input", path, "--write"],
        cwd=root,
    )
    item["status"] = "structured"
    print("  -> structured")

out = {"_comment": raw.get("_comment", ""), "queue": queue} if isinstance(raw, dict) else queue
json.dump(out, open(queue_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("Done.")
PY
