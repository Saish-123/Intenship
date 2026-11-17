# Ridgeline Trail Club: Performance and Accessibility (Week 4)

The Week 3 page, audited and rebuilt for speed and accessibility. `src/` is the readable code; `dist/` is the optimised build to deploy.

**Live demo:** _add your Netlify / Cloudflare Pages / GitHub Pages link here_

## Results (Lighthouse, mobile, simulated slow 4G + 4x CPU, median of 5 runs)
| Measure | Before | After |
|---|---|---|
| Largest Contentful Paint | 1564 ms | **699 ms** (-55%) |
| First Contentful Paint | 934 ms | **699 ms** (-25%) |
| Layout shift (CLS) | 0.0365 | **0** |
| Data transferred | 84.5 KB | **43.1 KB** (-49%) |
| Best Practices | 96 | **100** |
| Accessibility / SEO | 100 / 100 | 100 / 100 |
| Total Blocking Time | 62 ms | 125 ms (worse in the lab; explained in the report, section 4.9) |

Lighthouse and axe already scored about 100 before, so the accessibility work came from my own probes: keyboard focus, forced colours, text spacing, colour-vision simulation and the accessibility tree. See the report for the full list of 11 issues found and fixed.

## What changed
**Performance**
- Self-hosted fonts, subset to the characters used (69.5 KB to 24.2 KB), preloaded, with a metric-matched fallback so text does not jump
- Critical CSS inlined; the rest loads without blocking render (three strategies measured, the trade-off is explained)
- Minified HTML, CSS and JS; SVGs optimised (about 8.5 KB to 0.5 KB each); favicon added
- Content-hashed file names with immutable caching headers (`_headers`, `.htaccess`)
- Hero image preloaded with the right crop; lazy, sized, async-decoded images elsewhere

**Accessibility (WCAG 2.2)**
- Skip link target is focusable; keyboard focus is never hidden by the sticky header or the back-to-top button
- Forced-colours (High Contrast) support; selected state shown by a tick, not colour alone
- Decorative images use empty alt text; gallery photos keep descriptions
- Real Safety and Privacy page instead of dead links; required-fields note; `aria-current="location"`
- `prefers-contrast` and reduced-motion support; named footer navigation

## Tests
`102 / 102` automated checks pass on the built files (74 Week 3 behaviour checks plus accessibility and performance checks). axe-core: 0 violations in light and dark themes and 4 interactive states. html-validate, stylelint and ESLint: 0 errors. Visual regression: every section within 0.7% of the original. Not covered: Firefox, Safari, real screen readers, WebPageTest and WAVE (the report explains how to run them).

## Build, test, deploy
```
npm install
npm run build        # src/ -> dist/
npm run lint
# serve dist/ over HTTP, then:
SITE_URL=http://localhost:3000/ python tests/run_tests.py
```
Deploy `dist/`. Netlify and Cloudflare Pages read `dist/_headers`. GitHub Pages cannot set caching headers.

## Structure
```
src/                 readable source (index.html, policies.html, css/critical.css, css/main.css, js/, fonts/, images/)
dist/                optimised build
build.mjs            the build script
tools/               font subsetting script
tests/               automated checks, probes, Lighthouse and build reports
screenshots/         evidence (forced colours, colour-blind simulation, keyboard focus)
Week4_Report.docx    the full report
```
