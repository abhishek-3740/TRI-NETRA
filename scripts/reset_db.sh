#!/usr/bin/env bash
# Drops and recreates the Postgres schema + clears the Neo4j graph.
# Use between demo runs to guarantee a clean slate.
set -e

echo "Resetting Postgres..."
docker-compose exec -T postgres psql -U "${POSTGRES_USER:-trinetra}" -d "${POSTGRES_DB:-trinetra}" -c "
  DROP TABLE IF EXISTS transfers, events, entities, cases CASCADE;
"
# TODO: run alembic upgrade head (or your migration tool) here to recreate tables.

echo "Resetting Neo4j..."
docker-compose exec -T neo4j cypher-shell -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-changeme}" \
  "MATCH (n) DETACH DELETE n;"

echo "Reset complete."
