"""
STR (Suspicious Transaction Report) and LERS draft generation.

NOTE: LERS output is a DRAFT ONLY, meant for officer review and manual
signature/submission. This endpoint never sends anything over the network —
doing so would both break the air-gapped design and create an unreviewed
legal-instrument liability.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.reports.str_generator import generate_str_report
from app.reports.lers_draft_generator import generate_lers_draft

router = APIRouter()


@router.get("/str/{case_id}")
def download_str(case_id: str):
    path = generate_str_report(case_id)
    return FileResponse(path, filename=f"STR_{case_id}.pdf", media_type="application/pdf")


@router.get("/lers/{case_id}")
def download_lers_draft(case_id: str):
    path = generate_lers_draft(case_id)
    return FileResponse(
        path,
        filename=f"LERS_DRAFT_{case_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
