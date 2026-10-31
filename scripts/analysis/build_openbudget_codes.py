"""Map hromadas (data/releases/hromadas.json) to Open Budget budget codes via the BUDG dictionary.

Input:  data/openbudget/BUDG.json  (fetch_openbudget.py dict BUDG -o data/openbudget/BUDG.json)
Output: data/openbudget/hromada-budget-codes.csv, data/openbudget/codes-10.txt, codes-11.txt

Match = first 10 chars of KATOTTG ("UA" + 8-digit hromada prefix); the dictionary stores
settlement-level KATOTTG, so settlements of one hromada share that prefix. Only rows named
"Бюджет ... територіальної громади" are used. Budget codes changed from 11 digits (until 2022)
to 10 digits (from 2023), so both are kept; a hromada may have several codes (mergers).
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "openbudget"

budg = json.load(open(OUT / "BUDG.json"))
hromadas = json.load(open(ROOT / "data" / "releases" / "hromadas.json"))

codes = {10: defaultdict(set), 11: defaultdict(set)}
for r in budg:
    if r["katottg"] and r["namebudg"].startswith("Бюджет") and "територіальної громади" in r["namebudg"]:
        n = len(r["codebudg"])
        if n in codes:
            codes[n][r["katottg"][:10]].add(r["codebudg"])

with open(OUT / "hromada-budget-codes.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["katottg", "name", "oblast", "codes_10digit_2023plus", "codes_11digit_to2022"])
    for h in hromadas:
        k = h["Katottg"][:10]
        w.writerow([h["Katottg"], h["Name"], h["Oblast"],
                    ";".join(sorted(codes[10][k])), ";".join(sorted(codes[11][k]))])

for n in (10, 11):
    allc = sorted({c for h in hromadas for c in codes[n][h["Katottg"][:10]]})
    (OUT / f"codes-{n}.txt").write_text("\n".join(allc) + "\n")
    print(n, "digit: hromadas with code", sum(bool(codes[n][h["Katottg"][:10]]) for h in hromadas),
          "unique codes", len(allc))
