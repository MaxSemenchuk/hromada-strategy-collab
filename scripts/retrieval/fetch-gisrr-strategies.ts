/**
 * Fetch local hromada development strategies from ГІС Регіонального розвитку
 * (gisrr.gov.ua) into data/cache/gisrr/ — research cache for corpus growth.
 *
 * Source: https://gisrr.gov.ua/strategy-local
 * License: CC BY 4.0 (site footer)
 * Note: system is in дослідна експлуатація; coverage is incomplete (~200 ТГ,
 * not a full national registry). Catalog + detail payloads are SSR-embedded
 * in window.__pinia (no public list API).
 *
 * Usage:
 *   yarn fetch-gisrr-strategies
 *   yarn fetch-gisrr-strategies --force
 *   yarn fetch-gisrr-strategies --limit 5
 *   yarn fetch-gisrr-strategies --catalog-only
 *   yarn fetch-gisrr-strategies --dry-run
 */

import { createHash } from "crypto";
import * as fs from "fs";
import * as path from "path";

const ROOT = path.resolve(__dirname, "../..");
const OUT_DIR = path.join(ROOT, "data/cache/gisrr");
const DETAILS_DIR = path.join(OUT_DIR, "details");
const CATALOG_PATH = path.join(OUT_DIR, "catalog.json");
const MANIFEST_PATH = path.join(OUT_DIR, "manifest.json");

const LIST_URL = "https://gisrr.gov.ua/strategy-local";
const DETAIL_URL = (rroId: string) =>
  `https://gisrr.gov.ua/strategy-local/${encodeURIComponent(rroId)}`;

const UA =
  "hromada-strategy-collab/0.1 (+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)";

const CONCURRENCY = 4;
const REQUEST_GAP_MS = 150;

interface CatalogEntry {
  rro_id: string;
  atu_id: string;
  atu_name: string;
  reg_num: string;
  oblast: string;
  region_id: string;
  detail_url: string;
}

interface CatalogFile {
  source: string;
  license: string;
  fetched_at: string;
  oblast_count: number;
  document_count: number;
  unique_atu_count: number;
  documents: CatalogEntry[];
}

interface DetailStats {
  goals: number;
  subgoals: number;
  directions: number;
  tasks: number;
  trends: number;
  indicators: number;
  dev_scenarios: number;
  swot_blocks: number;
  activities_plan: number;
  has_strategic_vision: boolean;
  has_general_part: boolean;
  has_swot_description: boolean;
  doc_name: string | null;
  atu_name: string | null;
  acceptance_date: string | null;
  decision_number: string | null;
  period_from: string | null;
  period_to: string | null;
  bytes: number;
  sha256: string;
  fetched_at: string;
  detail_url: string;
}

interface Manifest {
  source: string;
  license: string;
  fetched_at: string;
  catalog_path: string;
  details_dir: string;
  document_count: number;
  unique_atu_count: number;
  details_ok: number;
  details_failed: number;
  details_skipped: number;
  with_goals: number;
  with_subgoals: number;
  with_strategic_vision: number;
  failures: { rro_id: string; error: string }[];
}

