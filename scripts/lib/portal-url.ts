/**
 * Derive a hromada official-portal homepage from StrategyUrl.
 *
 * Aggregators (data.gov.ua, rada.info, toolkit, Wayback, e-dem, Google Docs, …)
 * are NOT treated as the hromada portal — PortalUrl stays null unless an override
 * supplies one. Manual overrides: data/sources/portal-url-overrides.json
 */

import { readFileSync } from "fs";
import { join } from "path";

const AGGREGATOR_HOSTS = new Set([
    "data.gov.ua",
    "rada.info",
    "toolkit.in.ua",
    "consult.e-dem.ua",
    "web.archive.org",
    "archive.org",
    "docs.google.com",
    "drive.google.com",
    "filesusr.com",
]);

export type PortalOverride = {
    /** Official portal homepage (trailing slash optional). */
    portal_url: string;
    /** Optional note — why override / source of the link. */
    note?: string;
};

export type PortalOverridesFile = {
    _comment?: string;
    /** Key = KATOTTG code (preferred) or exact Name as in hromadas.json */
    by_katottg?: Record<string, PortalOverride>;
    by_name?: Record<string, PortalOverride>;
};

function normalizeHost(host: string): string {
    return host.toLowerCase().replace(/^www\./, "");
}

function isAggregatorHost(host: string): boolean {
    const h = normalizeHost(host);
    if (AGGREGATOR_HOSTS.has(h)) return true;
    if (h.startsWith("opendata.")) return true;
    if (h.endsWith(".filesusr.com")) return true;
    if (h.includes("archive.org")) return true;
    return false;
}

/** True if host looks like a municipal / hromada site (not a national aggregator). */
export function isLikelyOwnPortalHost(host: string): boolean {
    const h = normalizeHost(host);
    if (!h || isAggregatorHost(h)) return false;
    if (h.endsWith(".gov.ua")) return true;
    if (h.includes(".otg.")) return true;
    // Common non-.gov municipal patterns in the corpus
    if (h.endsWith(".ua") && (h.includes("rada") || h.includes("city") || h.includes("gromada"))) {
        return true;
    }
    return false;
}

/**
 * If StrategyUrl is a Wayback capture, return the original URL string; else null.
 * Example: https://web.archive.org/web/20220310/http://www.nikopol-mrada.dp.gov.ua/...
 */
function unwrapWaybackOriginal(strategyUrl: string): string | null {
    try {
        const parsed = new URL(strategyUrl.trim());
        const host = normalizeHost(parsed.host);
        if (!host.includes("archive.org")) return null;
        // /web/<timestamp>/<original>  or  /web/<timestamp>im_/<original>
        const m = parsed.pathname.match(/^\/web\/\d+(?:[a-zA-Z_]+)?\/(.+)$/);
        if (!m) return null;
        const original = m[1];
        if (!/^https?:\/\//i.test(original)) return null;
        return original;
    } catch {
        return null;
    }
}

/**
 * Homepage origin for an own-portal StrategyUrl, or null.
 * Aggregators → null. Wayback captures unwrap to the original host when it looks municipal.
 */
export function derivePortalUrlFromStrategyUrl(strategyUrl: string | null | undefined): string | null {
    if (!strategyUrl || typeof strategyUrl !== "string") return null;
    const unwrapped = unwrapWaybackOriginal(strategyUrl);
    const candidate = unwrapped ?? strategyUrl.trim();
    let parsed: URL;
    try {
        parsed = new URL(candidate);
    } catch {
        return null;
    }
    if (!isLikelyOwnPortalHost(parsed.host)) return null;
    return `${parsed.protocol}//${parsed.host}/`;
}

export function loadPortalOverrides(repoRoot?: string): PortalOverridesFile {
    const root = repoRoot ?? join(__dirname, "..", "..");
    const path = join(root, "data", "sources", "portal-url-overrides.json");
    try {
        return JSON.parse(readFileSync(path, "utf-8")) as PortalOverridesFile;
    } catch {
        return {};
    }
}

/**
 * Resolve PortalUrl: override (by Katottg, then Name) wins; else derive from StrategyUrl.
 */
export function resolvePortalUrl(opts: {
    strategyUrl?: string | null;
    katottg?: string | null;
    name?: string | null;
    overrides?: PortalOverridesFile;
}): string | null {
    const ov = opts.overrides ?? {};
    const kat = (opts.katottg || "").trim();
    if (kat && ov.by_katottg?.[kat]?.portal_url) {
        return normalizePortalHome(ov.by_katottg[kat].portal_url);
    }
    const name = (opts.name || "").trim();
    if (name && ov.by_name?.[name]?.portal_url) {
        return normalizePortalHome(ov.by_name[name].portal_url);
    }
    return derivePortalUrlFromStrategyUrl(opts.strategyUrl);
}

function normalizePortalHome(url: string): string {
    const u = url.trim();
    if (!u) return u;
    try {
        const p = new URL(u);
        return `${p.protocol}//${p.host}/`;
    } catch {
        return u.endsWith("/") ? u : `${u}/`;
    }
}
