import secrets
import pandas as pd
import pytest
from src.database import HistoryStore, HistoryError, export_csv
from src.readiness_scoring import assess
from src.recommendations import recommend


def test_save_repeat_restore_isolation_delete_export(tmp_path, inputs):
    db = HistoryStore(tmp_path / "history.sqlite3")
    a, b = secrets.token_hex(32), secrets.token_hex(32)
    assert db.list(a) == []
    result = assess(inputs)
    identifier = db.save(a, result, recommend(inputs))
    db.save(a, result, [], identifier)
    assert len(db.list(a)) == 1
    assert db.list(b) == []
    db.save(b, result, [])
    db.save(a, result, [])
    restored = HistoryStore(tmp_path / "history.sqlite3").list(a)
    assert len(restored) == 2
    assert restored[0]["inputs"] == result["inputs"]
    from io import StringIO
    csv = pd.read_csv(StringIO(export_csv(restored)))
    assert len(csv) == 2
    assert csv.iloc[0]["score"] == result["score"]
    assert "cgpa" in csv.columns and "score_Programming & DSA" in csv.columns
    db.clear(a)
    assert db.list(a) == []
    assert len(db.list(b)) == 1
    assert export_csv([]).startswith("assessment_id,")


def test_unavailable_database(tmp_path):
    with pytest.raises(HistoryError, match="Cannot access"):
        HistoryStore(tmp_path)  # A directory is not a database file.


@pytest.mark.parametrize("key", ["x' OR 1=1 --", "short", "a"*63, "g"*64])
def test_reject_invalid_keys(tmp_path, key):
    with pytest.raises(HistoryError):
        HistoryStore(tmp_path / "db.sqlite3").list(key)
