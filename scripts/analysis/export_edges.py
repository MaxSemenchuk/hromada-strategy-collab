#!/usr/bin/env python3
"""Write matching-edges manifest alongside the edges JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGES = ROOT / "data" / "releases" / "matching-edges.json"
MANIFEST = ROOT / "data" / "releases" / "matching-edges.manifest.json"


def main() -> None:
    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    known = sum(1 for e in edges if e.get("known"))
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pairCount": len(edges),
        "knownValidationPairs": known,
        "method": "v6: 60% goals_cosine + 25% KSE geo + 15% KSE mss_network",
        "model": "intfloat/multilingual-e5-small",
        "license": "CC BY 4.0 — see DATA-LICENSE.md",
        "warning": "Unverified hypotheses unless known=true",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
