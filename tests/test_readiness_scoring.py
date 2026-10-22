import pytest
from src.config import FIELDS, CATEGORY_FIELDS, CATEGORY_WEIGHTS
from src.readiness_scoring import assess, category_scores, normalize, readiness_band, ValidationError


def test_configuration():
    assert sum(CATEGORY_WEIGHTS.values()) == pytest.approx(1)
    assert all(sum(w.values()) == pytest.approx(1) for w in CATEGORY_FIELDS.values())
    assert {k for weights in CATEGORY_FIELDS.values() for k in weights} == set(FIELDS)


def test_strong_and_weak_boundaries(inputs):
    strong = {k: v[2] for k, v in FIELDS.items()}
    weak = {k: v[1] for k, v in FIELDS.items()}
    assert assess(strong)["score"] == 100
    assert assess(weak)["score"] == 0
    assert assess(strong)["band"] == "Strong Preparation"
    assert assess(weak)["band"] == "Foundation Building"


def test_reproducible_weighted_score(inputs):
    result = assess(inputs)
    assert result == assess(inputs)
    expected = round(sum(category_scores(inputs)[k] * w for k, w in CATEGORY_WEIGHTS.items()), 2)
    assert result["score"] == expected
    assert all(0 <= v <= 100 for v in result["categories"].values())


def test_optional_missing(inputs):
    result = assess(inputs)
    assert result["missing_optional"] == ["reasoning", "mock"]
    assert result["categories"]["Interview & resume"] == 25
    inputs["mock"] = 100
    assert assess(inputs)["categories"]["Interview & resume"] == 43.75


@pytest.mark.parametrize("field,value", [("cgpa", -1), ("cgpa", 11), ("dsa", 0), ("dsa", 6), ("dsa", 2.4), ("aptitude", 101), ("mock", float("nan")), ("resume", True), ("core", "3"), ("cgpa", float("inf"))])
def test_invalid(inputs, field, value):
    inputs[field] = value
    with pytest.raises(ValidationError):
        assess(inputs)


def test_required_missing(inputs):
    inputs.pop("cgpa")
    with pytest.raises(ValidationError, match="please enter"):
        assess(inputs)


@pytest.mark.parametrize("cgpa", [0, 10])
def test_cgpa_edges(inputs, cgpa):
    inputs["cgpa"] = cgpa
    assert 0 <= assess(inputs)["score"] <= 100


def test_relations(inputs):
    inputs["demos"] = 2
    with pytest.raises(ValidationError, match="cannot exceed"):
        assess(inputs)
    inputs.update(projects=0, demos=0, quality=2)
    with pytest.raises(ValidationError, match="no completed projects"):
        assess(inputs)
    inputs.update(quality=1, languages=0)
    with pytest.raises(ValidationError, match="no programming languages"):
        assess(inputs)


def test_caps_and_ratings():
    assert normalize("projects", 3) == normalize("projects", 100)
    assert normalize("problems", 250) == normalize("problems", 50000)
    assert normalize("dsa", 1) == 0
    assert normalize("dsa", 5) == 100


@pytest.mark.parametrize("score,band", [(39.99,"Foundation Building"), (40,"Developing"), (60,"Progressing Toward Readiness"), (75,"Nearly Ready"), (90,"Strong Preparation"), (100,"Strong Preparation")])
def test_bands(score, band):
    assert readiness_band(score) == band


def test_random_valid_scores():
    import random
    rng = random.Random(42)
    for _ in range(100):
        sample = {k: rng.uniform(v[1], v[2]) if isinstance(v[1], float) else rng.randint(v[1], v[2]) for k, v in FIELDS.items()}
        sample["demos"] = min(sample["demos"], sample["projects"])
        sample["documented"] = min(sample["documented"], sample["projects"])
        if sample["projects"] == 0:
            sample["quality"] = 1
        if sample["languages"] == 0:
            sample["programming"] = 1
        assert 0 <= assess(sample)["score"] <= 100


def test_independent_category():
    from src.readiness_scoring import score_category
    assert score_category("Academic preparation", {"cgpa": 10, "consistency": 5, "core": 5}) == 100
