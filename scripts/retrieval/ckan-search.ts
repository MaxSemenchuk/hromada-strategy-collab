/**
 * Query data.gov.ua CKAN API for hromada development-strategy datasets and emit a
 * flat JSON list of candidate document URLs.
 *
 * Usage:
 *   yarn ckan-search                          # stdout
 *   yarn ckan-search --out scripts/retrieval/ckan-candidates.json
 *   yarn ckan-search --limit 10                 # first page only (smoke test)
 *
 * API: https://data.gov.ua/api/3/action/package_search?q=стратегія+розвитку+громади
 * License: CC BY 4.0 (data.gov.ua)
 */

const CKAN_BASE = "https://data.gov.ua/api/3/action/package_search";
const DEFAULT_QUERY = "стратегія розвитку громади";
const PAGE_SIZE = 100;

export interface CkanCandidate {
    title: string;
    hromada_hint: string;
    resource_url: string;
    format: string;
}

interface CkanResource {
    url?: string;
    format?: string;
    name?: string;
    mimetype?: string;
}

interface CkanPackage {
    title?: string;
    notes?: string;
    organization?: { title?: string };
    resources?: CkanResource[];
}

interface CkanSearchResult {
    success: boolean;
    result?: {
        count: number;
        results: CkanPackage[];
    };
}

function parseArgs() {
    const args = process.argv.slice(2);
    const get = (flag: string) => {
        const i = args.indexOf(flag);
        return i >= 0 ? args[i + 1] : undefined;
    };
    return {
        out: get("--out"),
        query: get("--query") || DEFAULT_QUERY,
        limit: get("--limit") ? Number(get("--limit")) : undefined,
    };
}

/** Best-effort hromada name guess from dataset title or publishing org. */
function extractHromadaHint(pkg: CkanPackage): string {
    const org = pkg.organization?.title?.trim();
    if (org) {
        // "Виконавчий комітет Ніжинської міської ради" → keep as-is for manual review
        return org;
    }
    return (pkg.title || "").trim();
}

function normalizeFormat(resource: CkanResource): string {
    const fmt = (resource.format || resource.mimetype || "unknown").trim();
    return fmt.replace(/\*$/, "").toUpperCase() || "UNKNOWN";
}

function pickResourceUrl(resource: CkanResource): string | null {
    const url = resource.url?.trim();
    return url || null;
}

async function fetchPage(query: string, start: number, rows: number): Promise<CkanSearchResult> {
    const params = new URLSearchParams({
        q: query,
        start: String(start),
        rows: String(rows),
    });
    const res = await fetch(`${CKAN_BASE}?${params}`);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`CKAN package_search failed: ${res.status} ${text.slice(0, 200)}`);
    }
    return res.json() as Promise<CkanSearchResult>;
}

async function searchAll(query: string, maxResults?: number): Promise<CkanCandidate[]> {
    const candidates: CkanCandidate[] = [];
    let start = 0;

    while (true) {
        const rows = maxResults != null ? Math.min(PAGE_SIZE, maxResults - candidates.length) : PAGE_SIZE;
        if (rows <= 0) break;

        const data = await fetchPage(query, start, rows);
        if (!data.success || !data.result) {
            throw new Error("CKAN API returned success=false");
        }

        for (const pkg of data.result.results) {
            const hint = extractHromadaHint(pkg);
            const title = (pkg.title || pkg.notes || "Untitled").trim();
            const resources = pkg.resources?.length ? pkg.resources : [{} as CkanResource];

            for (const resource of resources) {
                const resourceUrl = pickResourceUrl(resource);
                if (!resourceUrl) continue;

                candidates.push({
                    title: resource.name?.trim() || title,
                    hromada_hint: hint,
                    resource_url: resourceUrl,
                    format: normalizeFormat(resource),
                });
            }
        }

        start += data.result.results.length;
        if (start >= data.result.count || data.result.results.length === 0) break;
        if (maxResults != null && candidates.length >= maxResults) break;
    }

    return candidates;
}

async function main() {
    const { out, query, limit } = parseArgs();
    const results = await searchAll(query, limit);

    const json = JSON.stringify(results, null, 2);
    if (out) {
        const fs = await import("fs");
        fs.writeFileSync(out, json + "\n", "utf8");
        console.error(`Wrote ${results.length} candidates to ${out}`);
    } else {
        console.log(json);
    }
}

main().catch((err) => {
    console.error(err instanceof Error ? err.message : err);
    process.exit(1);
});
