/**
 * Download strategy source files (PDF/DOC/HTML) from batch-queue.json into
 * scripts/retrieval/raw/ — local cache for re-extraction and alternate analyses.
 * Files are gitignored; only URLs + paths live in the queue.
 *
 * Usage:
 *   yarn download-raw                  # status=pending with strategy_url
 *   yarn download-raw --all            # every queue row with strategy_url
 *   yarn download-raw --force          # re-download even if file exists
 *   yarn download-raw --dry-run
 */

import { createHash } from "crypto";
import * as fs from "fs";
import * as path from "path";

const ROOT = path.resolve(__dirname, "../..");
const QUEUE_PATH = path.join(ROOT, "scripts/retrieval/batch-queue.json");
const RAW_DIR = path.join(ROOT, "scripts/retrieval/raw");
const MANIFEST_PATH = path.join(RAW_DIR, "manifest.json");

const UA =
  "hromada-strategy-collab/0.1 (+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)";

interface QueueItem {
  name: string;
  katottg?: string;
  status: string;
  strategy_url?: string;
  raw_text_path?: string;
  raw_source_path?: string;
  notes?: string;
}

interface QueueFile {
  _comment?: string;
  queue: QueueItem[];
}

interface ManifestEntry {
  name: string;
  url: string;
  path: string;
  sha256: string;
  bytes: number;
  content_type: string | null;
  downloaded_at: string;
}

function parseArgs() {
  const args = process.argv.slice(2);
  return {
    all: args.includes("--all"),
    force: args.includes("--force"),
    dryRun: args.includes("--dry-run"),
  };
}

function extFromUrl(url: string): string {
  try {
    const pathname = new URL(url).pathname;
    const base = path.basename(decodeURIComponent(pathname));
    const ext = path.extname(base).toLowerCase();
    if (ext && ext.length <= 8) return ext;
  } catch {
    /* ignore */
  }
  return ".bin";
}

function stemFromItem(item: QueueItem): string {
  if (item.raw_source_path) {
    return path.basename(item.raw_source_path, path.extname(item.raw_source_path));
  }
  if (item.raw_text_path) {
    const base = path.basename(item.raw_text_path);
    return base
      .replace(/\.(groq|extracted)\.txt$/i, "")
      .replace(/\.(txt|md|html)$/i, "");
  }
  return item.name
    .toLowerCase()
    .replace(/міська|селищна|сільська|територіальна|громада/gi, "")
    .replace(/[^a-zа-яіїєґ0-9]+/gi, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48) || "strategy";
}

function resolveSourcePath(item: QueueItem, url: string): string {
  if (item.raw_source_path) {
    return item.raw_source_path.startsWith("/")
      ? item.raw_source_path
      : path.join(ROOT, item.raw_source_path);
  }
  const rel = path.join("scripts/retrieval/raw", `${stemFromItem(item)}${extFromUrl(url)}`);
  return path.join(ROOT, rel);
}

function toRepoRel(abs: string): string {
  return path.relative(ROOT, abs).split(path.sep).join("/");
}

function loadManifest(): Record<string, ManifestEntry> {
  if (!fs.existsSync(MANIFEST_PATH)) return {};
  try {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8")) as Record<string, ManifestEntry>;
  } catch {
    return {};
  }
}

function saveManifest(manifest: Record<string, ManifestEntry>) {
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2) + "\n", "utf8");
}

async function download(url: string, dest: string): Promise<{ bytes: number; contentType: string | null; sha256: string }> {
  const res = await fetch(url, {
    headers: { "User-Agent": UA, Accept: "*/*" },
    redirect: "follow",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${body.slice(0, 120)}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, buf);
  return {
    bytes: buf.length,
    contentType: res.headers.get("content-type"),
    sha256: createHash("sha256").update(buf).digest("hex"),
  };
}

function shouldProcess(item: QueueItem, all: boolean): boolean {
  if (!item.strategy_url?.trim()) return false;
  if (all) return true;
  return item.status === "pending";
}

async function main() {
  const { all, force, dryRun } = parseArgs();
  if (!fs.existsSync(QUEUE_PATH)) {
    throw new Error(`Missing ${QUEUE_PATH}`);
  }

  const raw = JSON.parse(fs.readFileSync(QUEUE_PATH, "utf8")) as QueueFile | QueueItem[];
  const queue: QueueItem[] = Array.isArray(raw) ? raw : raw.queue;
  if (!Array.isArray(queue)) {
    throw new Error("batch-queue.json must be a JSON array or {\"queue\": [...]}");
  }

  fs.mkdirSync(RAW_DIR, { recursive: true });
  const manifest = loadManifest();

  let ok = 0;
  let skipped = 0;
  let failed = 0;

  for (const item of queue) {
    if (!shouldProcess(item, all)) continue;
    const url = item.strategy_url!.trim();
    const dest = resolveSourcePath(item, url);
    const rel = toRepoRel(dest);

    if (fs.existsSync(dest) && !force) {
      item.raw_source_path = rel;
      if (item.status === "pending") item.status = "downloaded";
      if (!dryRun && !manifest[rel]) {
        const buf = fs.readFileSync(dest);
        manifest[rel] = {
          name: item.name,
          url,
          path: rel,
          sha256: createHash("sha256").update(buf).digest("hex"),
          bytes: buf.length,
          content_type: null,
          downloaded_at: fs.statSync(dest).mtime.toISOString(),
        };
      }
      console.log(`skip (exists): ${item.name} → ${rel}`);
      skipped++;
      continue;
    }

    console.log(`${dryRun ? "dry-run" : "download"}: ${item.name}`);
    console.log(`  ${url}`);
    console.log(`  → ${rel}`);

    if (dryRun) {
      ok++;
      continue;
    }

    try {
      const meta = await download(url, dest);
      item.raw_source_path = rel;
      if (item.status === "pending" || item.status === "failed") {
        item.status = "downloaded";
      }
      manifest[rel] = {
        name: item.name,
        url,
        path: rel,
        sha256: meta.sha256,
        bytes: meta.bytes,
        content_type: meta.contentType,
        downloaded_at: new Date().toISOString(),
      };
      console.log(`  ok ${meta.bytes} bytes sha256=${meta.sha256.slice(0, 12)}…`);
      ok++;
    } catch (err) {
      item.status = "failed";
      const msg = err instanceof Error ? err.message : String(err);
      item.notes = [item.notes, `download failed: ${msg}`].filter(Boolean).join("; ");
      console.error(`  FAIL: ${msg}`);
      failed++;
    }
  }

  if (!dryRun) {
    const out: QueueFile = Array.isArray(raw)
      ? { queue }
      : { _comment: raw._comment, queue };
    fs.writeFileSync(QUEUE_PATH, JSON.stringify(out, null, 2) + "\n", "utf8");
    saveManifest(manifest);
  }

  console.error(`\nDone: ${ok} downloaded, ${skipped} skipped, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
