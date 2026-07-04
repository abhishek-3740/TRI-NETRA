#!/usr/bin/env bash
# Generates synthetic data for all demo scenarios and loads them into the
# running stack. Run this after `docker-compose up`.
set -e

echo "Generating synthetic scenario data..."
python data/synthetic_generators/gen_scenario_a.py
python data/synthetic_generators/gen_scenario_b.py
python data/synthetic_generators/gen_scenario_c.py
python data/synthetic_generators/gen_scenario_d.py

echo "Generating ML training data..."
python data/synthetic_generators/gen_ml_training_data.py

echo "Done. Upload the generated files via the frontend, or extend this"
echo "script to POST them straight to /api/upload/* for a one-command demo reset."
