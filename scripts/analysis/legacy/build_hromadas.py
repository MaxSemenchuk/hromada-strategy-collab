import json
import re
import glob
import os
import html as html_module
import openpyxl
import unicodedata

XLSX_PATH = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/b802f80e-1037-46c9-af86-289b7e5a371d/scratchpad/katottg.xlsx"
AREAS_DIR = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/4ab5edac-96bb-4235-956a-4039efe2f822/scratchpad/hromada_areas"
OUT_PATH = "/private/tmp/claude-501/-Users-maxs-Documents-w3i-network/4ab5edac-96bb-4235-956a-4039efe2f822/scratchpad/merged_hromadas.json"

TYPE_MAP = {"M": "міська", "T": "селищна", "C": "сільська"}


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s).strip().lower()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*область\s*$", "", s).strip()
    return s


def strip_suffix(name):
    # remove trailing "територіальна громада" / "громада" / oblast-region words
    n = norm(name)
    n = re.sub(r"\s*територіальна громада\s*$", "", n)
    n = re.sub(r"\s*(міська|селищна|сільська)?\s*громада\s*$", "", n)
    return n.strip()


# ---------- 1. Parse KATOTTG xlsx ----------
wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
ws = wb.active

oblast_name_by_code = {}
rayon_name_by_code = {}
rayon_oblast_by_code = {}
hromada_rows = []  # dict: oblast_code, rayon_code, hromada_code, name
child_categories = {}  # hromada_code -> set of category codes among its children

all_rows = list(ws.iter_rows(min_row=3, values_only=True))
for row in all_rows:
    lvl1, lvl2, lvl3, lvl4, lvl5, cat, name = row[:7]
    if name is None:
        continue
    if cat == "O":
        oblast_name_by_code[lvl1] = name.strip()
    elif cat == "P":
        rayon_name_by_code[lvl2] = name.strip()
        rayon_oblast_by_code[lvl2] = lvl1
    elif cat == "H":
        hromada_rows.append({"oblast_code": lvl1, "rayon_code": lvl2, "hromada_code": lvl3, "name": name.strip()})
    elif lvl3 is not None and cat in ("M", "T", "C", "X"):
        # settlement under a hromada
        child_categories.setdefault(lvl3, set()).add(cat)

def derive_type(hromada_code):
    cats = child_categories.get(hromada_code, set())
    if "M" in cats:
        return "міська"
    if "T" in cats:
        return "селищна"
    return "сільська"

katottg_entries = []
for h in hromada_rows:
    oblast_name = oblast_name_by_code.get(h["oblast_code"], "")
    if oblast_name == "Автономна Республіка Крим":
        continue  # excluded, occupied since 2014, not part of the 2020 hromada reform
    rayon_name = rayon_name_by_code.get(h["rayon_code"], "")
    katottg_entries.append({
        "oblast": oblast_name,
        "rayon": rayon_name,
        "name_adj": h["name"].strip(),
        "katottg": h["hromada_code"],
        "type": derive_type(h["hromada_code"]),
    })

print(f"KATOTTG hromadas (excl. Crimea): {len(katottg_entries)}")

# ---------- 2. Parse decentralization.gov.ua oblast pages ----------
decen_entries = []
for path in sorted(glob.glob(os.path.join(AREAS_DIR, "*.html"))):
    html = open(path, encoding="utf-8").read()
    blocks = re.split(r'(?=<a class="main-text-style tooltip-show" title="Назва громади")', html)
    for b in blocks[1:]:
        m_name = re.search(r'title="Назва громади" href="(/newgromada/\d+)">([^<]+)</a>', b)
        if not m_name:
            continue
        href, full_name = m_name.groups()
        decen_id = href.split("/")[-1]

        def field(label):
            m = re.search(
                r"title='" + re.escape(label) + r"'>\s*([^<\n][^<]*?)\s*</div>", b
            )
            return m.group(1).strip() if m else None

        population = field("К-ть населення")
        area = field("Площа територіальної громади, кв.км")
        settlements = field("Кількість населених пунктів")
        year = field("Створена")
        htype = field("Тип громади")
        rayon = field("Район")

        decen_entries.append({
            "decen_id": decen_id,
            "full_name": full_name.strip(),
            "name_adj": strip_suffix(full_name),
            "population": int(population) if population and population.isdigit() else None,
            "area": float(area) if area else None,
            "settlements": int(settlements) if settlements and settlements.isdigit() else None,
            "year_created": int(year) if year and year.isdigit() else None,
            "type": htype,
            "rayon": rayon.replace(" район", "").strip() if rayon else None,
        })

