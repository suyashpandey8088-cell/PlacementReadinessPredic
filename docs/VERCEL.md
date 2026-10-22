# Vercel web migration

## Decision

Keep the original Python scoring/recommendation code and local Streamlit app.
Use a small vanilla-JavaScript/Vite frontend plus a stateless Flask API for the
requested Vercel deployment. No duplicate JavaScript scoring formula, paid AI API,
external font service, account registration or new cloud database is required.

Streamlit is still supported locally but is not the production entrypoint.
Changing only a Vercel build command would not adapt its stateful UI/session model.

## Request flow

```text
Browser UI (Vite static files)
  → same-origin /api/config → Python input schema
  → /api/validate → category-specific validation on Continue
  → /api/assess → readiness score + rules-based coaching + plan
  → explicit Save → browser localStorage (not Vercel disk)

Model lab → /api/model → committed measured metadata
          → /api/simulate → trusted cached Scikit-learn pipeline
```

API endpoints are public, do not require cookies and expose no saved-student API.
Readiness calls import no Streamlit or ML dependencies. Only educational inference
lazily imports Pandas and loads the trusted model. Every API response is `no-store`;
request bodies are limited to 32 KiB. Errors return useful JSON without request-body
logging. Standard serverless scaling/platform limits apply; no claim of advanced
abuse prevention or enterprise authentication is made.

### Storage differences

| | Local Streamlit | Vercel web |
|---|---|---|
| UI | Stateful Streamlit server | Static Vite UI + short Python requests |
| Saved history | Local SQLite, scoped by workspace key | Same-browser, same-origin localStorage |
| Unsaved draft | Streamlit session state | Tab sessionStorage + memory |
| Recovery | Workspace key on same server | Private JSON backup, explicit restore |
| Cross-device automatic sync | No | No |
| Accounts | No | No |

On a shared device, another person with the same browser profile can read local
history. There is no login/encryption guarantee. JSON backup restore recomputes
scores and recommendations using current scoring criteria and preserves source
assessment IDs/timestamps. Duplicate IDs are skipped. It does not imply that
imported assessment timestamps were independently verified. Checklist ticks are
browser conveniences, not externally assessed achievements; they are not part of
assessment backup files.

The web app intentionally does not connect to an unrelated existing cloud database.
Moving to synced accounts later needs explicit identity and row-authorization design.

## Deployment settings

- Existing project: `placement-readiness-predic`.
- Framework: Vite; root is repository root.
- Install `npm ci`; build `npm run build`; output `dist`.
- `api/index.py` is the Flask/WSGI function; `/api/*` rewrites to it.
- Runtime uses `.python-version` **3.12** and pinned Scikit-learn **1.7.2**.
- `requirements.txt` contains web/API runtime dependencies only.
- `requirements-streamlit.txt` preserves local UI dependencies;
  `requirements-dev.txt` installs both for the complete test suite.
- `.vercelignore` and function excludes prevent bundling local databases, venv,
  developer tooling, training data, docs, tests and Streamlit UI.
- No environment variables or secrets required. No cloud credentials shipped to
  the browser. No cloud database provisioned.

The repository's Vercel project currently has automatic Git deployment creation
disabled. An explicit connector deployment is used; a push alone should not be
assumed to publish changes. The production deployment can use this session branch
without modifying or merging `main`.

### Shareability / protection

After deployment, check the production alias **without being logged into Vercel**.
Deployment Protection may restrict some URLs. If the platform requires login,
change the project's approved protection settings in the Vercel dashboard before
calling the site public. A READY build alone does not prove visitors can use it.

## Production checks

1. Open the assigned HTTPS alias; verify actual UI assets load.
2. `GET /api/health` must return JSON, not the SPA HTML document.
3. `GET /api/config` must include five categories and version 1.0.
4. Submit a valid profile and compare against `src.readiness_scoring.assess`.
5. Invalid fields must return helpful 422 errors.
6. `/api/model` must return genuine synthetic metadata; run `/api/simulate` on a
   seven-feature sample to exercise the saved artifact under the deployed runtime.
7. Reload `/assessment`, `/progress`, `/model` directly to test SPA routing.
8. Save, refresh, export, delete and restore in the browser. A separate browser
   profile must start empty. Check mobile navigation and horizontal overflow.
9. Confirm that the UI discloses device-local storage and synthetic limitations.

## Repeatable browser regression check (optional development tooling)

With the API and Vite servers running:

```bash
# Install in a throwaway ignored folder; not a production dependency.
npm install --prefix .cache/browser playwright
# Install a supported Chromium build using your normal Playwright environment.
NODE_PATH="$PWD/.cache/browser/node_modules" node tests/browser-smoke.cjs
```

Set `BROWSER_EXECUTABLE=/path/to/chromium` if using an existing browser binary.
`P2P_BASE_URL` defaults to `http://127.0.0.1:5173`; it can target a deployed origin.
The script creates only local test-browser records, exercises downloads, deletion
and JSON restore, and saves screenshots in ignored `.cache/screenshots/`.
It does not populate server storage or fabricate public history.

This sandbox used `@sparticuz/chromium` from npm plus bundled NSS/NSPR libraries:

```bash
NODE_PATH="$PWD/.cache/browser/node_modules" USE_SPARTICUZ=1 \
  LD_LIBRARY_PATH="$PWD/.cache/al2023/lib" node tests/browser-smoke.cjs
```

Single-process Chromium is deliberately disabled for the test because that mode can
share storage between browser contexts; isolation is tested with proper independent
contexts. Browser tooling is not needed to run the application.

## Accessibility and design

Warm off-white, forest-green accent, consistent secondary text, real Lucide icons,
small purposeful panels rather than decorative dashboards. Mobile navigation is
collapsed by default; hidden menus leave the focus order, Escape closes navigation,
Tab remains inside an open mobile menu, and result/model tabs support arrow keys.
Forms have associated labels/legends, error regions and native numeric validation.
Charts have textual values/alternatives. The confusion matrix is a semantic table.

Automated accessibility checks are a smoke test, not a certification or a substitute
for assistive-technology and student usability studies. Findings and fixes belong
in the verification record.

## Verified release

Public app: https://placement-readiness-predic.vercel.app

The Vercel production release reached READY/PROMOTED, and the public site and API
were checked. A hosted Chromium smoke test passed against the initial production
release; the latest hardening revision passed 71 Python tests, six JavaScript tests
and production build. Exact revision/timing distinctions and check links are in
[the verification record](../reports/web_verification.md).
