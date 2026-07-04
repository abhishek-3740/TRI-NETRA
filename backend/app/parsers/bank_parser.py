"""
Bank statement parser — 3-tier fallback:
  Tier 1: pdfplumber (digital-native PDFs)
  Tier 2: PaddleOCR PP-Structure (scanned PDFs) — install paddleocr to enable
  Tier 3: Regex extraction of UPI narrations from whatever text Tier 1/2 produced

Falls through to the Template Engine for column normalization, and to the
Manual Mapping UI if no template matches.
"""
import io
import re
from typing import Dict

import pdfplumber

from app.parsers.template_engine import TemplateEngine
from app.resolution.upi_bridge import extract_upi_id

UPI_REGEX = re.compile(r"[\w.\-]{2,}@[a-zA-Z]{2,}")


class BankParser:
    def __init__(self):
        self.template_engine = TemplateEngine()

    def parse(self, file_bytes: bytes, filename: str = "") -> Dict:
        tables = self._tier1_pdfplumber(file_bytes)

        if not tables:
            tables = self._tier2_ocr(file_bytes)

        if not tables:
            return {"status": "failed", "reason": "No extractable table found (Tier 1 & 2 both failed).", "row_count": 0}

        headers = tables[0][0] if tables[0] else []
        template = self.template_engine.detect_template(headers)

        if template is None:
            return {
                "status": "needs_manual_mapping",
                "reason": "No matching bank template found.",
                "raw_headers": headers,
                "raw_preview": tables[0][:5],
                "row_count": len(tables[0]) - 1 if tables[0] else 0,
            }

        rows = self._apply_template(tables[0], template)
        rows = self._tier3_regex_upi(rows)

        return {"status": "parsed", "bank": template["bank_name"], "rows": rows, "row_count": len(rows)}

    def _tier1_pdfplumber(self, file_bytes: bytes):
        tables = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                tables.extend(page_tables)
        return tables

    def _tier2_ocr(self, file_bytes: bytes):
        # Lazy import so the app runs even if paddleocr isn't installed yet.
        try:
            from app.parsers.ocr_engine import extract_tables_via_ocr
            return extract_tables_via_ocr(file_bytes)
        except ImportError:
            return []

    def _apply_template(self, table, template) -> list:
        headers, *data_rows = table
        col_map = template["column_map"]
        normalized = []
        for row in data_rows:
            record = {}
            for raw_col, value in zip(headers, row):
                canonical = col_map.get(raw_col.strip(), None)
                if canonical:
                    record[canonical] = value
            if record:
                normalized.append(record)
        return normalized

    def _tier3_regex_upi(self, rows: list) -> list:
        for row in rows:
            narration = row.get("narration", "") or ""
            upi_match = UPI_REGEX.search(narration)
            if upi_match:
                row["upi_id"] = upi_match.group()
                row["linked_phone"] = extract_upi_id(upi_match.group())
        return rows