function parseArgs() {
  const args = process.argv.slice(2);
  const limitIdx = args.indexOf("--limit");
  const limit =
    limitIdx >= 0 && args[limitIdx + 1]
      ? Math.max(0, parseInt(args[limitIdx + 1], 10) || 0)
      : 0;
  return {
    force: args.includes("--force"),
    dryRun: args.includes("--dry-run"),
    catalogOnly: args.includes("--catalog-only"),
    limit,
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url, {
    headers: {
      "User-Agent": UA,
      Accept: "text/html,application/xhtml+xml",
    },
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  return await res.text();
}

/** Softpro SSR embeds JS object literals with bare `undefined`. */
function extractPinia(html: string): unknown {
  const m = html.match(/window\.__pinia\s*=\s*(\{[\s\S]*?\});\s*window\.ctx\s*=/);
  if (!m) {
    throw new Error("window.__pinia payload not found");
  }
  const jsonish = m[1].replace(/:undefined\b/g, ":null");
  return JSON.parse(jsonish);
}

function listLen(v: unknown): number {
  return Array.isArray(v) ? v.length : 0;
}

function nonEmptyString(v: unknown): boolean {
  return typeof v === "string" && v.replace(/<[^>]+>/g, "").trim().length > 40;
}

function parseCatalog(html: string): CatalogEntry[] {
  const pinia = extractPinia(html) as {
    store?: { data?: { rows?: unknown } };
  };
  const rows = pinia?.store?.data?.rows;
  if (!Array.isArray(rows)) {
    throw new Error("catalog rows missing in pinia store");
  }

  const out: CatalogEntry[] = [];
  for (const reg of rows) {
    if (!reg || typeof reg !== "object") continue;
    const r = reg as Record<string, unknown>;
    const oblast = String(r.atu_name || "");
    const regionId = String(r.region_id || "");
    const list = Array.isArray(r.rr_objects_list) ? r.rr_objects_list : [];
    for (const item of list) {
      if (!item || typeof item !== "object") continue;
      const o = item as Record<string, unknown>;
      const rroId = String(o.rro_id || "");
      if (!rroId) continue;
      out.push({
        rro_id: rroId,
        atu_id: String(o.atu_id || ""),
        atu_name: String(o.atu_name || ""),
        reg_num: String(o.reg_num || ""),
        oblast,
        region_id: regionId,
        detail_url: DETAIL_URL(rroId),
      });
    }
  }
  return out;
}

function summarizeDetail(
  rows: Record<string, unknown>,
  meta: { bytes: number; sha256: string; fetched_at: string; detail_url: string }
): DetailStats {
  const doc =
    rows.document && typeof rows.document === "object"
      ? (rows.document as Record<string, unknown>)
      : {};
  return {
    goals: listLen(rows.goals),
    subgoals: listLen(rows.subgoals),
    directions: listLen(rows.directions),
    tasks: listLen(rows.tasks),
    trends: listLen(rows.trends),
    indicators: listLen(rows.indicators),
    dev_scenarios: listLen(rows.dev_scenarios),
    swot_blocks: listLen(rows.swot),
    activities_plan: listLen(rows.activities_plan),
    has_strategic_vision: nonEmptyString(doc.strategic_vision),
    has_general_part: nonEmptyString(doc.general_part),
    has_swot_description: nonEmptyString(doc.swot_description),
    doc_name: doc.doc_name != null ? String(doc.doc_name) : null,
    atu_name: doc.atu_id_text != null ? String(doc.atu_id_text) : null,
    acceptance_date:
      doc.acceptance_date != null ? String(doc.acceptance_date) : null,
    decision_number:
      doc.decision_number != null ? String(doc.decision_number) : null,
    period_from:
      doc.medium_term_period != null ? String(doc.medium_term_period) : null,
    period_to:
      doc.long_term_period != null ? String(doc.long_term_period) : null,
    ...meta,
  };
}

function detailPath(rroId: string): string {
  return path.join(DETAILS_DIR, `${rroId}.json`);
}

async function fetchDetail(entry: CatalogEntry): Promise<{
  payload: unknown;
  stats: DetailStats;
}> {
  const html = await fetchText(entry.detail_url);
  const pinia = extractPinia(html) as {
    store?: { data?: { rows?: unknown } };
  };
  const rows = pinia?.store?.data?.rows;
  if (!rows || typeof rows !== "object" || Array.isArray(rows)) {
    throw new Error("detail rows missing or unexpected shape");
  }
  const rowsObj = rows as Record<string, unknown>;
  const buf = Buffer.from(JSON.stringify(rowsObj), "utf8");
  const stats = summarizeDetail(rowsObj, {
    bytes: buf.length,
    sha256: createHash("sha256").update(buf).digest("hex"),
    fetched_at: new Date().toISOString(),
    detail_url: entry.detail_url,
  });
  const payload = {
    source: LIST_URL,
    license: "CC BY 4.0",
    rro_id: entry.rro_id,
    catalog: entry,
    fetched_at: stats.fetched_at,
    stats: {
      goals: stats.goals,
      subgoals: stats.subgoals,
      directions: stats.directions,
      tasks: stats.tasks,
      trends: stats.trends,
      indicators: stats.indicators,
      dev_scenarios: stats.dev_scenarios,
      swot_blocks: stats.swot_blocks,
      activities_plan: stats.activities_plan,
      has_strategic_vision: stats.has_strategic_vision,
      has_general_part: stats.has_general_part,
      has_swot_description: stats.has_swot_description,
    },
    rows: rowsObj,
  };
  return { payload, stats };
}

async function mapPool<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T, index: number) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
      if (REQUEST_GAP_MS > 0) await sleep(REQUEST_GAP_MS);
    }
  }
  const n = Math.min(concurrency, Math.max(1, items.length));
  await Promise.all(Array.from({ length: n }, () => worker()));
  return results;
}

