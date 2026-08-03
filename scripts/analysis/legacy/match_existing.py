import json
import re
import unicodedata

MERGED_PATH = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/4ab5edac-96bb-4235-956a-4039efe2f822/scratchpad/merged_hromadas.json"
EXISTING_PATH = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/4ab5edac-96bb-4235-956a-4039efe2f822/scratchpad/existing_hromadas.json"
UPDATES_OUT = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/4ab5edac-96bb-4235-956a-4039efe2f822/scratchpad/hromada_updates.json"
INSERTS_OUT = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/4ab5edac-96bb-4235-956a-4039efe2f822/scratchpad/hromada_inserts.json"


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s).strip().lower()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*область\s*$", "", s).strip()
    return s


def existing_name_adj(name):
    n = norm(name)
    n = re.sub(r"\s*територіальна\s*громада\s*$", "", n)
    n = re.sub(r"\s*громада\s*$", "", n)
    n = re.sub(r"\s*(міська|селищна|сільська)\s*$", "", n)
    return n.strip()


merged = json.load(open(MERGED_PATH, encoding="utf-8"))["merged"]
existing = json.load(open(EXISTING_PATH, encoding="utf-8"))["list"]

existing_index = {}
for r in existing:
    key = (norm(r["Oblast"]), existing_name_adj(r["Name"]))
    existing_index[key] = r

updates = []
inserts = []
matched_existing_ids = set()

for m in merged:
    key = (norm(m["oblast"]), norm(m["name_adj"]))
    ex = existing_index.get(key)
    if ex:
        matched_existing_ids.add(ex["Id"])
        patch = {"Id": ex["Id"]}
        if m.get("katottg"):
            patch["KATOTTG"] = m["katottg"]
        if m.get("population"):
            patch["Population"] = m["population"]
        if len(patch) > 1:
            updates.append(patch)
    else:
        full_name = f"{m['full_name_decen']}"
        # normalize display name to include type word, matching existing convention: "{Adj} {type} територіальна громада"
        type_word = m.get("type") or ""
        name_adj_cap = m["full_name_decen"].split(" територіальна")[0]
        display_name = f"{name_adj_cap} {type_word} територіальна громада".replace("  ", " ").strip()
        inserts.append({
            "Name": display_name,
            "Oblast": m["oblast"],
            "Rayon": (m["rayon"] + " район") if m["rayon"] else None,
            "Type": type_word or None,
            "KATOTTG": m.get("katottg"),
            "Population": m.get("population"),
        })

print(f"Matched existing rows to update: {len(updates)} (of {len(existing)} existing)")
print(f"New metadata-only rows to insert: {len(inserts)}")
unmatched_existing = [r for r in existing if r["Id"] not in matched_existing_ids]
print(f"Existing rows with NO match in the 1469 set (investigate): {len(unmatched_existing)}")
for r in unmatched_existing:
    print("  ", r["Name"], "|", r["Oblast"])

json.dump(updates, open(UPDATES_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(inserts, open(INSERTS_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("Wrote", UPDATES_OUT, "and", INSERTS_OUT)
