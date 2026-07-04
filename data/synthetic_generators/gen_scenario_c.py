"""
Scenario C — SIM-Swap + Physical Co-location (The Bonus)
Generates CDR with a coverage gap (SIM swap), IPDR with a new IMEI
appearing right after, and a bank CSV showing the resulting NEFT transfer.
"""
import csv
import os
from datetime import datetime, timedelta

OUT_DIR = "data/scenario_c"
BASE_TIME = datetime(2026, 1, 3, 9, 0, 0)


def gen_cdr_with_gap():
    with open(f"{OUT_DIR}/cdr.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["calling_party", "called_party", "timestamp", "cell_id", "lat", "lon"])
        # Suspect A and B ping the same tower minutes apart -> co-location
        writer.writerow(["9000000201", "9000000202", BASE_TIME.isoformat(), "TWR003", 21.19, 72.85])
        writer.writerow(["9000000202", "9000000201", (BASE_TIME + timedelta(minutes=3)).isoformat(), "TWR003", 21.19, 72.85])
        # Gap follows -> SIM swap
        # (next record 2 hours later on a new IMEI, handled in ipdr.csv)


def gen_ipdr_new_imei():
    with open(f"{OUT_DIR}/ipdr.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["public_ip", "nat_port", "private_ip", "session_start", "session_end", "imei"])
        writer.writerow(["49.36.20.9", "41050", "192.168.2.20",
                          (BASE_TIME + timedelta(hours=2)).isoformat(),
                          (BASE_TIME + timedelta(hours=2, minutes=10)).isoformat(),
                          "NEW-IMEI-99887766"])


def gen_bank_neft():
    with open(f"{OUT_DIR}/bank_transactions.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "narration", "amount_debit"])
        writer.writerow([(BASE_TIME + timedelta(hours=2, minutes=15)).strftime("%d/%m/%Y"), "NEFT/fraudulent transfer", "75000"])


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_cdr_with_gap(); gen_ipdr_new_imei(); gen_bank_neft()
    print("Scenario C synthetic data generated.")
