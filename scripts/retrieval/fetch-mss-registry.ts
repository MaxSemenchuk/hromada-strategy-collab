/**
 * Fetch the official МСС (inter-municipal cooperation) agreements registry
 * from data.gov.ua into data/cache/mss/ — local cache for known-pair validation
 * and alternate analyses. Gitignored (under data/cache/).
 *
 * Dataset: https://data.gov.ua/dataset/912c1ea4-38ea-4648-8306-59fc1df8b51b
 * License: CC BY 4.0
 *
 * Usage:
 *   yarn fetch-mss-registry
 *   yarn fetch-mss-registry --force
 *   yarn fetch-mss-registry --dry-run
 */

import { createHash } from "crypto";
import * as fs from "fs";
import * as path from "path";

const ROOT = path.resolve(__dirname, "../..");
const OUT_DIR = path.join(ROOT, "data/cache/mss");
const PACKAGE_ID = "912c1ea4-38ea-4648-8306-59fc1df8b51b";
const CKAN_SHOW = `https://data.gov.ua/api/3/action/package_show?id=${PACKAGE_ID}`;

const UA =
  "hromada-strategy-collab/0.1 (+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)";

interface CkanResource {
  id: string;
  name?: string;
  url?: string;
  format?: string;
  last_modified?: string | null;
  created?: string;
  size?: number | null;
  archiver?: { is_broken?: boolean };
}

interface PackageShowResponse {
  success: boolean;
  result?: {
    title?: string;
    name?: string;
    metadata_modified?: string;
    resources?: CkanResource[];
  };
}

interface Manifest {
  package_id: string;
  package_title: string | null;
  package_url: string;
  resource_id: string;
  resource_name: string | null;
  source_url: string;
  local_path: string;
  canonical_path: string;
  format: string;
  sha256: string;
  bytes: number;
  resource_last_modified: string | null;
  downloaded_at: string;
}

function parseArgs() {
  const args = process.argv.slice(2);
  return {
    force: args.includes("--force"),
    dryRun: args.includes("--dry-run"),
  };
}

function isXlsx(resource: CkanResource): boolean {
  const fmt = (resource.format || "").toUpperCase();
  const name = (resource.name || resource.url || "").toLowerCase();
  return fmt.includes("XLS") || name.endsWith(".xlsx") || name.endsWith(".xls");
}

function prefersDataGovHost(url: string): boolean {
  try {
    return new URL(url).hostname.includes("data.gov.ua");
  } catch {
    return false;
  }
}

function resourceSortKey(r: CkanResource): number {
  const t = r.last_modified || r.created || "";
  return Date.parse(t) || 0;
}

/** Prefer newest non-broken XLSX on data.gov.ua; fall back to any XLSX URL. */
function pickResource(resources: CkanResource[]): CkanResource {
  const xlsx = resources.filter((r) => r.url && isXlsx(r));
  if (!xlsx.length) {
    throw new Error("No XLSX resources found on МСС registry package");
  }

  const healthy = xlsx.filter((r) => r.archiver?.is_broken !== true);
  const pool = healthy.length ? healthy : xlsx;

  const ranked = [...pool].sort((a, b) => {
    const host = Number(prefersDataGovHost(b.url!)) - Number(prefersDataGovHost(a.url!));
    if (host !== 0) return host;
    return resourceSortKey(b) - resourceSortKey(a);
  });

  return ranked[0];
}

function datedFilename(resource: CkanResource): string {
  const stamp =
    (resource.last_modified || resource.created || "")
      .slice(0, 10)
      .replace(/[^0-9-]/g, "") || "unknown-date";
  return `mss_registry_${stamp}.xlsx`;
}

async function download(url: string): Promise<Buffer> {
  const res = await fetch(url, {
    headers: { "User-Agent": UA, Accept: "*/*" },
    redirect: "follow",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} downloading registry: ${body.slice(0, 160)}`);
  }
  return Buffer.from(await res.arrayBuffer());
}

async function main() {
  const { force, dryRun } = parseArgs();
  const canonical = path.join(OUT_DIR, "mss_registry.xlsx");
  const manifestPath = path.join(OUT_DIR, "manifest.json");

  if (fs.existsSync(canonical) && !force && !dryRun) {
    console.log(`Already present: ${path.relative(ROOT, canonical)} (use --force to refresh)`);
    if (fs.existsSync(manifestPath)) {
      console.log(fs.readFileSync(manifestPath, "utf8"));
    }
    return;
  }

  console.log(`CKAN package_show ${PACKAGE_ID}…`);
  const metaRes = await fetch(CKAN_SHOW, { headers: { "User-Agent": UA } });
  if (!metaRes.ok) {
    throw new Error(`CKAN package_show failed: ${metaRes.status}`);
  }
  const meta = (await metaRes.json()) as PackageShowResponse;
  if (!meta.success || !meta.result?.resources?.length) {
    throw new Error("CKAN returned no package resources");
  }

  const resource = pickResource(meta.result.resources);
  const url = resource.url!;
  const dated = path.join(OUT_DIR, datedFilename(resource));

  console.log(`Selected: ${resource.name || resource.id}`);
  console.log(`  ${url}`);
  console.log(`  → ${path.relative(ROOT, dated)}`);
  console.log(`  → ${path.relative(ROOT, canonical)} (canonical)`);

  if (dryRun) {
    console.log("dry-run: not writing files");
    return;
  }

  const buf = await download(url);
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(dated, buf);
  fs.writeFileSync(canonical, buf);

  const manifest: Manifest = {
    package_id: PACKAGE_ID,
    package_title: meta.result.title ?? null,
    package_url: `https://data.gov.ua/dataset/${PACKAGE_ID}`,
    resource_id: resource.id,
    resource_name: resource.name ?? null,
    source_url: url,
    local_path: path.relative(ROOT, dated).split(path.sep).join("/"),
    canonical_path: path.relative(ROOT, canonical).split(path.sep).join("/"),
    format: resource.format || "XLSX",
    sha256: createHash("sha256").update(buf).digest("hex"),
    bytes: buf.length,
    resource_last_modified: resource.last_modified ?? resource.created ?? null,
    downloaded_at: new Date().toISOString(),
  };
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");

  console.log(`ok ${manifest.bytes} bytes sha256=${manifest.sha256.slice(0, 12)}…`);
  console.log(`manifest → ${path.relative(ROOT, manifestPath)}`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
