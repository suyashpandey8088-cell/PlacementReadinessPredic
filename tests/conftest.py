import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import FIELDS


@pytest.fixture
def inputs():
    return {k: v[3] for k, v in FIELDS.items()}
