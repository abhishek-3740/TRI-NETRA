"""
Neo4j schema reference (constants, not an ORM — Neo4j is queried via raw
Cypher in app/fusion/graph_engine_neo4j.py). Kept here as the single
source of truth for label/relationship naming so Cypher queries and the
Postgres->Neo4j sync script stay consistent.
"""

NODE_LABEL_ACCOUNT = "Account"
RELATIONSHIP_TRANSFER = "TRANSFER"

# Constraint statements to run once against a fresh Neo4j instance
SCHEMA_CONSTRAINTS = [
    "CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
]

# Cypher used by the rebuild script to push a Postgres Transfer row into Neo4j
CYPHER_UPSERT_TRANSFER = """
MERGE (a:Account {id: $from_account_id, case_id: $case_id})
MERGE (b:Account {id: $to_account_id, case_id: $case_id})
MERGE (a)-[t:TRANSFER {id: $transfer_id}]->(b)
SET t.amount = $amount, t.timestamp = $timestamp
"""
