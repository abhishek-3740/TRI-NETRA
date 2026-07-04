"""
Isolation Forest anomaly detector — Layer 2 of the risk scoring pipeline.
Trains on synthetic transaction features and reports precision/recall +
ROC curve, used directly in the pitch deck.
"""
import joblib
import polars as pl
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_curve, roc_auc_score, precision_recall_curve
from pathlib import Path

FEATURES = ["amount", "txn_frequency_per_day", "in_out_ratio", "hour_of_day", "layering_depth", "degree_centrality"]
MODEL_PATH = Path("ml_artifacts/isolation_forest.pkl")
METRICS_DIR = Path("ml_artifacts/metrics")


def train(df: pl.DataFrame) -> IsolationForest:
    X = df.select(FEATURES).to_numpy()
    # IsolationForest is unsupervised, but we hold out labels purely for evaluation
    model = IsolationForest(n_estimators=200, contamination=0.2, random_state=42)
    model.fit(X)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    _evaluate(model, df)
    return model


def _evaluate(model: IsolationForest, df: pl.DataFrame):
    X = df.select(FEATURES).to_numpy()
    y_true = df["label"].to_numpy()

    # Isolation Forest scores: lower (more negative) = more anomalous.
    # Flip sign so higher score = more likely mule, matching y_true convention.
    scores = -model.score_samples(X)

    fpr, tpr, _ = roc_curve(y_true, scores)
    auc = roc_auc_score(y_true, scores)
    precision, recall, _ = precision_recall_curve(y_true, scores)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(METRICS_DIR / "isolation_forest_roc.npz", fpr=fpr, tpr=tpr, auc=auc)
    np.savez(METRICS_DIR / "isolation_forest_pr.npz", precision=precision, recall=recall)
    print(f"Isolation Forest trained. AUC = {auc:.3f}")


def score(features: dict) -> float:
    """Returns an anomaly score in [0, 1] for a single entity's features."""
    if not MODEL_PATH.exists():
        return 0.0
    model = joblib.load(MODEL_PATH)
    X = np.array([[features.get(f, 0) for f in FEATURES]])
    raw_score = -model.score_samples(X)[0]
    return float(np.clip(raw_score, 0, 1))


if __name__ == "__main__":
    from app.ml.data_generator import generate_synthetic_transactions
    df = generate_synthetic_transactions()
    train(df)
