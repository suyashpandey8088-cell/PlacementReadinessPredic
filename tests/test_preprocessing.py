import pandas as pd
import pytest
from src.data_preprocessing import generate_synthetic, load_dataset, FEATURES, TARGET, validate_features


def test_generation_reproducible():
    a, b = generate_synthetic(), generate_synthetic()
    pd.testing.assert_frame_equal(a, b)
    assert set(a[TARGET]) == {0, 1}
    assert 0 < a["aptitude"].isna().sum() < 150
    validate_features(a[FEATURES])


def test_load_audit_and_duplicate_removal(tmp_path):
    df = generate_synthetic(200)
    df = pd.concat([df, df.iloc[:1]], ignore_index=True)
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)
    result, audit = load_dataset(path)
    assert len(result) == 200
    assert audit["duplicate_feature_rows_removed"] == 1


def test_missing_dataset(tmp_path):
    with pytest.raises(FileNotFoundError, match="--generate"):
        load_dataset(tmp_path / "missing.csv")


def test_wrong_features_and_ranges():
    df = generate_synthetic(200)[FEATURES]
    with pytest.raises(ValueError, match="exactly"):
        validate_features(df.assign(salary=123))
    df.loc[0, "cgpa"] = 12
    with pytest.raises(ValueError, match="cgpa"):
        validate_features(df)


def test_invalid_target_and_all_missing(tmp_path):
    path = tmp_path / "data.csv"
    df = generate_synthetic(200)
    df[TARGET] = 1
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="both classes"):
        load_dataset(path)
    df = generate_synthetic(200)
    df["aptitude"] = float("nan")
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="entirely missing"):
        load_dataset(path)
