"""
Synthetic labeled transaction generator for training the Isolation Forest
and graph-embedding classifiers. Produces realistic mule-vs-legitimate
transaction patterns without using any real financial data.
"""
import random
import polars as pl
from datetime import datetime, timedelta


def generate_synthetic_transactions(n_legit: int = 80_000, n_mule: int = 20_000, seed: int = 42) -> pl.DataFrame:
    random.seed(seed)
    rows = []

    for i in range(n_legit):
        rows.append(_legit_transaction(i))
    for i in range(n_mule):
        rows.append(_mule_transaction(i))

    df = pl.DataFrame(rows)
    return df.sample(fraction=1.0, shuffle=True, seed=seed)  # shuffle legit/mule together


def _legit_transaction(i: int) -> dict:
    return {
        "account_id": f"legit_{i}",
        "amount": round(random.uniform(500, 20000), 2),
        "txn_frequency_per_day": random.randint(1, 5),
        "in_out_ratio": round(random.uniform(0.3, 3.0), 2),
        "hour_of_day": random.randint(7, 22),
        "layering_depth": 0,
        "degree_centrality": round(random.uniform(0.0, 0.1), 3),
        "label": 0,  # 0 = legitimate
    }


def _mule_transaction(i: int) -> dict:
    return {
        "account_id": f"mule_{i}",
        "amount": round(random.uniform(10000, 100000), 2),
        "txn_frequency_per_day": random.randint(10, 50),
        "in_out_ratio": round(random.uniform(5.0, 20.0), 2),   # much more money in than out
        "hour_of_day": random.choice([0, 1, 2, 3, 23]),        # odd hours
        "layering_depth": random.randint(2, 5),
        "degree_centrality": round(random.uniform(0.3, 0.9), 3),
        "label": 1,  # 1 = mule
    }


if __name__ == "__main__":
    df = generate_synthetic_transactions()
    df.write_csv("data/synthetic_generators/synthetic_transactions.csv")
    print(f"Generated {df.height} synthetic transactions.")
