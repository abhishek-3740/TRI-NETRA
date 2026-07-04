"""
Scenario A — UPI Investment Scam ("The Smoking Gun")
Generates: victim bank CSV (proxy for PDF), suspect CDR, suspect IPDR —
timed so a call, login, and transfer align within minutes.
"""
import csv
from datetime import datetime, timedelta

OUT_DIR = "data/scenario_a"
BASE_TIME = datetime(2026, 1, 1, 14, 0, 0)


def gen_cdr():
    with open(f"{OUT_DIR}/cdr.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["calling_party", "called_party", "timestamp", "cell_id", "lat", "lon"])
        writer.writerow(["9000000001", "9111111111", (BASE_TIME + timedelta(minutes=2)).isoformat(), "TWR001", 21.17, 72.83])


def gen_ipdr():
    with open(f"{OUT_DIR}/ipdr.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["public_ip", "nat_port", "private_ip", "session_start", "session_end"])
        writer.writerow(["49.36.10.5", "40012", "192.168.1.10",
                          (BASE_TIME + timedelta(minutes=4)).isoformat(),
                          (BASE_TIME + timedelta(minutes=9)).isoformat()])


def gen_bank():
    with open(f"{OUT_DIR}/bank_transactions.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "narration", "amount_debit", "login_ip"])
        writer.writerow([(BASE_TIME + timedelta(minutes=8)).strftime("%d/%m/%Y"),
                          "UPI/9111111111@okhdfc/investment scheme", "50000", "49.36.10.5"])
        # Money hops to 3 mule accounts by minute 12
        for i in range(3):
            writer.writerow([(BASE_TIME + timedelta(minutes=12)).strftime("%d/%m/%Y"),
                              f"UPI/mule_{i}@okhdfc/transfer", str(15000 + i * 1000), ""])


if __name__ == "__main__":
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_cdr(); gen_ipdr(); gen_bank()
    print("Scenario A synthetic data generated.")
