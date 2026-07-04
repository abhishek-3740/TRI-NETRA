from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import (
    routes_upload,
    routes_templates,
    routes_entities,
    routes_fusion,
    routes_risk,
    routes_report,
)

app = FastAPI(
    title="Project Trinetra",
    description="AI-powered, 100% local, air-gapped Bank/CDR/IPDR fusion engine.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(routes_templates.router, prefix="/api/templates", tags=["Bank Templates"])
app.include_router(routes_entities.router, prefix="/api/entities", tags=["Entities"])
app.include_router(routes_fusion.router, prefix="/api/fusion", tags=["Fusion"])
app.include_router(routes_risk.router, prefix="/api/risk", tags=["Risk Scoring"])
app.include_router(routes_report.router, prefix="/api/report", tags=["Reports"])


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "trinetra-backend",
        "neo4j_enabled": settings.use_neo4j,
        "graphsage_enabled": settings.use_graphsage,
    }
