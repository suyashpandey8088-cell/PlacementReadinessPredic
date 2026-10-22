# Web migration verification · 2026-10-22

This record supersedes the original local-Streamlit verification for the Vercel
web app. `reports/verification.md` remains a historical record of the original UI.

Sections below dated before the "Optional accounts" addendum describe the guest-only
release; the addendum records what changed and supersedes those statements.

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

- Guest history remains device/browser/origin-local, with no encryption at rest;
  shared browser profiles can read it. Account history requires signing in.
- No paid API was provisioned. Optional accounts reuse the existing shared Supabase
  project through four new `p2p_*` tables; no pre-existing table was altered.
- The original local Streamlit version still uses SQLite; the deployed web version
  does not write SQLite or rely on serverless disk persistence.
- Synthetic metrics do not establish genuine hiring accuracy or fairness.
- No user study, high-stakes suitability, uptime guarantee or enterprise security
  certification is claimed.

## Final recorded results

- **Production release:** `dpl_A43fZmYVjTDRfabMf9dtXhS8eF6f` from runtime commit
  `c5f4d94b7b21a6dfe7c9bb3bff13f78f08321813` reached **READY / PROMOTED**.
- Public alias: **https://placement-readiness-predic.vercel.app**.
- After promotion, public `/api/health`, `/assessment` and `/model` were retrieved
  successfully. The assessment rendered real controls and the model page rendered
  actual measured metadata and the semantic confusion-matrix table.
- **71 Python tests, six browser-storage tests and production build passed remotely**
  for commit `c5f4d94`:
  https://github.com/suyashpandey8088-cell/PlacementReadinessPredic/actions/runs/39727868895
- **Live Vercel smoke test passed** from a GitHub-hosted Chromium runner:
  https://github.com/suyashpandey8088-cell/PlacementReadinessPredic/actions/runs/39727868988
  All browser steps and screenshot upload completed successfully. This run exercised
  the initial production release (`10e8ac3`) while the final hardening deployment
  was being prepared. It includes actual public API scoring and saved-model
  inference—not only local tests or a successful build status.
- The subsequent hardening release preserves those features and adds input-type
  validation, stricter browser-record validation and intentional config ordering;
  it passed the full local browser suite and the remote unit/API/build checks above.
  The public GET checks after its promotion are listed separately rather than
  misrepresenting the earlier live test as a second post-promotion browser run.
- A requested manual repeat of the live workflow was not dispatched: GitHub returned
  `403 Resource not accessible by integration` for workflow dispatch. The successful
  push-triggered checks and deployment are unaffected. No broader GitHub login or
  repository access failure is inferred from that specific permission restriction.
- No main-branch merge was performed. The source and documentation are pushed on
  `arena/cb92804d-placementreadinesspredic`. Later documentation-only updates do not
  change the deployed runtime files.

## Optional accounts · added 2026-10-22

The earlier guest-only release is superseded by optional sign-up/sign-in. Every
previously verified guest behaviour still passes unchanged.

### Local executed checks

- `python -m pytest -q`: **86 passed**. The 15 account tests use a fake store/auth
  pair and cover: duplicate email (409), weak password (422), 8 failed logins then
  `429` with `Retry-After`, unauthenticated history (401), cross-user record access
  (404), the 200-record cap (409), server-side score recomputation on import,
  idempotent import, duplicate IDs (422), oversized payload (413), corrupt stored
  records skipped, password change revoking other sessions, account deletion, and
  an unconfigured deployment returning `{"available": false, "user": null}`.
- `npm test`: **11 passed**, including email/password rules, initials, and
  `safeNextPath` rejecting external, protocol-relative and `/login` targets.
- `npm run build`: succeeded (CSS 33.27 kB, JS 265.19 kB / 87.68 kB gzip).
- `node --check web/main.js` and `python -m compileall -q api src`: clean.
- A DOM harness (happy-dom + esbuild, stubbed Chart.js/Lucide) drove the real
  `web/main.js` against a mocked API: sign-in, redirect to `/progress`, account
  header, account-history rendering, password change, sign-out, mode switch to
  sign-up with URL persistence, and sign-up. Screenshots of `/login`, `/account`
  and `/privacy` were reviewed at 1440×1050 and 390×844; no horizontal overflow.

### Real Chromium, local servers

`tests/browser-smoke.cjs` passed locally against Flask + Vite, now also covering
`/login` (tab switch, password visibility toggle), `/account` signed out, and the
signed-out privacy page. Guest assessment, plan ticks, CSV downloads, delete and
restore, model inference and mobile layouts still pass with zero JavaScript errors.

### Live production account flow

The reusable smoke test now signs in with a disposable account (`p2p-smoke@example.com`,
created on first run), completes a full five-section assessment, saves it to the
account, and confirms it appears in `/progress`. A second browser context with no
cookie receives **401** from `/api/history` with no record data, and the account
data is then deleted, after which the session no longer authenticates.

- Run: https://github.com/suyashpandey8088-cell/PlacementReadinessPredic/actions/runs/39732909720
  — **success** (commit `8130d3b`).
- Post-run database check: `p2p_profiles`, `p2p_sessions` and `p2p_assessments`
  contained no smoke-test rows; assessments were removed by the profile cascade.
  The shared Supabase sign-in identity remains, exactly as the UI states.
- The same run also re-verified every guest flow against the account-enabled build.

### Production release with accounts

- Deployment `dpl_AweyPGou318fSZB2p8sar9ZyitGE` from `b7bb8ce` reached
  **READY / PROMOTED** and was assigned
  **https://placement-readiness-predic.vercel.app**.
- `/api/health` returned
  `{"status":"ok","scoring_version":"1.0","history":"browser-or-account","auth":"configured","release":"b7bb8ce"}`.
- `/api/auth/me` returned `{"available":true,"user":null}` for a signed-out request.
- A real visitor account created through the deployed UI was observed in
  `p2p_profiles`/`p2p_sessions` during verification, independently confirming that
  sign-up, password grant and session creation work against the live database.

### Remaining limits

- No verification or password-reset email is sent, so email ownership is unverified
  and a forgotten password cannot be recovered in-app.
- Account deletion keeps the shared GoTrue identity (documented in the UI and README).
- Rate limits and CSRF checks are application-level, not a substitute for a full
  security review or enterprise identity provider.
