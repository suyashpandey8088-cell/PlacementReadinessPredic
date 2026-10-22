# Path2Placement
### Prepare with purpose. Understand your next step.

**Live app: [placement-readiness-predic.vercel.app](https://placement-readiness-predic.vercel.app)**

An explainable placement-readiness assessment for engineering students, now with a
**responsive Vercel-ready web app**, a Python scoring API, browser-local guest history
and **optional accounts** for cross-device history. The original Streamlit application
remains available locally.

> **Readiness ≠ placement probability.** The readiness score uses documented rules,
> not a trained model. A separate learning lab trains classifiers on explicitly
> **synthetic interview-exercise outcomes**. No result guarantees employment.

## The web experience

- Guided five-step assessment with rating descriptions, draft retention, optional
  blank test scores, browser/server validation and an editable review screen.
- Explainable 0–100 readiness score, category breakdown, relative strengths and gaps.
- Deterministic, prioritized recommendations with measurable completion criteria.
- Personalized seven-day starter plan, checkable days and plan CSV download.
- Explicitly saved history, trend chart, category changes, historical result inspection.
- **Optional sign-up/sign-in** with 30-day secure-cookie sessions; guest mode stays complete.
  Signed-in history is stored per account and every query is scoped to the session's user ID.
- CSV export, JSON backup/restore with server-side score recomputation, confirmed deletion.
- Separate ML learning lab: actual model comparison, holdout metrics, confusion matrix,
  class distribution, importance statistics and real saved-model inference.
- Responsive navigation, keyboard-visible focus, semantic forms, live error messages,
  reduced-motion support and no external font or paid API dependency.

### Why the architecture changed

Streamlit needs a running stateful UI server. Rather than attempting to keep one
inside serverless functions, the deployed app uses **Vite + vanilla JavaScript**
for the interface and **Flask on Vercel's Python runtime** for short API requests.
No React/Next.js rewrite was necessary. The API imports the **same Python scoring
and recommendation modules** as Streamlit; no second scoring formula is duplicated
in JavaScript.

Vercel's function disk is not used as a database. Guest history stays in **this
browser's localStorage**; drafts and unsaved results use sessionStorage. Optional
accounts add a separate, user-scoped history in Supabase Postgres, accessed only by
the Python API with a server-side key. See [privacy](#privacy-and-storage) and
[accounts](#optional-accounts).

## Run the web app locally

Requirements: **Node.js 22+** and **Python 3.11 or 3.12**. Vercel is configured for
Python 3.12, with the artifact's Scikit-learn version pinned.

```bash
git clone https://github.com/suyashpandey8088-cell/PlacementReadinessPredic.git
cd PlacementReadinessPredic
git checkout arena/cb92804d-placementreadinesspredic
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
```

Run these in **two terminals** from the project root:

```bash
# Terminal 1: Python API
source .venv/bin/activate
python -m flask --app api.index run --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2: web UI; /api requests are proxied to Python
npm run dev
```

Open `http://localhost:5173`. Browser requests use relative `/api/...` URLs, not
sandbox/backend localhost addresses. No API key, account or database is required.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
# Terminal 1
.\.venv\Scripts\python.exe -m flask --app api.index run --host 0.0.0.0 --port 8000
# Terminal 2
npm run dev
```

Using the venv executables directly avoids PowerShell activation-policy changes.

### Original Streamlit application

```bash
python -m pip install -r requirements-streamlit.txt
streamlit run app.py
```

This version retains local SQLite and workspace recovery keys. They are **not** used
by the Vercel web version. See [the local Streamlit guide](docs/STREAMLIT_GUIDE.md).

## Test, build and train

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q             # Core logic, API, database and Streamlit tests
npm test                       # Browser storage / backup / CSV unit tests
npm run build                  # Production UI output in dist/
python -m pip check

# Optional: regenerate the explicitly synthetic dataset and saved model
python -m src.train_model --generate
```

Training is **never** run during assessment or on frontend navigation. The small,
trusted model artifact and metadata are included. Never load untrusted Joblib files;
pickle-based serialization can execute code. After retraining, redeploy/restart
the API to replace cached model resources.

The current local verification passes **71 Python tests** and **6 browser-storage tests**,
plus production frontend build and scripted desktop/mobile workflows. See
[the web verification record](reports/web_verification.md) for exact scope and limitations.

A reproducible real-browser regression script is included in
`tests/browser-smoke.cjs`. Setup and its limitations are described in
[docs/VERCEL.md](docs/VERCEL.md). GitHub Actions runs Python tests, browser-storage
unit tests and the production build. Remote check status must be inspected separately.

## Scoring methodology · version 1.0

All configuration lives in `src/config.py`.

| Category | Weight | Within-category criteria |
|---|---:|---|
| Academic preparation | 15% | CGPA 45%, consistency 20%, core subjects 35% |
| Programming & DSA | 30% | languages 10%, programming 30%, DSA 40%, coding practice 20% |
| Projects & experience | 25% | count 10%, demos 20%, documented 15%, quality 50%, internship 5% |
| Aptitude & communication | 15% | aptitude 35%, optional reasoning 15%, communication 25%, explanation 25% |
| Interview & resume | 15% | optional mock 25%, resume 30%, preparation 25%, project confidence 20% |

- Ratings: `(rating − 1) / 4 × 100`. CGPA: `cgpa × 10`. Percentages are unchanged.
- Count contribution: `min(count / cap, 1) × 100`. Caps: **3 languages**, **250
  understood coding problems**, **3 projects**, **2 demos**, **2 documented projects**.
- A completed internship contributes at most **1.25 overall points**. Project quality
  has substantially more influence than quantity.
- Missing optional tests are excluded only within their category and other weights
  are rescaled. No test score is invented; comparisons with different coverage are flagged.
- Demos/documented projects cannot exceed total completed projects. Zero projects
  requires quality 1; zero languages requires programming proficiency 1.
- Full precision is used before rounding the final score to two decimals. The exact
  score is displayed alongside the rounded headline.

Bands: **0–<40** Foundation Building; **40–<60** Developing; **60–<75** Progressing
Toward Readiness; **75–<90** Nearly Ready; **90–100** Strong Preparation. These are
product-design choices, **not validated employability thresholds**. Self-assessments
are subjective and do not measure a student's worth or future potential.

## Dataset and ML learning lab

No real-outcome dataset was supplied or verified, so the fallback uses **1,400
simulated observations** with related, noisy simulated labels. There are no genuine
hiring records. Exact distributions, coefficients, target meaning, permissions notes
and replacement guidance are in [the data card](data/README.md).

Preprocessing uses `Pipeline` + `ColumnTransformer`. A stratified 80/20 split holds
out 280 observations. Imputation, scaling and encoding fit inside training CV folds,
not on the full dataset. The winner is selected by five-fold training CV F1, then
fit on training rows and evaluated on the untouched holdout.

| Candidate | Training CV F1 mean |
|---|---:|
| Logistic Regression | 0.6976 |
| Decision Tree | 0.6046 |
| Random Forest | 0.6621 |

Selected Logistic Regression: held-out synthetic accuracy **0.7250**, precision
**0.6984**, recall **0.6929**, F1 **0.6957**. Confusion matrix (actual rows 0/1,
predicted columns 0/1): `[[115,38],[39,88]]`.

**These metrics do not establish real-world placement accuracy.** Feature importance
is not causation. See [the measured evaluation report](reports/model_evaluation.md),
metadata and the Model insights page. Schema/version/checksum failures produce a
recoverable lab error without disabling ordinary readiness assessments.

## Privacy and storage

**Guest mode (default):** answers are sent to the same-origin Python API for
computation. Nothing is written to a server database unless you create an account
and choose to save. Only the Save action writes to browser storage. The same
browser profile on the same site can read it; that is **device-local privacy, not
identity authentication or encrypted storage**. Incognito mode, browser cleanup or
a changed origin can remove or hide records.

- CSV exports are human-readable reports, not backup imports.
- JSON backups contain inputs, results and timestamps; keep them private.
- Restore validates the backup and recomputes every input profile through the
  Python API before writing the merged history. A failed import does not partially save.
- At most 200 assessments are kept; reaching the limit gives an explicit error rather
  than silently deleting records. Backups are limited to 2 MB.
- Delete clears local assessments, plan ticks and this tab's draft/result. It cannot
  delete files already exported to your device or data in another browser.

## Optional accounts

Signing in is genuinely optional: every assessment, result, plan and guest export
works without an account. Accounts only change **where explicitly saved history
lives**.

- **Credentials:** Supabase Auth stores the email and password hash. This app never
  receives or stores the password itself.
- **Sessions:** the API issues a random 32-byte token in a `Secure`, `HttpOnly`,
  `SameSite=Lax` cookie (`__Host-p2p_session` on HTTPS). Only a SHA-256 hash of the
  token is stored server-side, sessions expire after 30 days, and sign-out deletes
  the row. Password changes invalidate other sessions.
- **Data:** `p2p_profiles` (email), `p2p_sessions` (token hashes) and
  `p2p_assessments` (one JSON record per saved assessment). All three have row-level
  security enabled with **no browser-facing policies**; only the server-side
  service key can read them, and every account query is filtered by `user_id`.
- **Limits:** 8 failed sign-ins per email per 15 minutes, 30 per IP, 5 sign-ups per IP
  per hour. Duplicate emails return a clear conflict instead of overwriting an account.
- **Deletion:** "Delete my Path2Placement data" removes the profile, sessions and all
  saved assessments, then signs you out. The underlying shared sign-in identity is
  kept, so signing in again starts with an empty history; the UI states this explicitly.
- **Honest gaps:** this demo sends no verification or password-reset email, so email
  ownership is unverified and a forgotten password cannot be recovered in-app. It is
  not an enterprise identity system and should not hold confidential student records.
  The shared Supabase project also serves another demo app, so the same email may be
  recognized there; assessment tables remain separate.

Local setup for accounts needs a Supabase project and these server-side variables
(`SUPABASE_SECRET_KEY` must never be exposed to the browser):

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_PUBLISHABLE_KEY="sb_publishable_..."
export SUPABASE_SECRET_KEY="server-only-secret"   # service_role key; never ship to the client
```

Without them the app still runs: `/api/health` reports `"auth":"unconfigured"`,
`/api/auth/me` returns `{"available":false,"user":null}`, and `/login` explains that
accounts are unavailable. Run the four `p2p_*` table migrations (see
[docs/VERCEL.md](docs/VERCEL.md#account-tables)) before enabling accounts.

## Deployment on Vercel

`vercel.json` configures Vite static output plus the Python function in
`api/index.py`. `.python-version` selects 3.12; `requirements.txt` contains only
API/runtime dependencies. Streamlit and developer tools are excluded from the
function bundle. The frontend sends relative URLs, and SPA routes rewrite to
`index.html` while `/api/*` routes go to Python.

Import this repository into Vercel, use the current working branch, and keep:

- Framework: **Vite**
- Build: **`npm run build`**
- Install: **`npm ci`**
- Output: **`dist`**
- Root directory: repository root
- Environment variables: optional accounts only — `SUPABASE_URL`,
  `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` (server-only). Guest mode needs none.

See [docs/VERCEL.md](docs/VERCEL.md) for architecture, production smoke checks,
redeployment and deployment protection. The user-requested production deployment
uses this branch; it does not automatically merge changes into `main`.

## Project map

```text
web/main.js, styles.css   Responsive UI, navigation, forms, result/history/account pages
web/auth-utils.js        Email/password/initials validation and safe next-path rules
web/storage.js           Validated explicit saves, backup parsing, safe CSV export
api/index.py             Flask API; shared Python scoring and inference
api/accounts.py          Optional accounts, sessions, rate limits, account history
api/supabase_store.py    Server-only Supabase REST/Auth client
index.html, public/      Web entry and static favicon
vite.config.js           Local proxy and production build
vercel.json              Serverless routing, function bundle and security headers
src/config.py            Single input schema, normalization caps and category weights
src/readiness_scoring.py  Reproducible validation and readiness scoring
src/recommendations.py   Deterministic priorities and seven-day plan
src/predict.py           Trusted saved-pipeline validation and illustrative inference
src/train_model.py       Separate reproducible training and evaluation command
src/data_preprocessing.py Synthetic generator, dataset checks and preprocessing
app.py, src/ui.py         Original local Streamlit interface
src/database.py          Original local-only SQLite storage (not used on Vercel)
models/, data/           Small model/metadata and documented synthetic dataset
tests/                   Python, browser-storage and optional real-browser tests
reports/                 Evaluation and verification records
docs/                    Deployment, presentation and legacy local-app guides
```

## Common problems

| Problem | Action |
|---|---|
| Web page cannot open its API | Start Flask on port 8000 as well as Vite locally; check `/api/health` after deployment |
| Port already used | Stop the old process or update both the API port and Vite proxy |
| Model missing/incompatible | Regenerate artifacts and restart/redeploy; readiness scoring is independent |
| History seems missing | It belongs to the same browser profile **and origin**; restore a private JSON backup |
| Browser storage blocked/full | Assessment still works in memory; browser saving may fail explicitly |
| Import fails | Use an actual JSON backup, not CSV; restore validates/recomputes all inputs before saving |
| Deployment shows sign-in | Check the Vercel project's Deployment Protection settings before sharing publicly |
| Streamlit command unavailable | Install `requirements-streamlit.txt`, not just the web runtime dependencies |

## Limits and next steps

This is an educational preparation tool, not a hiring, admission or ranking system.
Self-ratings, design-choice weights, unequal opportunities and missing tests limit
interpretation. Synthetic data cannot prove external validity or fairness. Add real
user feedback and objective quizzes before expanding outcome claims; accounts and
cloud sync should be a separately reviewed feature, not hidden prototype behavior.

For a presentation script, interview answers and resume wording, see
[docs/PORTFOLIO.md](docs/PORTFOLIO.md). Verification records distinguish completed
checks from public-hosting and identity guarantees that have not been established.
