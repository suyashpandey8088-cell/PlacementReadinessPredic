# Web migration verification · 2026-10-22

This record supersedes the original local-Streamlit verification for the Vercel
web app. `reports/verification.md` remains a historical record of the original UI.

## Local executed checks

- `python -m pytest -q`: **71 passed**. Includes the original scoring/ML/SQLite/
  Streamlit tests plus new Flask API validation, schema, body-size, metadata,
  inference and model-unavailability tests.
- `npm test`: **6 passed**. Explicit/idempotent save, separate browser storage,
  corrupt-history rejection, safe CSV cells, backup validation and 200-record limit.
- `npm run build`: succeeded. Production static JS/CSS generated in ignored `dist`.
- `npm audit --omit=dev`: zero reported vulnerabilities at verification time.
- `python -m pip check`: no broken requirements.
- `python -m compileall -q api src app.py tests`: passed.

Scoring and coaching are imported unchanged from the original Python modules;
API tests compare exact output against them rather than a copied frontend formula.
Model artifacts and synthetic metrics were not regenerated or invented.

## Real Chromium local workflow

`tests/browser-smoke.cjs` ran against the running Flask/Vite servers at 1440×1050
and 390×844. Executed:

1. Overview, assessment, cross-field validation failure and recovery.
2. Five submitted sections, editable review and actual API scoring.
3. Explicit save, seven-day plan checkbox and real CSV plan download.
4. Changed preparation inputs, recalculation, second save and genuine trend chart.
5. Actual CSV history download; refresh preserved saved history.
6. JSON backup download, confirmed deletion, useful empty state and validated
   two-record restore through the API.
7. Synthetic evaluation/data pages and actual saved-model inference.
8. About methodology disclosure.
9. Mobile navigation, no horizontal overflow in form/results, full mobile assessment.
10. Separate browser context started with empty history.

Successful run reported **zero JavaScript page errors**. Browser contexts were
isolated with normal multi-process Chromium; single-process test mode was removed
because it can share storage between contexts.

## Accessibility smoke checks

Injected axe-core into actual running pages and checked WCAG 2 A/AA and 2.1 AA tags.
Overview, assessment section 1, Model insights evaluation, and Privacy & data each
returned **zero violations** after fixes to secondary-text contrast and semantic
confusion-matrix markup. Keyboard tabs support arrows/Home/End; mobile navigation
supports Escape and traps focus while open. Hidden mobile navigation is removed
from the focus order. Reduced-motion preference is respected.

This is not a complete accessibility certification or an assistive-technology user
study. Other UI states still deserve continued manual and screen-reader review.

## Production deployment and public checks

The existing Vercel project `placement-readiness-predic` was changed from its failed
Python/Streamlit configuration to Vite static output plus the Flask function.
The first deployment reached **READY / PROMOTED**, assigned the public alias
**https://placement-readiness-predic.vercel.app**. The public homepage rendered the
actual UI, and `/api/health` returned JSON:

```json
{"history":"browser-only","scoring_version":"1.0","status":"ok"}
```

The sandbox cannot directly connect to Vercel via curl, so public GET checks use
the page-fetch tool. A separate GitHub Actions workflow, **Live Vercel smoke test**,
executes the reusable Chromium script from a hosted runner against the public
production alias, including actual API POST requests and model inference. Its
success must be checked independently; simply adding the workflow is not a pass.

The first commit's **Tests and production build** workflow passed remotely at:
https://github.com/suyashpandey8088-cell/PlacementReadinessPredic/actions/runs/39727569360

Final production deployment and live-browser workflow results are recorded after
verification, not inferred from the local tests.

## Explicit limits

- Device/browser/origin-local history; no account system, cloud sync or encryption
  at rest. Shared profiles can read saved records. JSON backups are private files.
- No new Supabase resources, cloud database or paid API was provisioned.
- The original local Streamlit version still uses SQLite; the deployed web version
  does not write SQLite or rely on serverless disk persistence.
- Synthetic metrics do not establish genuine hiring accuracy or fairness.
- No user study, high-stakes suitability, uptime guarantee or enterprise security
  certification is claimed.
