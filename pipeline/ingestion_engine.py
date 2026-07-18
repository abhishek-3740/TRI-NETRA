"""
pipeline/ingestion_engine.py
PDF Bank Statement Ingestion Engine for TRI-NETRA (ERH26_PS_03).

Parses digital PDF bank statements, extracts transaction tables,
mines UPI IDs from narration, detects transaction modes,
and normalizes to the canonical TRI-NETRA schema.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
import polars as pl


# ── Config & Regex Patterns ──────────────────────────────────────────────────

UPI_PATTERN = re.compile(r"[\w.-]+@[\w.-]+")
TXN_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "UPI": ["upi", "upi-", "upi/", "upi transfer"],
    "NEFT": ["neft", "neft-", "neft/", "national electronic"],
    "IMPS": ["imps", "imps-", "imps/", "immediate payment"],
    "RTGS": ["rtgs", "rtgs-", "real time gross"],
    "ATM": ["atm", "atm wdl", "atm withdrawal", "cash withdrawal"],
    "POS": ["pos", "point of sale", "card swiped", "purchase"],
    "CASH": ["cash deposit", "cash wdl", "cash"],
    "CHEQUE": ["chq", "cheque", "chk", "check no"],
}


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class ParsedTransaction:
    raw_date: str
    timestamp: Optional[datetime]
    narration: str
    chq_ref_no: Optional[str]
    value_date: Optional[str]
    withdrawal: Optional[float]
    deposit: Optional[float]
    closing_balance: Optional[float]
    transaction_amount: float
    transaction_type: str
    extracted_upi_id: Optional[str]
    transaction_id: str = field(default_factory=lambda: f"PARSED_{uuid.uuid4().hex[:12].upper()}")


# ── Base Parser ─────────────────────────────────────────────────────────────

class PDFStatementParser(ABC):
    """
    Abstract base for bank-specific PDF parsers.
    Subclass per bank (HDFC, SBI, ICICI, Axis, etc.) to handle
    layout-specific column indices and date formats.
    """

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.raw_pages: List[List[List[str]]] = []  # pages -> tables -> rows -> cells
        self.transactions: List[ParsedTransaction] = []

    # ── Public API ───────────────────────────────────────────────────────

    def parse(self) -> pl.DataFrame:
        """Full pipeline: extract → clean → normalize → DataFrame."""
        self._extract_tables()
        self._parse_rows()
        return self._to_dataframe()

    def save(self, out_path: str | Path) -> None:
        df = self.parse()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        df.write_csv(out_path)
        print(f"[IE] Saved {df.height} rows to {out_path}")

    # ── Extraction ─────────────────────────────────────────────────────────

    def _extract_tables(self) -> None:
        """Pull tables from every page. Skip pages with no tables."""
        print(f"[IE] Opening {self.pdf_path.name}...")
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    continue
                for table in tables:
                    if table and len(table) > 1:
                        self.raw_pages.append(table)
        total_rows = sum(len(t) for t in self.raw_pages)
        print(f"[IE] Extracted {len(self.raw_pages)} tables, ~{total_rows} raw rows.")

    # ── Row Parsing (bank-specific) ──────────────────────────────────────

    @abstractmethod
    def _parse_rows(self) -> None:
        """Override in subclass to map raw table rows to ParsedTransaction."""
        raise NotImplementedError

    @abstractmethod
    def _map_columns(self, header: List[str]) -> Dict[str, int]:
        """
        Given a table header, return a dict mapping canonical field names
        to column indices: {'date': 0, 'narration': 1, ...}
        """
        raise NotImplementedError

    # ── Shared Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _extract_upi(narration: str) -> Optional[str]:
        match = UPI_PATTERN.search(narration)
        return match.group(0).lower() if match else None

    @staticmethod
    def _detect_txn_type(narration: str) -> str:
        narr_lower = narration.lower()
        for txn_type, keywords in TXN_TYPE_KEYWORDS.items():
            if any(kw in narr_lower for kw in keywords):
                return txn_type
        return "OTHER"

    @staticmethod
    def _parse_amount(val: str | None) -> Optional[float]:
        if not val:
            return None
        cleaned = val.replace(",", "").replace("₹", "").replace("(", "-").replace(")", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _parse_date(val: str | None, fmt: str = "%d/%m/%Y") -> Optional[datetime]:
        if not val:
            return None
        for f in (fmt, "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d %b %Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(val.strip(), f)
            except ValueError:
                continue
        return None

    @staticmethod
    def _compute_txn_amount(
        withdrawal: Optional[float],
        deposit: Optional[float],
    ) -> float:
        """Return signed amount: negative for withdrawal, positive for deposit."""
        if withdrawal and withdrawal > 0:
            return -abs(withdrawal)
        if deposit and deposit > 0:
            return abs(deposit)
        return 0.0

    # ── Normalization ──────────────────────────────────────────────────────

    def _to_dataframe(self) -> pl.DataFrame:
        if not self.transactions:
            print("[IE] Warning: No transactions parsed. Returning empty frame.")
            return pl.DataFrame(schema={
                "Transaction_ID": pl.Utf8,
                "Timestamp": pl.Datetime,
                "Raw_Date": pl.Utf8,
                "Narration": pl.Utf8,
                "Chq_Ref_No": pl.Utf8,
                "Value_Date": pl.Utf8,
                "Transaction_Amount": pl.Float64,
                "Transaction_Type": pl.Utf8,
                "Extracted_UPI_ID": pl.Utf8,
                "Closing_Balance": pl.Float64,
            })

        rows = [
            {
                "Transaction_ID": t.transaction_id,
                "Timestamp": t.timestamp,
                "Raw_Date": t.raw_date,
                "Narration": t.narration,
                "Chq_Ref_No": t.chq_ref_no,
                "Value_Date": t.value_date,
                "Transaction_Amount": t.transaction_amount,
                "Transaction_Type": t.transaction_type,
                "Extracted_UPI_ID": t.extracted_upi_id,
                "Closing_Balance": t.closing_balance,
            }
            for t in self.transactions
        ]

        df = pl.DataFrame(rows)
        # Drop rows where we couldn't parse a date or amount
        df = df.filter(
            pl.col("Timestamp").is_not_null() & (pl.col("Transaction_Amount") != 0)
        )
        return df


# ── Concrete: HDFC Parser ────────────────────────────────────────────────────

class HDFCStatementParser(PDFStatementParser):
    """
    Parser for HDFC Bank digital PDF statements.
    Expected header: Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt. | Deposit Amt. | Closing Balance
    """

    def _map_columns(self, header: List[str]) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        header_norm = [h.lower().strip().replace(".", "").replace("/", "") for h in header]

        for i, h in enumerate(header_norm):
            if "date" in h and "value" not in h:
                mapping["date"] = i
            elif "narration" in h or "description" in h or "particulars" in h:
                mapping["narration"] = i
            elif "chq" in h or "ref" in h or "cheque" in h:
                mapping["chq_ref"] = i
            elif "value" in h and "date" in h:
                mapping["value_date"] = i
            elif "withdrawal" in h or "debit" in h or "wdl" in h:
                mapping["withdrawal"] = i
            elif "deposit" in h or "credit" in h:
                mapping["deposit"] = i
            elif "balance" in h or "closing" in h:
                mapping["balance"] = i

        return mapping

    def _parse_rows(self) -> None:
        for table in self.raw_pages:
            if not table or len(table) < 2:
                continue

            header = table[0]
            col_map = self._map_columns(header)
            if not col_map:
                continue

            for row in table[1:]:
                if len(row) < max(col_map.values()) + 1:
                    continue

                # Skip summary / total rows
                narration = self._safe_get(row, col_map.get("narration"))
                if not narration or "opening balance" in narration.lower() or "total" in narration.lower():
                    continue

                raw_date = self._safe_get(row, col_map.get("date"))
                timestamp = self._parse_date(raw_date, fmt="%d/%m/%Y")

                withdrawal = self._parse_amount(self._safe_get(row, col_map.get("withdrawal")))
                deposit = self._parse_amount(self._safe_get(row, col_map.get("deposit")))
                txn_amount = self._compute_txn_amount(withdrawal, deposit)

                # Skip zero-amount rows (headers, footers, blank lines)
                if txn_amount == 0:
                    continue

                upi = self._extract_upi(narration)
                txn_type = self._detect_txn_type(narration)

                self.transactions.append(
                    ParsedTransaction(
                        raw_date=raw_date or "",
                        timestamp=timestamp,
                        narration=narration.strip(),
                        chq_ref_no=self._safe_get(row, col_map.get("chq_ref")),
                        value_date=self._safe_get(row, col_map.get("value_date")),
                        withdrawal=withdrawal,
                        deposit=deposit,
                        closing_balance=self._parse_amount(self._safe_get(row, col_map.get("balance"))),
                        transaction_amount=txn_amount,
                        transaction_type=txn_type,
                        extracted_upi_id=upi,
                    )
                )

        print(f"[IE] Parsed {len(self.transactions)} transactions from HDFC statement.")

    @staticmethod
    def _safe_get(row: List[str], idx: Optional[int]) -> Optional[str]:
        if idx is None or idx >= len(row):
            return None
        val = row[idx]
        return val.strip() if val else None


# ── Factory ──────────────────────────────────────────────────────────────────

def get_parser(bank_name: str, pdf_path: str | Path) -> PDFStatementParser:
    """
    Factory to instantiate the correct parser by bank name.
    Extend this as you add SBI, ICICI, Axis, etc.
    """
    bank = bank_name.strip().upper()
    if bank in ("HDFC", "HDFC BANK"):
        return HDFCStatementParser(pdf_path)
    # TODO: Add SBI, ICICI, Axis, PNB, Kotak, etc.
    raise ValueError(f"No parser registered for bank: {bank_name}")


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_ingestion(
    pdf_path: str | Path,
    bank_name: str,
    out_csv: str | Path,
) -> pl.DataFrame:
    parser = get_parser(bank_name, pdf_path)
    df = parser.parse()
    parser.save(out_csv)
    return df


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent

    # Example usage — requires a sample PDF to be placed at this path
    sample_pdf = ROOT / "data" / "raw_statements" / "sample_hdfc_statement.pdf"
    if sample_pdf.exists():
        run_ingestion(
            pdf_path=sample_pdf,
            bank_name="HDFC",
            out_csv=ROOT / "data" / "parsed" / "normalized_statement.csv",
        )
    else:
        print(f"[IE] No sample PDF found at {sample_pdf}. Skipping demo run.")
        print("[IE] Place an HDFC bank statement PDF at the above path to test ingestion.")
