"""Metrics are computed, never hard-coded display values."""
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


def evaluate(model, x, y):
    pred = model.predict(x)
    return {"accuracy": float(accuracy_score(y, pred)), "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)), "f1": float(f1_score(y, pred, zero_division=0)),
            "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist()}
