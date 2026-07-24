# Stakeholder site (GitHub Pages)

Static site rooted at this folder. After Pages is enabled (Actions source),
the public URL is:

**https://maxsemenchuk.github.io/hromada-strategy-collab/**

Coverage reflected on the site (2026-07-24 release): **1,469** metadata rows,
**77** text-mined strategies (**68** with Goals), **2,278** matching-edges (v6),
known МСС ranks **#5–#11**. PIN map: **~447** PIN nodes / **918** edges from KSE; underlay **~1 418** mainland
hromadas with coordinates (metadata — not the strategy corpus). Click a point for
`PortalUrl` / `StrategyUrl` when present in the release.

| Path | Content |
|------|---------|
| [`index.html`](index.html) | Landing / «О проєкті» (all stakeholder audiences) |
| [`matches.html`](matches.html) | Known pairs + top hypotheses |
| [`funds.html`](funds.html) | Donor portfolio: shared next grant / bridges / hubs |
| [`mss-pin-matching-graph.html`](mss-pin-matching-graph.html) | Full PIN map + thematic / operational overlays |
| [`outreach.html`](outreach.html) | Draft outreach copy for all four stakeholder groups |
| [`hromada-project-passport.html`](hromada-project-passport.html) | Redirect → `index.html` (legacy URL) |

Shared chrome: [`assets/site.css`](assets/site.css), [`assets/nav.js`](assets/nav.js).

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
