# Student presentation and learning guide

The deployed web version uses Vite + Flask and browser-local history. The original
Streamlit app remains a local alternative. The scoring and synthetic ML workflow
are shared between both interfaces.

## Three-to-five-minute demonstration (about four minutes)

**0:00–0:35 · Problem and honesty**
“Students often know they need to prepare, but not what to do next. Path2Placement
turns an honest snapshot into a manageable plan. This is a preparation score, not
a probability of getting a job. I deliberately separate scoring from ML.”
Show Overview. Explain the five categories and the absence of invented history.

**0:35–1:35 · Assessment**
Open an assessment. Use a mixed profile: CGPA 7.5, DSA 2, one completed project,
zero demos, quality 2, communication 4 and resume 2. Keep project documentation
at zero; leave optional mock/reasoning blank. Advance with section buttons,
briefly demonstrate going back, then review and calculate.
Explain that self-ratings are subjective and a working project matters more than counts.

**1:35–2:25 · Results and coaching**
Show the exact score and readiness band, category bar chart and top priorities.
Open How this score works: category weights sum to 100%, counts are capped,
and blank optional inputs are excluded within their category.
Open the plan and show one measurable completion criterion. Download the plan.
“This result comes from deterministic rules, not an LLM.”

**2:25–3:05 · Persistence**
Save. Show My progress. Update a relevant skill only if you have evidence (or
explicitly call it a demonstration input), save another assessment and show the
category change. Export CSV. Open Privacy & data. Download a private JSON backup, demonstrate confirmed
deletion and restore. Explain that browser-local history is not account-based
cloud synchronization.
Use a dedicated demonstration workspace; never pretend demo records belong to a real student.

**3:05–4:00 · ML and engineering**
Open Model insights. “These 1,400 rows and labels are simulated.” Show three
candidate CV F1 scores, selected Logistic Regression and held-out confusion matrix.
Explain that imputation/scaling happens inside folds, and the holdout does not
select the winner. Run illustrative inference. Close with tests, limitations and
future validation on a properly licensed real dataset.

If time remains, show `python -m pytest -q` and open `src/readiness_scoring.py`.
Never describe simulated metrics as actual placement accuracy.

## Resume-ready description

**Path2Placement | Python, Flask, JavaScript, Vite, Scikit-learn, Vercel**
- Built an explainable five-category placement-readiness self-assessment with
  validated inputs, prioritized rule-based coaching and a measurable seven-day plan.
- Shipped a responsive Vercel web app with browser-local history, category/trend
  visualization, CSV export, validated JSON backup/restore and Python/API/UI tests.
- Developed a reproducible synthetic ML learning lab comparing Logistic Regression,
  Decision Tree and Random Forest with leakage-safe pipelines, stratified CV and
  held-out evaluation; documented why simulated results are not hiring forecasts.

Mention test counts only after running them yourself. Do not write “predicts
placement with 72.5% accuracy”; that would misrepresent this project.

## Interview questions and suggested answers

**1. Is the readiness score a machine-learning model?**
No. It is a versioned weighted scoring formula. The separate learning lab trains
classifiers on simulated exercise outcomes. The UI distinguishes both systems.

**2. Why not show a placement probability?**
We lack representative, appropriately licensed real hiring outcomes and external
validation. A confident-looking number would imply evidence we do not have.

**3. How do you normalize different scales?**
CGPA × 10; percentages unchanged; ratings `(x-1)/4*100`; counts divided by a
specified cap and clipped. Category averages are combined with documented weights.

**4. What happens when a mock score is missing?**
Its weight is excluded within Interview & resume and the remaining category weights
are rescaled. This avoids inventing a test score but reduces comparability with
complete assessments, so the UI explicitly flags it.

**5. How do you prevent target leakage?**
Predictors are an exact allowed schema without the target or future outcomes.
Deduplication precedes splitting. Imputation, encoding and scaling fit inside each
training CV fold, never on the full dataset or holdout.

