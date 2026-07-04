"""
Scenario D — Unknown Bank Format (Template Engine self-heal demo)
Generates a bank CSV with deliberately unusual column names so it fails
auto-detection and triggers the Manual Mapping UI live during the demo.
"""
import csv
import os

OUT_DIR = "data/scenario_d"


def gen_unrecognized_format():
    with open(f"{OUT_DIR}/unknown_bank_statement.csv", "w", newline="") as f:
        writer = csv.writer(f)
        # Deliberately non-standard headers, unlike any pre-built template
        writer.writerow(["Txn Dt", "Particulars", "Wdrl", "Depst", "Closing Bal"])
        writer.writerow(["05/01/2026", "NEFT-OUT/suspect transfer", "12000", "", "38000"])


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_unrecognized_format()
    print("Scenario D synthetic data generated.")
