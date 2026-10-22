# Synthetic learning-lab evaluation

> Not a placement predictor. No real-world accuracy claim.

Generated at: 2026-10-22T04:39:22.555389+00:00
Seed: 42. Usable rows: 1400. Train: 1120. Held out: 280.

## Selection: five-fold stratified CV on training rows only

| Model | CV F1 mean | CV standard deviation |
|---|---:|---:|
| Logistic Regression | 0.6976 | 0.0372 |
| Decision Tree | 0.6046 | 0.0362 |
| Random Forest | 0.6621 | 0.0330 |

Selected **Logistic Regression** by highest mean CV F1. No hyperparameter search; conservative fixed settings keep this small workflow understandable.

## Selected model: untouched holdout

- Accuracy: 0.7250
- Precision: 0.6984
- Recall: 0.6929
- F1: 0.6957
- Confusion matrix (rows actual 0/1, columns predicted 0/1): `[[115, 38], [39, 88]]`

A false positive predicts a simulated pass for a simulated failure. A false negative misses a simulated pass. Neither is evidence about an actual student getting hired.

## Data audit

```json
{
  "usable_observations": 1400,
  "duplicate_feature_rows_removed": 0,
  "missing_values": {
    "cgpa": 0,
    "coding_practice": 0,
    "dsa_rating": 0,
    "project_quality": 0,
    "aptitude": 46,
    "communication": 54,
    "internship": 0,
    "simulated_outcome": 0
  },
  "class_distribution": {
    "0": 763,
    "1": 637
  }
}
```

## Limitations

- All labels are simulated, not genuine placement outcomes.
- Metrics only measure recovery of an invented relationship; they do not establish real-world accuracy.
- No temporal, geographic or institutional external validation.
- Permutation importance is not causation; correlated features can share importance.
- A future real dataset needs a provenance, consent/licensing and leakage review, plus subgroup and calibration evaluation.
