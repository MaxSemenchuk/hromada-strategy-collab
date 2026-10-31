"""Download local-budget execution data from the Open Budget public API.

API: https://api.openbudget.gov.ua  (swagger group v1.0, endpoint /api/public/localBudgetData)
One request = one budget code x one year x one classification type. Output is CSV (';'-separated,
UTF-8 although the API header claims windows-1251) with cumulative-within-year amounts
(Q2 includes Q1). FUND_TYP: T = total, C = general fund, S = special fund (T = C + S).
Budget codes are 11-digit up to 2022 and 10-digit from 2023 (see build_openbudget_codes.py).
Size: ~1 MB per budget-year, so a full 1463 x 8-year run is ~10+ GB; start with a subset.

The API is reachable only from some networks (a Ukrainian IP / VPN exit may be needed).

Usage:
  python scripts/analysis/fetch_openbudget.py ping
  python scripts/analysis/fetch_openbudget.py dicts                 # list public dictionaries
  python scripts/analysis/fetch_openbudget.py dict <code> [-o f]    # dump one dictionary as JSON
  python scripts/analysis/fetch_openbudget.py fetch --codes 1651500000 --years 2021-2025
  python scripts/analysis/fetch_openbudget.py fetch --codes-file codes.txt --years 2018-2025 \
      --classification PROGRAM FUNCTIONAL

Raw files land in data/openbudget/raw/{code}_{year}_{item}_{classification}_{period}.csv and
are skipped if already present, so interrupted runs resume. Failures are logged to
data/openbudget/failed.tsv.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE = "https://api.openbudget.gov.ua"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "openbudget"
RAW = OUT / "raw"


def get(path, **params):
    r = requests.get(BASE + path, params=params, timeout=120)
    r.raise_for_status()
    return r


def parse_years(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(y) for y in spec.split(",")]


def read_codes(args):
    codes = list(args.codes or [])
    if args.codes_file:
        for line in Path(args.codes_file).read_text().splitlines():
            line = line.split("#")[0].strip().split(",")[0].strip()
            if line and line.lower() != "budgetcode":
                codes.append(line)
    return list(dict.fromkeys(codes))


def cmd_fetch(args):
    RAW.mkdir(parents=True, exist_ok=True)
    codes, years = read_codes(args), parse_years(args.years)
    if not codes:
        sys.exit("no budget codes: pass --codes or --codes-file")
    jobs = [(c, y, k) for c in codes for y in years for k in args.classification]
    print(f"{len(jobs)} requests ({len(codes)} budgets x {len(years)} years x {len(args.classification)} classifications)")
    todo = [(i, j) for i, j in enumerate(jobs, 1)
            if not (RAW / f"{j[0]}_{j[1]}_{args.item}_{j[2]}_{args.period}.csv").exists()]
    print(f"{len(todo)} to download ({len(jobs) - len(todo)} already present), {args.workers} workers")

    def one(item):
        i, (code, year, cls) = item
        path = RAW / f"{code}_{year}_{args.item}_{cls}_{args.period}.csv"
        for attempt in range(1, args.retries + 1):
            try:
                r = get("/api/public/localBudgetData", budgetCode=code, budgetItem=args.item,
                        classificationType=cls, period=args.period, year=year)
                tmp = path.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.rename(path)
                print(f"[{i}/{len(jobs)}] {path.name} {len(r.content)} B", flush=True)
                break
            except requests.RequestException as e:
                if attempt == args.retries:
                    print(f"[{i}/{len(jobs)}] FAILED {code} {year} {cls}: {e}", flush=True)
                    with open(OUT / "failed.tsv", "a") as f:
                        f.write(f"{code}\t{year}\t{cls}\t{e}\n")
                else:
                    time.sleep(args.delay * attempt * 2)
        time.sleep(args.delay)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(one, todo))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping")
    sub.add_parser("dicts")
    d = sub.add_parser("dict")
    d.add_argument("code")
    d.add_argument("-o", "--out")
    f = sub.add_parser("fetch")
    f.add_argument("--codes", nargs="*")
    f.add_argument("--codes-file", help="one budget code per line (or CSV, first column)")
    f.add_argument("--years", default="2018-2025")
    f.add_argument("--item", default="EXPENSES",
                   choices=["EXPENSES", "INCOMES", "FINANCING_DEBTS", "FINANCING_CREDITOR", "CREDITS"])
    f.add_argument("--classification", nargs="+", default=["PROGRAM"],
                   choices=["PROGRAM", "FUNCTIONAL", "ECONOMIC", "CREDIT"])
    f.add_argument("--period", default="QUARTER", choices=["QUARTER", "MONTH"])
    f.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    f.add_argument("--retries", type=int, default=3)
    f.add_argument("--workers", type=int, default=1, help="parallel requests")
    args = p.parse_args()

    if args.cmd == "ping":
        print(get("/api/public/ping").text)
    elif args.cmd == "dicts":
        for x in get("/items").json():
            print(x["code"], "|", x.get("label"), "|", x.get("lastUpdate"))
    elif args.cmd == "dict":
        text = json.dumps(get(f"/items/{args.code}").json(), ensure_ascii=False, indent=1)
        if args.out:
            Path(args.out).write_text(text)
        else:
            print(text[:5000])
    else:
        cmd_fetch(args)


if __name__ == "__main__":
    main()