print(f"Decentralization.gov.ua hromadas: {len(decen_entries)}")

# ---------- 3. Merge ----------
# Index katottg entries by (norm(oblast), norm(rayon), norm(name_adj))
katottg_index = {}
for e in katottg_entries:
    key = (norm(e["oblast"]), norm(e["rayon"]), norm(e["name_adj"]))
    katottg_index[key] = e

# Also a looser index by (norm(oblast), norm(name_adj)) in case rayon naming differs slightly
katottg_loose_index = {}
for e in katottg_entries:
    key = (norm(e["oblast"]), norm(e["name_adj"]))
    katottg_loose_index.setdefault(key, []).append(e)

merged = []
unmatched_decen = []
used_katottg_keys = set()

for d in decen_entries:
    oblast_guess = None  # decentralization page doesn't repeat oblast name per row; fill from filename mapping below
    merged.append(d)

# We need oblast name per decen entry -- derive from which file it came from.
# Re-parse with oblast context.
merged = []
for path in sorted(glob.glob(os.path.join(AREAS_DIR, "*.html"))):
    html = open(path, encoding="utf-8").read()
    m_ob = re.search(r"<title>\s*([^<\n]+?)\s*-\s*\nГромади", html)
    oblast_name = m_ob.group(1).strip() if m_ob else None
    blocks = re.split(r'(?=<a class="main-text-style tooltip-show" title="Назва громади")', html)
    for b in blocks[1:]:
        m_name = re.search(r'title="Назва громади" href="(/newgromada/\d+)">([^<]+)</a>', b)
        if not m_name:
            continue
        href, full_name = m_name.groups()
        full_name = html_module.unescape(full_name)
        decen_id = href.split("/")[-1]

        def field(label, text=b):
            m = re.search(r"title='" + re.escape(label) + r"'>\s*([^<\n][^<]*?)\s*</div>", text)
            return m.group(1).strip() if m else None

        population = field("К-ть населення")
        area = field("Площа територіальної громади, кв.км")
        settlements = field("Кількість населених пунктів")
        year = field("Створена")
        htype = field("Тип громади")
        rayon = field("Район")
        rayon_clean = rayon.replace(" район", "").strip() if rayon else None

        name_adj = strip_suffix(full_name)
        key = (norm(oblast_name), norm(rayon_clean), norm(name_adj))
        k = katottg_index.get(key)
        match_quality = "exact"
        if not k:
            loose = katottg_loose_index.get((norm(oblast_name), norm(name_adj)))
            if loose:
                k = loose[0]
                match_quality = "loose(no-rayon-check)"
            else:
                match_quality = "unmatched"

        merged.append({
            "name_adj": name_adj,
            "full_name_decen": full_name.strip(),
            "oblast": oblast_name,
            "rayon": rayon_clean,
            "type": htype or (k["type"] if k else None),
            "katottg": k["katottg"] if k else None,
            "population": int(population) if population and population.isdigit() else None,
            "area": float(area) if area else None,
            "settlements": int(settlements) if settlements and settlements.isdigit() else None,
            "year_created": int(year) if year and year.isdigit() else None,
            "decen_id": decen_id,
            "match_quality": match_quality,
        })
        if k:
            used_katottg_keys.add((norm(k["oblast"]), norm(k["rayon"]), norm(k["name_adj"])))

print(f"Merged rows: {len(merged)}")
mq = {}
for m in merged:
    mq[m["match_quality"]] = mq.get(m["match_quality"], 0) + 1
print("Match quality breakdown:", mq)

# katottg entries never matched to a decen row (should be near-zero if good)
unmatched_katottg = [e for e in katottg_entries if (norm(e["oblast"]), norm(e["rayon"]), norm(e["name_adj"])) not in used_katottg_keys]
print(f"KATOTTG entries with no decen match: {len(unmatched_katottg)}")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "merged": merged,
        "unmatched_katottg": unmatched_katottg,
    }, f, ensure_ascii=False, indent=2)

print(f"Wrote {OUT_PATH}")
