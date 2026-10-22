"""Deterministic scoring. This module does not use a machine-learning model."""
import math
from numbers import Real
from src.config import FIELDS, CATEGORY_FIELDS, CATEGORY_WEIGHTS, BANDS, SCORING_VERSION


class ValidationError(ValueError):
    """An input is missing, inconsistent, or outside its declared scale."""


def validate_inputs(inputs, fields=None):
    """Validate all inputs, or only a named category's field subset."""
    cleaned = {}
    for key in (FIELDS if fields is None else fields):
        label, low, high, _, optional, _ = FIELDS[key]
        value = inputs.get(key)
        if value is None:
            if optional:
                cleaned[key] = None
                continue
            raise ValidationError(f"{label}: please enter a value.")
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValidationError(f"{label}: enter a finite number.")
        if not low <= value <= high:
            raise ValidationError(f"{label}: use a value from {low:g} to {high:g}.")
        if isinstance(low, int) and value != int(value):
            raise ValidationError(f"{label}: use a whole number.")
        cleaned[key] = float(value) if isinstance(low, float) else int(value)
    for key in ("demos", "documented"):
        if key in cleaned and "projects" in cleaned and cleaned[key] > cleaned["projects"]:
            raise ValidationError(f"{FIELDS[key][0]} cannot exceed completed projects.")
    if cleaned.get("projects") == 0 and cleaned.get("quality", 1) > 1:
        raise ValidationError("With no completed projects, set implementation & understanding to 1 (Beginner).")
    if cleaned.get("languages") == 0 and cleaned.get("programming", 1) > 1:
        raise ValidationError("With no programming languages, set programming proficiency to 1 (Beginner).")
    return cleaned


def normalize(key, value):
    _, low, high, _, _, cap = FIELDS[key]
    if cap:
        return min(value / cap, 1.) * 100
    return (value - low) / (high - low) * 100


def score_category(category, inputs):
    """Calculate one category independently from just its own valid inputs."""
    weights = CATEGORY_FIELDS[category]
    clean = validate_inputs(inputs, fields=weights)
    present = {k: w for k, w in weights.items() if clean[k] is not None}
    return sum(normalize(k, clean[k]) * w for k, w in present.items()) / sum(present.values())


def category_scores(inputs):
    """Full precision category scores; round only for display/storage."""
    clean = validate_inputs(inputs)
    return {category: score_category(category, clean) for category in CATEGORY_FIELDS}


def readiness_band(score):
    return next(label for boundary, label in BANDS if score < boundary)


def assess(inputs):
    clean = validate_inputs(inputs)
    categories = category_scores(clean)
    score = round(max(0., min(100., sum(categories[k] * w for k, w in CATEGORY_WEIGHTS.items()))), 2)
    return {"score": score, "band": readiness_band(score),
            "categories": {k: round(v, 2) for k, v in categories.items()},
            "inputs": clean, "scoring_version": SCORING_VERSION,
            "missing_optional": [k for k, v in clean.items() if v is None]}
