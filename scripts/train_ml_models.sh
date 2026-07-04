#!/usr/bin/env bash
# Trains the Isolation Forest and graph-embedding classifier from scratch
# using freshly generated synthetic data.
set -e

cd backend

echo "Generating synthetic training data..."
python -m app.ml.data_generator

echo "Training Isolation Forest (produces ROC/precision-recall metrics)..."
python -m app.ml.isolation_forest

echo "Done. Metrics written to ml_artifacts/metrics/, model to ml_artifacts/isolation_forest.pkl"
echo "NOTE: GraphSAGE/Node2Vec training runs on-demand per case via app.ml.graphsage_model —"
echo "there's no separate offline training step since it depends on each case's live graph."
