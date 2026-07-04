"""
File upload endpoints: Bank PDFs, CDR CSVs, IPDR CSVs.
Writes to Postgres first (source of truth); Neo4j projection is updated
asynchronously afterward — see app/db/neo4j_client.py::sync_from_postgres.
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.parsers.bank_parser import BankParser
from app.parsers.cdr_parser import CDRParser
from app.parsers.ipdr_parser import IPDRParser
from app.db.neo4j_client import queue_neo4j_projection_update

router = APIRouter()

bank_parser = BankParser()
cdr_parser = CDRParser()
ipdr_parser = IPDRParser()


@router.post("/bank")
async def upload_bank_statement(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Bank statement upload must be a PDF.")
    contents = await file.read()
    result = bank_parser.parse(contents, filename=file.filename)

    # TODO: persist `result` to Postgres inside a transaction here.
    # Only after that commit succeeds do we queue the Neo4j projection update.
    if background_tasks is not None:
        background_tasks.add_task(queue_neo4j_projection_update, source="bank", payload=result)

    return {"filename": file.filename, "status": result.get("status"), "rows_parsed": result.get("row_count", 0)}


@router.post("/cdr")
async def upload_cdr(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "CDR upload must be a CSV.")
    contents = await file.read()
    result = cdr_parser.parse(contents)

    if background_tasks is not None:
        background_tasks.add_task(queue_neo4j_projection_update, source="cdr", payload=result)

    return {"filename": file.filename, "status": "parsed", "row_count": result.get("row_count", 0)}


@router.post("/ipdr")
async def upload_ipdr(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "IPDR upload must be a CSV.")
    contents = await file.read()
    result = ipdr_parser.parse(contents)

    if background_tasks is not None:
        background_tasks.add_task(queue_neo4j_projection_update, source="ipdr", payload=result)

    return {"filename": file.filename, "status": "parsed", "row_count": result.get("row_count", 0)}
