# Verification record

Date: 2026-10-22 UTC. Environment: Linux, Python 3.11.2; pinned dependencies in
`requirements.txt`. These checks were actually executed in the development sandbox.
No public hosting deployment is claimed.

## Automated checks

- `python -m pytest -q`: **53 passed** on the final feature set.
- `python -m compileall -q app.py src tests`: passed.
- `python -m pip check`: no broken requirements.
- `python -m src.train_model --generate`: generated 1,400 explicitly synthetic rows,
  trained three candidates, selected Logistic Regression by training CV F1, saved
  pipeline/metadata and generated `reports/model_evaluation.md`.
- Training reproducibility test retrained all three candidates twice on a smaller
  seeded synthetic dataset and verified identical CV results/holdout metrics.

Test coverage by scenario:

| Scenario | Evidence |
|---|---|
| Strong, weak, mixed and random valid profiles | boundary tests, reproducibility and 100 seeded input profiles |
| Missing optional values | category weight-rescaling tests and UI assessment flow |
| Invalid ranges/types/nonfinite inputs | parameterized scoring/schema tests |
| CGPA 0 and 10 | explicit boundary tests |
| Consistency errors | demos > completed, no projects with high quality, no languages with high proficiency |
| Independent category scoring | category-only academic input test |
| Repeated save and repeated assessments | idempotent save test and full Streamlit integration flow |
| Empty history, isolation and clear | separate workspace keys, recovery by key, scoped deletion |
| Missing dataset and invalid labels | preprocessing recovery/error tests |
| Missing/incompatible/corrupted model | artifact schema, missing file and checksum tests |
| Unavailable database | directory-as-database test; home still usable with warning |
| CSV export | round-trip Pandas CSV parsing, preserved inputs and category scores |
| Correct inference schema | saved pipeline inference, reordered columns, unknown feature rejection |
| Changing relevant recommendations | DSA trigger and strong-profile maintenance tests |
| All major pages | Streamlit AppTest executes home, form, review, results, progress, model insights and about |
| Form preservation and section validation | forward/backward answer retention; invalid section remains editable |

## Running server and scripted Chromium checks

Started the actual app with:

```bash
.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

`GET /_stcore/health` returned `ok`. The server was exposed as a development live
preview; this is not a durable hosted release.

A temporary Playwright script used Chromium installed from npm tooling (not a runtime
app dependency). Browser setup initially lacked system NSS/NSPR libraries; bundled
Chromium libraries were extracted for the browser-only test environment. No browser
libraries or tooling are committed as core dependencies.

Successful scripted checks against the actual server:

1. Opened Overview at **1440 × 1000**; navigated to the five-section form.
2. Submitted each section, opened review and calculated default-input demo results.
3. Waited for the actual Plotly chart to mount and inspected the category bars.
4. Saved an assessment; opened genuine saved history.
5. Clicked Export; browser emitted an actual download named
   `path2placement-history.csv`.
6. Opened Model insights; inspected CV/held-out displays, confusion matrix,
   class distribution and permutation importance.
7. Ran saved-pipeline illustrative inference and observed the explicit
   “Simulated exercise class … not an employment forecast” output.
8. Opened About and inspected methodology expanders and privacy text.
9. Opened a fresh **390 × 844** mobile context. Native navigation collapsed;
   completed the entire assessment and rendered results. Horizontal-overflow check
   returned **false**. Browser JavaScript page-error collection returned **[]**.

Screenshots from the actual running app were visually reviewed for all seven pages
and for mobile assessment/results. Review led to moving the wordmark into native
Streamlit branding, using auto-collapsed mobile navigation, adding mobile header
spacing and waiting for charts rather than capturing loading skeletons. Selected
screenshots in `docs/screenshots/` show demonstration inputs, not real students.

## Deliberate non-claims

- Synthetic evaluation does **not** establish real hiring accuracy, calibration or fairness.
- No real dataset provenance/permission was established, so no real outcome model is shown.
- No institutional deployment, identity authentication, production backup, public-host
  persistence, external integration or accessibility certification was verified.
- Browser checks are scripted plus visual screenshot review, not a formal user study.
- GitHub Actions configuration is included; its remote status must be checked after push.
