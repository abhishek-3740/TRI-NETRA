"""
Configurable template engine for bank statement parsing.

Templates are stored as JSON (see data/bank_templates/*.json) describing
column-name -> canonical-field mappings and date formats per bank.
If a bank format isn't recognized, the Manual Mapping UI (frontend
TemplateMappingModal.jsx -> routes_templates.py) lets an officer map it
once, and it's saved here for automatic reuse.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "data" / "bank_templates"


class TemplateEngine:
    def __init__(self, template_dir: Path = TEMPLATE_DIR):
        self.template_dir = template_dir
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self):
        return [f.stem for f in self.template_dir.glob("*.json")]

    def get_template(self, bank_key: str) -> Optional[Dict]:
        path = self.template_dir / f"{bank_key}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def save_template(self, bank_key: str, column_map: Dict[str, str], date_format: str) -> Dict:
        template = {
            "bank_name": bank_key,
            "column_map": column_map,
            "date_format": date_format,
        }
        path = self.template_dir / f"{bank_key}.json"
        with open(path, "w") as f:
            json.dump(template, f, indent=2)
        return template

    def detect_template(self, table_headers: list) -> Optional[Dict]:
        """
        Naive auto-detection: match extracted table headers against
        known templates' source column names. Returns the best-matching
        template, or None if nothing matches well enough (triggers the
        Manual Mapping UI on the frontend).
        """
        headers_set = set(h.strip().lower() for h in table_headers)
        best_match, best_score = None, 0

        for bank_key in self.list_templates():
            template = self.get_template(bank_key)
            template_cols = set(c.strip().lower() for c in template["column_map"].keys())
            overlap = len(headers_set & template_cols)
            if overlap > best_score:
                best_score = overlap
                best_match = template

        # Require at least 2 matching columns to trust auto-detection
        return best_match if best_score >= 2 else None
