# 🎯 Project Trinetra

AI-powered, 100% local, air-gapped financial & telecom dataset fusion engine
for detecting fraud rings across Bank, CDR, and IPDR data.

## Quickstart

```bash
cp .env.example .env      # edit passwords as needed
docker-compose up --build
```

- Backend (FastAPI + Swagger docs): http://localhost:8000/docs
- Frontend (React dashboard): http://localhost:5173
- Neo4j Browser: http://localhost:7474

## Architecture

See [`docs/PROJECT_TRINETRA_v2.md`](docs/PROJECT_TRINETRA_v2.md) for the full
architecture, pipeline, ML strategy, and demo scenarios.

**Key architectural rules baked into this scaffold:**
1. **Postgres is the source of truth.** Neo4j is a read-model/projection — it
   is written to only *after* a Postgres transaction commits, via a
   background task. If Neo4j goes down, rebuild it with
   `scripts/rebuild_neo4j_from_postgres.sh`.
2. **The frontend never talks to Neo4j directly.** All graph queries are
   proxied through FastAPI (`app/api/routes_fusion.py`), which runs the
   Cypher query, attaches risk scores/colors, and returns plain JSON for
   Cytoscape.js to render.
3. **GraphSAGE is the ML goal; Node2Vec is the safety net.** If PyTorch
   Geometric install/training stalls (common with CPU-only `torch-scatter`
   dependency issues), flip `USE_GRAPHSAGE=false` in `.env` to fall back to
   Node2Vec without touching the rest of the pipeline.

## Seeding demo data

```bash
bash scripts/seed_demo.sh
```

## Running tests

```bash
cd backend && pytest
```
