#!/bin/sh
# Re-run the (resumable) fetch until nothing fails; survives VPN drops.
# Usage: fetch_openbudget_loop.sh <codes-file> <years> [classification]
F=data/openbudget/failed.tsv
for i in 1 2 3 4 5 6 7 8 9 10; do
  rm -f "$F"
  python3 -u -W ignore scripts/analysis/fetch_openbudget.py fetch --codes-file "$1" --years "$2" \
    --classification "${3:-FUNCTIONAL}" --workers 2 --delay 2 --retries 5
  [ -s "$F" ] || break
  echo "pass $i had failures, waiting 60s"; sleep 60
done
