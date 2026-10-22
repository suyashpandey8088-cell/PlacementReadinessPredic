"""Synthetic data generation and strict schema validation for the learning lab."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from src.config import SEED

NUMERIC = ["cgpa", "coding_practice", "dsa_rating", "project_quality", "aptitude", "communication"]
CATEGORICAL = ["internship"]
FEATURES = NUMERIC + CATEGORICAL
TARGET = "simulated_outcome"
RANGES = {"cgpa": (0, 10), "coding_practice": (0, 500), "dsa_rating": (1, 5),
          "project_quality": (1, 5), "aptitude": (0, 100), "communication": (1, 5)}


def generate_synthetic(n=1400, seed=SEED):
    """Simulated interview exercise outcome, NOT recorded hiring outcomes.

    Shared latent preparation induces plausible correlations; Bernoulli noise
    prevents a deterministic score-to-label mapping. No names or identifiers.
    """
    rng = np.random.default_rng(seed)
    latent = rng.normal(0, 1, n)
    rating = lambda offset=0: np.clip(np.rint(3 + .7 * latent + rng.normal(0, 1, n) + offset), 1, 5).astype(int)
    df = pd.DataFrame({
        "cgpa": np.round(np.clip(7 + .65 * latent + rng.normal(0, .9, n), 0, 10), 2),
        "coding_practice": np.clip(rng.gamma(2, 45, n) + latent * 20, 0, 500).astype(int),
        "dsa_rating": rating(), "project_quality": rating(),
        "aptitude": np.round(np.clip(58 + 10 * latent + rng.normal(0, 15, n), 0, 100), 1),
        "communication": rating(), "internship": rng.choice(["none", "completed"], n, p=[.72, .28]),
    })
    logit = (-.25 + .30 * (df.cgpa - 7) + .004 * (df.coding_practice - 90)
             + .55 * (df.dsa_rating - 3) + .45 * (df.project_quality - 3)
             + .018 * (df.aptitude - 58) + .30 * (df.communication - 3)
             + .30 * (df.internship == "completed"))
    df[TARGET] = rng.binomial(1, 1 / (1 + np.exp(-logit)))
    # Realistic missingness in predictors, introduced after label generation.
    for col in ["aptitude", "communication"]:
        df.loc[rng.random(n) < .035, col] = np.nan
    return df


def validate_features(frame):
    if set(frame.columns) != set(FEATURES):
        raise ValueError(f"Expected exactly these feature columns: {', '.join(FEATURES)}. Do not include outcome or future information.")
    out = frame[FEATURES].copy()
    for col, (low, high) in RANGES.items():
        values = pd.to_numeric(out[col], errors="raise")
        if not values.dropna().between(low, high).all():
            raise ValueError(f"{col} must be between {low} and {high}.")
        if col in ("coding_practice", "dsa_rating", "project_quality", "communication") and not (values.dropna() % 1 == 0).all():
            raise ValueError(f"{col} must contain whole numbers or missing values.")
        out[col] = values
    if not out["internship"].dropna().isin(["none", "completed"]).all():
        raise ValueError("internship must be 'none' or 'completed'.")
    return out


def load_dataset(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}. Run python -m src.train_model --generate.")
    df = pd.read_csv(path)
    if TARGET not in df:
        raise ValueError(f"Missing target: {TARGET}. Only use a documented dataset with this schema.")
    if df[TARGET].isna().any() or not df[TARGET].isin([0, 1]).all() or df[TARGET].nunique() != 2:
        raise ValueError("Target must contain both classes 0 and 1 with no missing labels.")
    validate_features(df.drop(columns=TARGET))
    duplicates = int(df.duplicated(subset=FEATURES).sum())
    # Remove repeated predictor rows before splitting to reduce leakage risk.
    df = df.drop_duplicates(subset=FEATURES).reset_index(drop=True)
    if len(df) < 100 or df[TARGET].value_counts().min() < 10:
        raise ValueError("Need at least 100 usable rows and 10 observations in each class for stratified validation.")
    if any(df[c].isna().all() for c in FEATURES):
        raise ValueError("A feature is entirely missing. Supply observed training values.")
    return df, {"usable_observations": len(df), "duplicate_feature_rows_removed": duplicates,
                "missing_values": {k: int(v) for k, v in df.isna().sum().items()},
                "class_distribution": {str(k): int(v) for k, v in df[TARGET].value_counts().sort_index().items()}}


def preprocessor():
    return ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC),
        ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                                  ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), CATEGORICAL),
    ])
