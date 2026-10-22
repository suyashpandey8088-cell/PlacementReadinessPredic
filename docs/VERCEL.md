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
| Cross-device automatic sync | No | Optional, account-scoped |
| Accounts | No | Optional (Supabase Auth) |

On a shared device, another person with the same browser profile can read local
history. There is no login/encryption guarantee. JSON backup restore recomputes
scores and recommendations using current scoring criteria and preserves source
assessment IDs/timestamps. Duplicate IDs are skipped. It does not imply that
imported assessment timestamps were independently verified. Checklist ticks are
browser conveniences, not externally assessed achievements; they are not part of
assessment backup files.

Guest data never leaves the browser. Account data is only written after an explicit
save by a signed-in user; see [Account tables](#account-tables) and the security model
below.

### Accounts (optional)

Credentials live in Supabase Auth; the app never sees passwords. The Flask API issues
its own opaque session token (`secrets.token_urlsafe(32)`) in a `Secure`, `HttpOnly`,
`SameSite=Lax` cookie — `__Host-p2p_session` on HTTPS, `p2p_session` on localhost because
browsers reject `__Host-` cookies without TLS. Only a SHA-256 hash of the token is stored.
Sessions last 30 days and are deleted on sign-out; a password change removes every other
session for that user.

Every account-table query is filtered by the authenticated `user_id` from the session
cookie — never by a client-supplied ID. The four `p2p_*` tables have RLS enabled with
no policies, and `anon`/`authenticated` privileges are revoked, so the browser cannot
read them directly even if it obtained the publishable key.

| Endpoint | Auth | Behaviour |
|---|---|---|
| `GET /api/auth/me` | cookie optional | `{available, user}`; clears an invalid cookie |
| `POST /api/auth/signup` | none (rate-limited) | creates a confirmed Supabase user, profile and session |
| `POST /api/auth/login` | none (rate-limited) | password grant, then app session |
| `POST /api/auth/logout` | cookie | deletes the session row and clears the cookie |
| `POST /api/auth/password` | required | verifies the current password, updates it, revokes other sessions |
| `GET /api/history` | required | saved assessments for the session user (invalid stored records are skipped and counted) |
| `POST /api/history` | required | validates inputs, recomputes score/plan server-side, enforces the 200 cap |
| `DELETE /api/history/<id>` | required | deletes one record scoped to the user |
| `POST /api/history/import` | required | recomputes each backup record, skips duplicates, reports counts |
| `DELETE /api/account/data` | required | removes profile, sessions and assessments; keeps the shared login identity |

Rate limits are stored as HMAC-SHA-256 hashes of email/IP in `p2p_auth_attempts`
(8 failures per email per 15 min, 30 per IP, 5 sign-ups per IP per hour), so raw
addresses and emails are not duplicated there. CSRF is blocked by an Origin /
`Sec-Fetch-Site` check on every state-changing request.

Email confirmation is disabled on this shared Supabase project (its mailer is
rate-limited and unsuited to a demo), so accounts are created with
`email_confirm: true`. That means **email ownership is not verified and password reset
is unavailable in-app**; the UI says so rather than implying a full identity system.

### Account tables

Created as migration `path2placement_account_tables` in the existing shared Supabase
project. No pre-existing table was altered.

```sql
create table public.p2p_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  created_at timestamptz not null default now()
);
create unique index p2p_profiles_email_key on public.p2p_profiles (lower(email));

create table public.p2p_sessions (
  token_hash text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);
create index p2p_sessions_user_idx on public.p2p_sessions (user_id);

create table public.p2p_assessments (
  id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  record jsonb not null,
  created_at timestamptz not null default now(),
  primary key (user_id, id)
);

create table public.p2p_auth_attempts (
  key_hash text primary key,
  attempts integer not null default 0 check (attempts >= 0),
  window_started_at timestamptz not null default now()
);

alter table public.p2p_profiles enable row level security;
alter table public.p2p_sessions enable row level security;
alter table public.p2p_assessments enable row level security;
alter table public.p2p_auth_attempts enable row level security;
-- no policies: only the server-side service key may read or write
```

`SUPABASE_SECRET_KEY` bypasses RLS, so it is set as a Vercel environment variable for
all targets and is never sent to the browser. The publishable key is only used by the
API for the password-grant call.

## Deployment settings

- Existing project: `placement-readiness-predic`.
- Framework: Vite; root is repository root.
- Install `npm ci`; build `npm run build`; output `dist`.
- `api/index.py` is the Flask/WSGI function; `/api/*` rewrites to it.
- Account environment variables (all targets, optional):
  `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`.
  Without them the deployment runs guest-only and `/api/auth/me` returns
  `{"available": false, "user": null}`.
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

### Disposable smoke-test account

The live smoke workflow signs in with `p2p-smoke@example.com` so the real sign-in,
account save, cross-session isolation and deletion paths run on every push that
touches the workflow or the browser test. The account holds no personal data and its
Path2Placement rows are deleted at the end of each run; the shared Supabase Auth
identity remains. Remove that identity from Supabase → Authentication → Users if you
no longer want it, and delete the `P2P_SMOKE_*` environment variables from the
workflow to skip the block entirely. Failed runs report a one-line check annotation
(taken from `.cache/smoke-error.txt`) instead of relying on downloadable logs.

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
