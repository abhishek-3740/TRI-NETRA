"""
Normalization helpers: timestamps to IST epoch, column-name standardization
beyond what the Template Engine already handles for bank statements.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

COLUMN_ALIASES = {
    "withdrwl_amt": "amount_debit",
    "debit": "amount_debit",
    "withdrawal_amount": "amount_debit",
    "deposit_amt": "amount_credit",
    "credit": "amount_credit",
    "deposit_amount": "amount_credit",
}


def to_ist_epoch(dt_str: str, date_format: str) -> int:
    """Parses a timestamp string (assumed IST) and returns Unix epoch seconds."""
    naive = datetime.strptime(dt_str.strip(), date_format)
    aware = naive.replace(tzinfo=IST)
    return int(aware.timestamp())


def normalize_column_name(raw_name: str) -> str:
    key = raw_name.strip().lower().replace(" ", "_")
    return COLUMN_ALIASES.get(key, key)
