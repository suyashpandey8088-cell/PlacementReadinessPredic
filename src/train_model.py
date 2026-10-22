"""Run: python -m src.train_model --generate. No training on Streamlit reruns."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import joblib
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from src.config import ROOT, SEED
from src.data_preprocessing import generate_synthetic, load_dataset, preprocessor, FEATURES, TARGET
from src.evaluation import evaluate


def train(data_path, output_dir, report_path=None):
    df, audit = load_dataset(data_path)
    x, y = df[FEATURES], df[TARGET]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=.2, stratify=y, random_state=SEED)
    candidates = {
        "Logistic Regression": LogisticRegression(max_iter=1500, random_state=SEED),
        "Decision Tree": DecisionTreeClassifier(max_depth=5, min_samples_leaf=12, random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=160, max_depth=7, min_samples_leaf=6, random_state=SEED, n_jobs=1),
    }
    pipelines, comparison = {}, []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for name, classifier in candidates.items():
        pipeline = Pipeline([("preprocess", preprocessor()), ("classifier", classifier)])
        scores = cross_val_score(pipeline, x_train, y_train, cv=cv, scoring="f1")
        comparison.append({"model": name, "cv_f1_mean": float(scores.mean()), "cv_f1_std": float(scores.std()), "cv_folds": scores.tolist()})
        pipelines[name] = pipeline
    # Selection uses CV on the training partition, never the holdout.
    selected = max(comparison, key=lambda row: row["cv_f1_mean"])["model"]
    pipeline = pipelines[selected].fit(x_train, y_train)
    test_metrics = evaluate(pipeline, x_test, y_test)
    importance = permutation_importance(pipeline, x_test, y_test, scoring="f1", n_repeats=8, random_state=SEED)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "placement_model.joblib"
    joblib.dump(pipeline, model_path, compress=3)
    metadata = {
        "artifact_version": 1, "model_name": selected, "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__, "seed": SEED, "synthetic": True,
        "dataset": "Path2Placement synthetic v1; generated with NumPy, seed 42. No real students or hiring records.",
        "dataset_sha256": hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "features": FEATURES, "target": TARGET, "target_definition": "A simulated interview-exercise outcome sampled from a documented logistic relationship; 1 = simulated pass.",
        "audit": audit, "training_rows": len(x_train), "test_rows": len(x_test),
        "comparison": comparison, "test_metrics": test_metrics,
        "permutation_importance": [{"feature": f, "mean": float(m), "std": float(s)} for f, m, s in zip(FEATURES, importance.importances_mean, importance.importances_std)],
        "limitations": ["All labels are simulated, not genuine placement outcomes.", "Metrics only measure recovery of an invented relationship; they do not establish real-world accuracy.",
                        "No temporal, geographic or institutional external validation.", "Permutation importance is not causation; correlated features can share importance.",
                        "A future real dataset needs a provenance, consent/licensing and leakage review, plus subgroup and calibration evaluation."],
    }
    (output_dir / "model_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if report_path:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Synthetic learning-lab evaluation", "", "> Not a placement predictor. No real-world accuracy claim.", "",
                 f"Generated at: {metadata['trained_at_utc']}", f"Seed: {SEED}. Usable rows: {len(df)}. Train: {len(x_train)}. Held out: {len(x_test)}.",
                 "", "## Selection: five-fold stratified CV on training rows only", "", "| Model | CV F1 mean | CV standard deviation |", "|---|---:|---:|"]
        lines += [f"| {r['model']} | {r['cv_f1_mean']:.4f} | {r['cv_f1_std']:.4f} |" for r in comparison]
        lines += ["", f"Selected **{selected}** by highest mean CV F1. No hyperparameter search; conservative fixed settings keep this small workflow understandable.",
                  "", "## Selected model: untouched holdout", ""]
        lines += [f"- {k.title()}: {v:.4f}" for k, v in test_metrics.items() if k != "confusion_matrix"]
        lines += [f"- Confusion matrix (rows actual 0/1, columns predicted 0/1): `{test_metrics['confusion_matrix']}`", "",
                  "A false positive predicts a simulated pass for a simulated failure. A false negative misses a simulated pass. Neither is evidence about an actual student getting hired.",
                  "", "## Data audit", "", "```json", json.dumps(audit, indent=2), "```", "",
                  "## Limitations", ""] + [f"- {x}" for x in metadata["limitations"]]
        report_path.write_text("\n".join(lines) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true", help="Regenerate the explicitly synthetic dataset")
    parser.add_argument("--data", type=Path, default=ROOT / "data/student_placement.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "models")
    args = parser.parse_args()
    if args.generate:
        args.data.parent.mkdir(parents=True, exist_ok=True)
        generate_synthetic().to_csv(args.data, index=False)
    try:
        metadata = train(args.data, args.output, ROOT / "reports/model_evaluation.md")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Training failed: {exc}\n")
    print(json.dumps({"selected": metadata["model_name"], "held_out": metadata["test_metrics"]}, indent=2))


if __name__ == "__main__":
    main()
