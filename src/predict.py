"""Inference for the separate, explicitly synthetic learning lab only."""
import hashlib
import json
from pathlib import Path
import joblib
import sklearn
from src.config import ROOT
from src.data_preprocessing import FEATURES, validate_features


class ModelError(RuntimeError):
    pass


def load_model(folder=None):
    folder = Path(folder or ROOT / "models")
    try:
        metadata = json.loads((folder / "model_metadata.json").read_text())
        path = folder / "placement_model.joblib"
        if metadata["artifact_version"] != 1 or metadata["features"] != FEATURES or metadata["synthetic"] is not True:
            raise ValueError("Unsupported artifact schema or missing synthetic declaration")
        if metadata["sklearn_version"] != sklearn.__version__:
            raise ValueError("Scikit-learn version changed; regenerate artifacts in this environment")
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["model_sha256"]:
            raise ValueError("Model checksum mismatch")
        # Only load this project's trusted local artifact. Never accept joblib uploads.
        pipeline = joblib.load(path)
        if list(pipeline.feature_names_in_) != FEATURES:
            raise ValueError("Pipeline feature schema mismatch")
        return pipeline, metadata
    except Exception as exc:
        raise ModelError("Learning-lab model is missing or incompatible. Run `python -m src.train_model --generate` in your active environment. Readiness assessments still work.") from exc


def predict_simulated(frame, pipeline):
    clean = validate_features(frame)
    if clean.empty:
        raise ValueError("Provide at least one observation.")
    return pipeline.predict(clean)
