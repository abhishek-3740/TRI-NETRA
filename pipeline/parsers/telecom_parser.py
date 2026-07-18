"""
Target path in your repo: pipeline/parsers/telecom_parser.py

Polars-based ingestion for CDR and IPDR exports, per the schemas in
Final_Dataset_Documentation.md (ERH26_PS_03 — TRI-NETRA), §2.2 / §2.3.

NOTE: `Subscriber_ID` exists in BOTH cdr_final.csv and ipdr_final.csv but
maps to DIFFERENT people in each dataset (7,634 colliding IDs). It is NOT
a valid cross-dataset join key — only phone (Caller_MSISDN / User_MSISDN)
and IMEI are reliable entity-resolution links (per §3, §4.2 of the
handbook). Do not join on Subscriber_ID in downstream fusion code.
"""

from __future__ import annotations

import os
from pathlib import Path

import polars as pl

# ---------------------------------------------------------------------------
# Canonical schemas (24 columns each — Final_Dataset_Documentation.md §2.2/2.3)
# ---------------------------------------------------------------------------

CDR_SCHEMA: dict[str, pl.DataType] = {
    "CDR_ID": pl.Utf8,
    "Call_Start_Time": pl.Utf8,  # parsed to Datetime below
    "Call_End_Time": pl.Utf8,  # parsed to Datetime below
    "Call_Duration_Seconds": pl.Int64,
    "Call_Type": pl.Utf8,  # Outgoing | Incoming | Missed
    "Call_Status": pl.Utf8,  # Completed | Missed | Failed | Dropped
    "Subscriber_ID": pl.Utf8,  # internal CDR only — NOT a join key
    "Caller_MSISDN": pl.Int64,
    "Receiver_MSISDN": pl.Int64,
    "Caller_Name": pl.Utf8,
    "Receiver_Name": pl.Utf8,
    "SIM_Number": pl.Int64,
    "IMSI": pl.Float64,  # 2.5% null (stored as float text, same as IMEI)
    "IMEI": pl.Float64,  # 2.5% null — links to IPDR
    "Device_Model": pl.Utf8,
    "Device_OS": pl.Utf8,
    "Network_Provider": pl.Utf8,
    "Network_Type": pl.Utf8,
    "Cell_Tower_ID": pl.Utf8,  # 2.5% null
    "Tower_City": pl.Utf8,  # 2.5% null
    "Latitude": pl.Float64,  # 2.5% null
    "Longitude": pl.Float64,  # 2.5% null
    "International_Call_Flag": pl.Int8,
    "Roaming_Flag": pl.Int8,
}

IPDR_SCHEMA: dict[str, pl.DataType] = {
    "IPDR_ID": pl.Utf8,
    "Session_ID": pl.Utf8,
    "Subscriber_ID": pl.Utf8,  # ISP-internal only — NOT a join key
    "User_MSISDN": pl.Int64,  # links to Bank phone + CDR phone
    "User_Name": pl.Utf8,
    "Session_Start_Time": pl.Utf8,  # parsed to Datetime below
    "Session_End_Time": pl.Utf8,  # parsed to Datetime below
    "Session_Duration_Seconds": pl.Int64,
    "Data_Usage_MB": pl.Float64,
    "Upload_MB": pl.Float64,
    "Download_MB": pl.Float64,
    "Public_IP_Address": pl.Utf8,  # 2.5% null
    "Private_IP_Address": pl.Utf8,
    "ISP_Name": pl.Utf8,
    "Network_Type": pl.Utf8,
    "Connection_Type": pl.Utf8,
    "Device_ID": pl.Utf8,  # 2.5% null
    "IMEI": pl.Float64,  # 2.5% null — links to CDR
    "Device_Model": pl.Utf8,
    "Operating_System": pl.Utf8,
    "Browser": pl.Utf8,
    "IP_Location_City": pl.Utf8,  # 2.5% null
    "Latitude": pl.Float64,  # 2.5% null
    "Longitude": pl.Float64,  # 2.5% null
}

_DATETIME_COLUMNS = {
    "cdr": ["Call_Start_Time", "Call_End_Time"],
    "ipdr": ["Session_Start_Time", "Session_End_Time"],
}


def _parse_datetimes(lf: pl.LazyFrame, columns: list[str]) -> pl.LazyFrame:
    """Cast string timestamp columns to Datetime, tolerating format drift."""
    return lf.with_columns([pl.col(c).str.to_datetime(strict=False) for c in columns])


def load_cdr(path: str | Path) -> pl.LazyFrame:
    """Lazily load and type cdr_final.csv (or any CDR export matching the schema)."""
    lf = pl.scan_csv(path, schema=CDR_SCHEMA, null_values=["", "NULL", "NaN"])
    return _parse_datetimes(lf, _DATETIME_COLUMNS["cdr"])


def load_ipdr(path: str | Path) -> pl.LazyFrame:
    """Lazily load and type ipdr_final.csv (or any IPDR export matching the schema)."""
    lf = pl.scan_csv(path, schema=IPDR_SCHEMA, null_values=["", "NULL", "NaN"])
    return _parse_datetimes(lf, _DATETIME_COLUMNS["ipdr"])


def ingest_summary(lf: pl.LazyFrame, label: str) -> None:
    """Sanity check: row count, dtypes, and non-zero null counts. Collects the frame."""
    df = lf.collect()
    print(f"\n--- {label} ---")
    print(f"rows: {df.height:,}  cols: {df.width}")
    null_counts = df.null_count()
    print("null columns (non-zero only):")
    for col, n in zip(null_counts.columns, null_counts.row(0)):
        if n:
            print(f"  {col}: {n:,} ({n / df.height:.1%})")


if __name__ == "__main__":
    # TRINETRA_DATA_DIR is set to /app/data/final inside docker (see docker-compose.yml);
    # falls back to <repo_root>/data/final when run locally.
    default_dir = Path(__file__).resolve().parents[2] / "data" / "final"
    DATA_DIR = Path(os.environ.get("TRINETRA_DATA_DIR", default_dir))

    cdr = load_cdr(DATA_DIR / "cdr_final.csv")
    ipdr = load_ipdr(DATA_DIR / "ipdr_final.csv")

    ingest_summary(cdr, "CDR")
    ingest_summary(ipdr, "IPDR")