**6. Why Logistic Regression?**
It had the highest mean five-fold F1 on the training partition with the committed
seed and data. The data-generating process is itself logistic, so this is unsurprising
and is not proof it will outperform other models on genuine hiring data.

**7. Why F1 rather than accuracy alone?**
F1 balances precision and recall. Accuracy can conceal minority-class failures.
The app also shows class counts and the confusion matrix. In a real application,
error costs, calibration, thresholds and subgroup performance need separate review.

**8. Why use Pipeline and ColumnTransformer?**
They keep preprocessing together with the classifier. CV clones the entire pipeline
so validation rows do not influence imputation or scaling. Inference uses the exact
same fitted transformations as training.

**9. What is the difference between training and inference?**
Training learns parameters from labeled examples and writes artifacts. Inference
loads the trusted fitted pipeline and classifies new schema-validated rows. Streamlit
reruns never train a model.

**10. How is saved history isolated?**
The Vercel web app has no student-record database: explicitly saved history belongs
to a browser profile and origin. Another browser profile starts empty, but someone
sharing the same profile can read it. It is not authenticated or encrypted storage.
The separate local Streamlit version uses SQLite scoped by a hashed workspace key.

**11. How are recommendations generated?**
Deterministic rules inspect actual low ratings/counts/test results and category gaps.
They produce a reason, task and measurable criterion, then sort by affected category
score. No external LLM, paid API or nondeterministic text is used.

**12. What are the biggest limitations?**
Subjective ratings, design-choice weights, incomplete optional tests, unequal
opportunities, simulated labels, no external validity and prototype history security.
The system must not be used to rank students or make employment decisions.

**13. What would you improve first?**
User testing and short objective quizzes, then responsibly sourced real data if
outcome modeling is needed. Before public institutional deployment, implement
proper authentication, authorization, storage retention and backup policies.

**14. How would you debug a bad score?**
Reproduce the exact inputs/version, call `validate_inputs`, inspect normalized
features and category contributions, check missing coverage/caps, then add a
regression test. Avoid changing weights just to make a desired answer appear.

## Seven practical implementation days

1. Environment, source/permission review, data card, input schema and scoring design.
2. Normalize/validate inputs, implement scoring, test low/high/mixed/missing values.
3. Generate documented simulated data, leakage-safe training, CV and artifact metadata.
4. Build assessment/review/results and deterministic recommendations.
5. Add workspace-isolated history, CSV, charts and restrained visual system.
6. Run unit/integration/browser checks; fix rerun, persistence and responsive issues.
7. Finish documentation, rehearse demo, push GitHub branch and verify hosting if chosen.

This is a learning schedule, not a guarantee. Read and reproduce one module at a time.

## Suggested learning exercises

- Change one weight in configuration, keeping the sum at one; observe score changes
  and update the scoring version, documentation and tests before using saved comparisons.
- Test how filling a missing optional test changes the score without changing other inputs.
- Add an honest deterministic rule and test that its trigger changes the recommendation.
- Inspect false positives/negatives on the synthetic holdout and explain why neither
  should be interpreted as a real student's employment outcome.
- Replace the synthetic generator only after a documented source/permission/leakage
  review; never silently remove the synthetic warnings.

## Known limitations and future work

- No genuine placement classifier or real hiring probability.
- No objective skill examination or longitudinal validation of the readiness rubric.
- No accounts, email recovery, encryption at rest, rate limiting or managed backups.
- Hosted SQLite persistence depends on the host; no CSV import or cross-device sync.
- Rerun state is temporary until saved; unsent form edits are not persisted.
- Rules target broad engineering preparation, not a company-specific role.
- Independent synthetic rows do not model temporal, institutional or social structure.
- Model metrics describe one reproducible synthetic split; external validity is absent.
- Future: validated quizzes, role tracks, accessibility/user studies, better feedback,
  consented representative data with grouped/temporal splits and fairness evaluation.
