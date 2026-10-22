# Data card: explicitly synthetic educational data

## Why the fallback is used

The starting repository contained no dataset, provenance record, license, or genuine
placement outcomes. No external real-student dataset was verified for appropriate
permissions and representative use during this build. Instead of implying that an
unverified CSV establishes employability, this project uses the requested synthetic
fallback. **There are no genuine hiring outcomes in this repository.**

`student_placement.csv` is an unfortunately conventional filename, not a claim of
real placements. It contains **1,400 simulated observations**, generated entirely by
`src/data_preprocessing.py::generate_synthetic`, with NumPy's generator, seed 42.
No external dataset was downloaded or combined. There is no external dataset
attribution or third-party dataset license to assert. Reuse of project-created
code and synthetic data follows the repository owner's licensing decisions; no
open-source license has been granted by this implementation on the owner's behalf.
Dependencies retain their own licenses.

## Schema

| Feature | Meaning in this simulation | Range / values |
|---|---|---|
| cgpa | Simulated academic score | 0–10 |
| coding_practice | Simulated understood coding-problem count | integer 0–500 |
| dsa_rating | Simulated subjective skill rating | integer 1–5 |
| project_quality | Simulated practical implementation rating | integer 1–5 |
| aptitude | Simulated practice-test percentage | 0–100; missing allowed |
| communication | Simulated subjective communication rating | 1–5; missing allowed |
| internship | Simulated completed experience | `none`, `completed` |
| simulated_outcome | Simulated interview-exercise pass, **not placement** | 0 = fail, 1 = pass |

All predictors would conceptually be known before an interview exercise. No salary,
final hiring status, offer date or future feature is included. `simulated_outcome`
is excluded from predictors and checked separately.

## Exact generation recipe

For each row, draw latent preparation `z ~ Normal(0,1)`:

- CGPA: clip `7 + 0.65*z + Normal(0,0.9)` to [0,10], round to two decimals.
- Coding practice: clip `Gamma(shape=2, scale=45) + 20*z` to [0,500], cast to integer.
- Each 1–5 rating: clip rounded `3 + 0.7*z + Normal(0,1)` to [1,5]; independent noise per rating.
- Aptitude: clip `58 + 10*z + Normal(0,15)` to [0,100], round to one decimal.
- Internship: `none` with probability .72, `completed` with probability .28.

Compute:

```text
logit = -0.25 + 0.30*(cgpa-7) + 0.004*(coding_practice-90)
        + 0.55*(dsa_rating-3) + 0.45*(project_quality-3)
        + 0.018*(aptitude-58) + 0.30*(communication-3)
        + 0.30*I(internship == completed)
p = 1 / (1 + exp(-logit))
simulated_outcome ~ Bernoulli(p)
```

This `p` is a **data-generation parameter**, never a user's placement probability.
After labeling, approximately 3.5% of aptitude and communication values are set
missing independently. Random draw order is defined by the generator source.
Labels are related to features but noisy, not arbitrary random labels or exact
thresholds from the readiness formula.

## Audit and limitations

The actual row counts, missing counts, class distribution and duplicate audit are
recorded in `models/model_metadata.json` and `reports/model_evaluation.md`. The
initial generated dataset has 1,400 usable rows, no repeated predictor rows and
both target classes. Missing values are imputed inside training folds, not globally.
Repeated predictor rows are removed before splitting; both classes and sufficient
samples are required. All-missing features, out-of-range values and schema errors
are rejected.

Distributions and coefficients are author-selected assumptions. They do not model
employer preferences, economic conditions, institution, region, disability,
opportunity differences, fairness or actual placement outcomes. Apparent importance
mostly reflects the generator. Metrics assess recovery of invented relationships,
not real-world predictive accuracy. Self-ratings are not objective measurements.

## Regenerate

```bash
python -m src.train_model --generate
```

This replaces the dataset and model artifacts. Omitting `--generate` trains on the
existing schema-validated CSV. Replacing the CSV is not enough to justify a real
outcome model: first establish source, permission, sampling, feature availability,
target definition, temporal/group split strategy, external validation and bias
analysis. Change the metadata and product labeling only after that review; the
current loader intentionally requires the synthetic declaration.
