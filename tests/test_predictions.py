import json
import numpy as np
import pytest
from src.data_preprocessing import FEATURES, generate_synthetic
from src.predict import load_model, predict_simulated, ModelError
from src.train_model import train


def test_committed_model_inference():
    pipeline, meta = load_model()
    frame = generate_synthetic(12)[FEATURES]
    pred = predict_simulated(frame, pipeline)
    assert len(pred) == 12 and set(pred) <= {0, 1}
    assert np.array_equal(pred, predict_simulated(frame[FEATURES[::-1]], pipeline))
    assert meta["synthetic"] is True
    assert sum(sum(row) for row in meta["test_metrics"]["confusion_matrix"]) == meta["test_rows"]


def test_missing_model(tmp_path):
    with pytest.raises(ModelError, match="Readiness assessments still work"):
        load_model(tmp_path)


def test_corrupt_and_incompatible_artifacts(tmp_path):
    from src.config import ROOT
    import shutil
    for file in (ROOT / "models").iterdir():
        shutil.copy(file, tmp_path)
    metadata_path = tmp_path / "model_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["features"] = ["leaked_target"]
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ModelError):
        load_model(tmp_path)


def test_checksum_failure(tmp_path):
    from src.config import ROOT
    import shutil
    shutil.copy(ROOT / "models/model_metadata.json", tmp_path)
    (tmp_path / "placement_model.joblib").write_bytes(b"untrusted")
    with pytest.raises(ModelError):
        load_model(tmp_path)


def test_reproducible_training(tmp_path):
    path = tmp_path / "synthetic.csv"
    generate_synthetic(300).to_csv(path, index=False)
    first = train(path, tmp_path / "first")
    second = train(path, tmp_path / "second")
    assert first["comparison"] == second["comparison"]
    assert first["test_metrics"] == second["test_metrics"]
    assert len(first["comparison"]) == 3
    assert all(len(r["cv_folds"]) == 5 for r in first["comparison"])
