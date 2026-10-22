from src.config import FIELDS
from src.recommendations import recommend, seven_day_plan


def test_recommendations_change(inputs):
    inputs["dsa"] = 1
    assert any(a["field"] == "dsa" for a in recommend(inputs))
    inputs["dsa"] = 5
    assert not any(a["field"] == "dsa" for a in recommend(inputs))


def test_deterministic_prioritized_no_duplicates(inputs):
    from src.readiness_scoring import assess
    actions = recommend(inputs)
    assert actions == recommend(inputs)
    assert len({a["title"] for a in actions}) == len(actions)
    scores = assess(inputs)["categories"]
    assert [scores[a["category"]] for a in actions] == sorted(scores[a["category"]] for a in actions)
    assert all(a["reason"] and a["task"] and a["criterion"] for a in actions)


def test_plan(inputs):
    plan = seven_day_plan(inputs)
    assert len(plan) == 7
    assert [d["Day"] for d in plan] == list(range(1, 8))
    assert all(0 < d["Minutes"] <= 45 and d["Done when"] for d in plan)


def test_strong_optional_enhancement():
    inputs = {k: v[2] for k, v in FIELDS.items()}
    assert recommend(inputs)[0]["priority"] == "Optional enhancement"
