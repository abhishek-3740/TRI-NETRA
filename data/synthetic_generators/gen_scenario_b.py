"""
Scenario B — Loan App Extortion (The Network)
Generates 5 bank CSVs (mule accounts) + 1 mastermind CDR, all linked to a
single mastermind phone via 5 different mule VPAs, to demo the Neo4j
mastermind-centrality query.
"""
import csv
import os

OUT_DIR = "data/scenario_b"
MASTERMIND_PHONE = "9000000099"


def gen_mule_bank_csvs():
    for i in range(5):
        with open(f"{OUT_DIR}/bank_mule_{i}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "narration", "amount_credit"])
            writer.writerow(["02/01/2026", f"UPI/{MASTERMIND_PHONE}@okhdfc/loan disbursement", str(20000 + i * 500)])


def gen_mastermind_cdr():
    with open(f"{OUT_DIR}/mastermind_cdr.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["calling_party", "called_party", "timestamp", "cell_id", "lat", "lon"])
        for i in range(5):
            writer.writerow([MASTERMIND_PHONE, f"91000000{10+i}", "2026-01-02T11:00:00", "TWR002", 21.20, 72.84])


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_mule_bank_csvs(); gen_mastermind_cdr()
    print("Scenario B synthetic data generated.")
