"""
Bank statement template management — the "self-healing" template engine.
Lets an officer manually map columns for an unrecognized bank format,
then saves it for automatic reuse next time.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from app.parsers.template_engine import TemplateEngine

router = APIRouter()
engine = TemplateEngine()


class ColumnMapping(BaseModel):
    bank_name: str
    column_map: Dict[str, str]   # e.g. {"Date": "date", "Withdrwl Amt": "amount_debit"}
    date_format: str = "%d/%m/%Y"


@router.get("/")
def list_templates():
    return engine.list_templates()


@router.get("/{bank_key}")
def get_template(bank_key: str):
    template = engine.get_template(bank_key)
    if not template:
        raise HTTPException(404, f"No template found for '{bank_key}'.")
    return template


@router.post("/")
def save_template(mapping: ColumnMapping):
    """Called from the Manual Mapping UI after an officer maps a new bank format."""
    saved = engine.save_template(
        bank_key=mapping.bank_name.lower().replace(" ", "_"),
        column_map=mapping.column_map,
        date_format=mapping.date_format,
    )
    return {"status": "saved", "template": saved}
