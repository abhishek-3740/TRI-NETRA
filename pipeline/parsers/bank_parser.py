"""
Target path: pipeline/parsers/bank_parser.py

Polars ingestion for bank_transactions.csv — Final_Dataset_Documentation.md §2.1.
44 columns: 7 transaction-level + 14 Sender_* + 14 Receiver_* (mirrored) + 9 tail fields.
"""

from __future__ import annotations

import os
from pathlib import Path

import polars as pl

# The 14 Sender_*/Receiver_* fields are identical in shape — define once, mirror twice.
_PARTY_FIELDS: dict[str, pl.DataType] = {
    "Customer_ID": pl.Utf8,
    "Bank_Name": pl.Utf8,
    "City": pl.Utf8,  # null rate varies by side (Sender: 7.3%)
    "Account_Number": pl.Utf8,
    "IFSC": pl.Utf8,
    "Phone_Number": pl.Int64,  # entity-resolution key (§3 linking map)
    "UPI_ID": pl.Utf8,  # entity-resolution key — ~32.5% embed the phone
    "Gender": pl.Utf8,
    "Customer_Name": pl.Utf8,
    "Email": pl.Utf8,
    "DOB": pl.Utf8,  # parsed to Date below
    "Customer_Since": pl.Utf8,  # parsed to Date below
    "Occupation": pl.Utf8,
    "KYC_Status": pl.Utf8,
}

BANK_SCHEMA: dict[str, pl.DataType] = {
    "Transaction_ID": pl.Utf8,
    "Timestamp": pl.Utf8,  # parsed to Datetime below
    "Txn_Ref_Number": pl.Utf8,
    "Transaction_Mode": pl.Utf8,  # ATM|UPI|Cash Deposit|IMPS|POS|CASH|NEFT|RTGS
    "Transaction_Status": pl.Utf8,  # SUCCESS|FAILED|PENDING
    "Currency": pl.Utf8,
    "Transaction_Amount": pl.Float64,
    **{f"Sender_{k}": v for k, v in _PARTY_FIELDS.items()},
    **{f"Receiver_{k}": v for k, v in _PARTY_FIELDS.items()},
    "Merchant_Name": pl.Utf8,  # 57.3% null — UPI/IMPS/POS merchant rows only
    "Merchant_Category": pl.Utf8,  # 57.0% null
    "Channel": pl.Utf8,  # Mobile_App|ATM|Branch|Net_Banking
    "Sender_Account_Type": pl.Utf8,
    "Receiver_Account_Type": pl.Utf8,
    "Sender_Monthly_Salary": pl.Int64,
    "Receiver_Monthly_Salary": pl.Int64,
    "Sender_IP_Address": pl.Utf8,  # Key link: bridges to IPDR Public_IP_Address (§4.2 CGNAT Defeat)
    "Sender_Device_ID": pl.Utf8,  # Possible link to IPDR Device_ID
}

_DATETIME_COLS = ["Timestamp"]
_DATE_COLS = [
    "Sender_DOB",
    "Sender_Customer_Since",
    "Receiver_DOB",
    "Receiver_Customer_Since",
]

# UPI VPA looks like "9876543210@paytm" — capture the 10-digit phone if it's the handle.
_UPI_PHONE_RE = r"^(\d{10})@"


def load_bank(path: str | Path) -> pl.LazyFrame:
    """Lazily load, type, and pre-enrich bank_transactions.csv."""
    lf = pl.scan_csv(path, schema=BANK_SCHEMA, null_values=["", "NULL", "NaN"])
    return lf.with_columns(
        [pl.col(c).str.to_datetime(strict=False) for c in _DATETIME_COLS]
        + [pl.col(c).str.to_date(strict=False) for c in _DATE_COLS]
        # §3 linking map: extract phone from the UPI handle where embedded.
        + [
            pl.col("Sender_UPI_ID")
            .str.extract(_UPI_PHONE_RE, 1)
            .alias("Sender_UPI_Phone"),
            pl.col("Receiver_UPI_ID")
            .str.extract(_UPI_PHONE_RE, 1)
            .alias("Receiver_UPI_Phone"),
        ]
    )


def ingest_summary(lf: pl.LazyFrame, label: str = "BANK") -> None:
    df = lf.collect()
    print(f"\n--- {label} ---")
    print(f"rows: {df.height:,}  cols: {df.width}")
    null_counts = df.null_count()
    print("null columns (non-zero only):")
    for col, n in zip(null_counts.columns, null_counts.row(0)):
        if n:
            print(f"  {col}: {n:,} ({n / df.height:.1%})")
    extracted = df.filter(pl.col("Sender_UPI_Phone").is_not_null()).height
    print(
        f"UPI IDs with embedded phone (Sender side): {extracted:,} ({extracted / df.height:.1%})"
    )


if __name__ == "__main__":
    default_dir = Path(__file__).resolve().parents[2] / "data" / "final"
    DATA_DIR = Path(os.environ.get("TRINETRA_DATA_DIR", default_dir))

    bank = load_bank(DATA_DIR / "bank_transactions.csv")
    ingest_summary(bank)
