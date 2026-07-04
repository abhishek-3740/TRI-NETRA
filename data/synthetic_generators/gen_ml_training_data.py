"""Thin CLI wrapper around app.ml.data_generator for standalone use."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.ml.data_generator import generate_synthetic_transactions

if __name__ == "__main__":
    df = generate_synthetic_transactions(n_legit=80_000, n_mule=20_000)
    out_path = os.path.join(os.path.dirname(__file__), "synthetic_transactions.csv")
    df.write_csv(out_path)
    print(f"Generated {df.height} rows -> {out_path}")
