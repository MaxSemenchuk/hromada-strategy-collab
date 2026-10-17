"""Flatten the main release layers to UTF-8 CSV under data/releases/csv/.

JSON stays canonical; CSVs are a convenience for spreadsheet / R / pandas users.
Every file carries `katottg` (or `Katottg`) as the join key. List fields are
joined with "; ". Layers are not merged here — join on the key yourself.

Usage: yarn export-csv
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = ROOT / "data" / "releases"
OUT = REL / "csv"


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return v


def write(name, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            w.writerow([cell(r.get(k)) for k in fields])
    print(f"{name}: {len(rows)} rows, {len(fields)} cols")


def load(name):
    return json.load(open(REL / name, encoding="utf-8"))


def main():
    OUT.mkdir(exist_ok=True)

    write("hromadas.csv", load("hromadas.json"))

    write("edem-barometer.csv", load("edem-barometer.json")["hromadas"])

    dream = load("dream-priorities.json")["hromadas"]
    keep = ["katottg", "name", "project_count", "top_sectors", "sector_counts",
            "purpose_counts", "type_counts"]
    write("dream-priorities.csv", dream, keep)

    # one row per hromada–partner pair
    edges = []
    for h in load("twinning-partners.json")["hromadas"]:
        for p in h.get("partners", []):
            edges.append({"katottg": h["katottg"], "name": h["name"], "oblast": h["oblast"], **p})
    fields = ["katottg", "name", "oblast"] + sorted({k for e in edges for k in e} - {"katottg", "name", "oblast"})
    write("twinning-partners.csv", edges, fields)

    edges = []
    for h in load("intl-agreements.json")["hromadas"]:
        for a in h.get("agreements", []):
            edges.append({"katottg": h["katottg"], "name": h["name"], "oblast": h["oblast"], **a})
    fields = ["katottg", "name", "oblast"] + sorted({k for e in edges for k in e} - {"katottg", "name", "oblast"})
    write("intl-agreements.csv", edges, fields)


if __name__ == "__main__":
    main()
