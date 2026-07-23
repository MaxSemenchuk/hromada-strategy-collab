#!/usr/bin/env bash
# Persist pre-structured JSON for batch-queue entries with status=downloaded.
# Expects scripts/hromada-output/<slug-from-name>.json already produced in-session.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QUEUE="$ROOT/scripts/retrieval/batch-queue.json"

if [[ ! -f "$QUEUE" ]]; then
  echo "Missing $QUEUE"
  exit 1
fi

python3 - <<'PY' "$QUEUE" "$ROOT"
import json, subprocess, sys, re
from pathlib import Path
queue_path, root = sys.argv[1], sys.argv[2]
raw = json.load(open(queue_path, encoding="utf-8"))
queue = raw["queue"] if isinstance(raw, dict) and "queue" in raw else raw
if not isinstance(queue, list):
    print("batch-queue.json must be a JSON array or {\"queue\": [...]}")
    sys.exit(1)

out_dir = Path(root) / "scripts" / "hromada-output"

for item in queue:
    if item.get("status") != "downloaded":
        continue
    name = item["name"]
    slug = re.sub(r"[^\w\u0400-\u04FF]+", "-", name, flags=re.UNICODE).strip("-")
    json_path = out_dir / f"{slug}.json"
    if not json_path.exists():
        # try looser match
        matches = list(out_dir.glob("*.json"))
        hit = next((p for p in matches if name.split()[0] in p.name), None)
        if not hit:
            print(f"Skip {name}: missing {json_path.name} (structure in-session first)")
            continue
        json_path = hit
    print(f"Writing {name} from {json_path.name}...")
    cmd = ["yarn", "--ignore-engines", "structure-hromada", "--name", name, "--json", str(json_path), "--write"]
    if item.get("nocodb_id"):
        cmd += ["--update", str(item["nocodb_id"])]
    subprocess.check_call(cmd, cwd=root)
    item["status"] = "structured"
    print("  -> structured")

out = {"_comment": raw.get("_comment", ""), "queue": queue} if isinstance(raw, dict) else queue
json.dump(out, open(queue_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("Done.")
PY