async function main() {
  const opts = parseArgs();
  console.log(`GISRR local strategies → ${path.relative(ROOT, OUT_DIR)}`);
  console.log(`  list: ${LIST_URL}`);

  if (opts.dryRun) {
    console.log("dry-run: fetching catalog only (no writes)");
  }

  const listHtml = await fetchText(LIST_URL);
  const documents = parseCatalog(listHtml);
  const uniqueAtu = new Set(documents.map((d) => d.atu_id).filter(Boolean));
  console.log(
    `catalog: ${documents.length} documents · ${uniqueAtu.size} unique atu_id · ${new Set(documents.map((d) => d.oblast)).size} oblasts`
  );

  if (opts.dryRun) {
    for (const d of documents.slice(0, 5)) {
      console.log(`  ${d.atu_name} · ${d.oblast} · ${d.rro_id}`);
    }
    if (documents.length > 5) console.log(`  … +${documents.length - 5} more`);
    return;
  }

  fs.mkdirSync(DETAILS_DIR, { recursive: true });

  const catalog: CatalogFile = {
    source: LIST_URL,
    license: "CC BY 4.0",
    fetched_at: new Date().toISOString(),
    oblast_count: new Set(documents.map((d) => d.oblast)).size,
    document_count: documents.length,
    unique_atu_count: uniqueAtu.size,
    documents,
  };
  fs.writeFileSync(CATALOG_PATH, JSON.stringify(catalog, null, 2), "utf8");
  console.log(`wrote ${path.relative(ROOT, CATALOG_PATH)}`);

  if (opts.catalogOnly) {
    console.log("catalog-only: skipping details");
    return;
  }

  const targets = opts.limit > 0 ? documents.slice(0, opts.limit) : documents;
  if (opts.limit > 0) {
    console.log(`limit: ${targets.length} of ${documents.length}`);
  }

  let ok = 0;
  let skipped = 0;
  let failed = 0;
  const failures: { rro_id: string; error: string }[] = [];
  let done = 0;

  await mapPool(targets, CONCURRENCY, async (entry) => {
    const outPath = detailPath(entry.rro_id);
    if (!opts.force && fs.existsSync(outPath)) {
      skipped++;
      done++;
      if (done % 25 === 0 || done === targets.length) {
        console.log(
          `  progress ${done}/${targets.length} · ok=${ok} fail=${failed} skip=${skipped}`
        );
      }
      return;
    }

    try {
      const { payload } = await fetchDetail(entry);
      fs.writeFileSync(outPath, JSON.stringify(payload, null, 2), "utf8");
      ok++;
    } catch (err) {
      failed++;
      const message = err instanceof Error ? err.message : String(err);
      failures.push({ rro_id: entry.rro_id, error: message });
      console.warn(`  FAIL ${entry.atu_name} (${entry.rro_id}): ${message}`);
    } finally {
      done++;
      if (done % 25 === 0 || done === targets.length) {
        console.log(
          `  progress ${done}/${targets.length} · ok=${ok} fail=${failed} skip=${skipped}`
        );
      }
    }
  });

  let withGoals = 0;
  let withSubgoals = 0;
  let withVision = 0;
  let detailsOnDisk = 0;
  for (const entry of targets) {
    const p = detailPath(entry.rro_id);
    if (!fs.existsSync(p)) continue;
    detailsOnDisk++;
    try {
      const prev = JSON.parse(fs.readFileSync(p, "utf8"));
      const st = prev?.stats;
      if (st?.goals > 0) withGoals++;
      if (st?.subgoals > 0) withSubgoals++;
      if (st?.has_strategic_vision) withVision++;
    } catch {
      /* ignore */
    }
  }

  const manifest: Manifest = {
    source: LIST_URL,
    license: "CC BY 4.0",
    fetched_at: new Date().toISOString(),
    catalog_path: path.relative(ROOT, CATALOG_PATH),
    details_dir: path.relative(ROOT, DETAILS_DIR),
    document_count: documents.length,
    unique_atu_count: uniqueAtu.size,
    details_ok: detailsOnDisk,
    details_failed: failed,
    details_skipped: skipped,
    with_goals: withGoals,
    with_subgoals: withSubgoals,
    with_strategic_vision: withVision,
    failures,
  };
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2), "utf8");

  console.log(`wrote ${path.relative(ROOT, MANIFEST_PATH)}`);
  console.log(
    `done: ${detailsOnDisk}/${targets.length} details on disk · goals=${withGoals} subgoals=${withSubgoals} vision=${withVision} · failed=${failed}`
  );
  if (failed) process.exitCode = 1;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
