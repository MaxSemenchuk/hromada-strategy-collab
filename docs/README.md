# Stakeholder site (GitHub Pages)

Static site rooted at this folder. After Pages is enabled (Actions source),
the public URL is:

**https://maxsemenchuk.github.io/hromada-strategy-collab/**

Coverage reflected on the site (2026-07-29 release): **1,469** metadata rows,
**77** text-mined strategies (**68** with Goals), **2,278** matching-edges (v7),
known МСС ranks **#6–#14**. Extra layers: complementary, explicit-ask, resources/DREAM.
PIN map: **~459** PIN nodes / **918** edges from KSE; underlay **~1 418** mainland
hromadas with coordinates (metadata — not the strategy corpus). Click a point for
`PortalUrl` / `StrategyUrl` when present in the release.

| Path | Content |
|------|---------|
| [`index.html`](index.html) | Landing / «Про проєкт» (all stakeholder audiences) |
| [`matches.html`](matches.html) | Known pairs + thematic / operational / complementary / explicit-ask |
| [`funds.html`](funds.html) | Donor portfolio: shared next grant / bridges / hubs |
| [`resources.html`](resources.html) | KSE resource proxies × DREAM revealed priorities |
| [`mss-pin-matching-graph.html`](mss-pin-matching-graph.html) | Full PIN map + four hypothesis overlays |
| [`strategy-writing-guide.md`](strategy-writing-guide.md) | How to write strategies that surface МСС signals |
| [`corpus-growth.md`](corpus-growth.md) | Priority corpus growth checklist |
| [`hromada-project-passport.html`](hromada-project-passport.html) | Redirect → `index.html` (legacy URL) |

Shared chrome: [`assets/site.css`](assets/site.css), [`assets/nav.js`](assets/nav.js), [`assets/i18n.js`](assets/i18n.js). UK/EN language switch lives in the site nav.

## Enable once

Repo **Settings → Pages → Deploy from a branch**: `main` / `/docs`
(or GitHub Actions via `.github/workflows/deploy-pages.yml`).

Local preview:

```bash
cd docs && python3 -m http.server 8765
# open http://127.0.0.1:8765/
```

Markdown files in this folder (`*.md`) are research docs for the repo, not
nav pages — they are still served as raw text if opened by URL.
