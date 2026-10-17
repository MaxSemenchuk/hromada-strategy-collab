/**
 * Offline, idempotent data-hygiene pass over data/releases/hromadas.json:
 *   - fill missing Katottg (+ null Rayon/Population) from data/sources/katottg-overrides.json
 *   - normalize Oblast to the "X область" form
 *   - drop the never-populated `Sectors` field (sector signal lives in dream-priorities.json)
 *
 * Usage: yarn apply-hromada-fixes
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

const root = join(__dirname, "..");
const releasePath = join(root, "data", "releases", "hromadas.json");
const manifestPath = join(root, "data", "releases", "hromadas.manifest.json");
const overridesPath = join(root, "data", "sources", "katottg-overrides.json");

type Row = Record<string, unknown> & { Name: string; Katottg: string | null; Oblast: string | null };
type Override = { Katottg: string; Rayon?: string | null; Population?: number | null };

function main() {
    const rows = JSON.parse(readFileSync(releasePath, "utf-8")) as Row[];
    const { overrides } = JSON.parse(readFileSync(overridesPath, "utf-8")) as {
        overrides: Record<string, Override>;
    };

    let katottgFilled = 0;
    let oblastFixed = 0;
    for (const row of rows) {
        const ov = overrides[row.Name];
        if (ov && !row.Katottg) {
            row.Katottg = ov.Katottg;
            if (row.Rayon == null && ov.Rayon) row.Rayon = ov.Rayon;
            if (row.Population == null && ov.Population != null) row.Population = ov.Population;
            katottgFilled++;
        }
        if (row.Oblast && !row.Oblast.endsWith("область")) {
            row.Oblast = `${row.Oblast} область`;
            oblastFixed++;
        }
        delete row.Sectors;
    }

    writeFileSync(releasePath, JSON.stringify(rows, null, 2) + "\n");

    const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
    manifest.katottgRows = rows.filter((r) => r.Katottg).length;
    manifest.hygieneAppliedAt = new Date().toISOString();
    writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n");

    console.log(
        `Katottg filled: ${katottgFilled}; Oblast normalized: ${oblastFixed}; rows with Katottg: ${manifest.katottgRows}/${rows.length}`
    );
}

main();
