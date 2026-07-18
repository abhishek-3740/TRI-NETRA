# TRI-NETRA — Master Project Handbook (Final Version)
## AI-Powered Financial & Telecom Dataset Analyzer (Bank + CDR + IPDR Fusion)
### Official Problem Statement: ERH26_PS_03 | Domain: Big Data and Analytics

**Event:** E-RAKSHAK Hackathon 2026 — Organized by Surat City Police in collaboration with NEXUS NIT Surat
**Team:** Mismatch | **Mentor:** Tanish Panchal
**Build Window:** 1–28 Jul 2026 | **Presentation:** 1st week Aug 2026, SVNIT Surat
**Constraint Checklist:** Cloud-enabled using Free APIs (e.g., Groq/Gemini for LLMs, Neo4j Aura for Graph, etc.) to maximize capability and speed.

---

## 1. THE PROBLEM & THE PITCH

### The Real-World Problem
An investigating officer working a financial-fraud case must requisition bank transaction data, Call Detail Records (CDR), and Internet Protocol Detail Records (IPDR). They must open three separate formats, from different providers, and manually scan thousands of rows to find moments where a call, an internet session, and a bank transfer line up in time. This takes days to weeks. By the time patterns are found, mule accounts are drained.

### Our Solution
A single, **cloud-enabled, API-accelerated** platform where an officer uploads raw Bank + CDR + IPDR exports and sees:
- **WHO** — every identifier resolved into one entity profile.
- **WHEN** — every event on one unified, zoomable timeline.
- **WHY** — every correlation comes with a numeric breakdown, never a black-box score.
- **WHO ELSE** — an interactive money-flow network graph showing mule chains.
- **PROOF** — a one-click, evidence-grade forensic report (STR/PDF) with source citations.

> *"We built TRINETRA, a powerful forensic fusion engine powered by modern cloud APIs. Our ingestion layer is a self-healing template engine covering major Indian banks out of the box, with zero code changes needed for new formats. We defeat CGNAT masking to bridge IPDR to UPI, and back our money-flow graph with Neo4j. We don't stop at rules—we use an Isolation Forest and Graph ML to catch novel smurfing topologies. TRINETRA reconstructs the exact millisecond a suspect called, logged in, and moved money."*

---

## 2. PS03 REQUIREMENTS TRACEABILITY MATRIX

| # | Official Requirement | Satisfied By |
|---|---|---|
| **KO-1** | Ingest bank statements, CDR, IPDR | §4 Ingestion Engine — Format Sniffer, Polars, Template Engine |
| **KO-2** | Normalize records onto unified entity/time | §5 Entity Resolution + `entities` table |
| **KO-3** | Correlate events on a common timeline | §5.3 Unified Timeline + Temporal Correlation Engine |
| **KO-4** | Detect patterns and visualize networks | §6 Anomaly Engine; §7.2 Network Graph |
| **KO-5** | Produce investigation-ready report | §8 Reporting Engine — STR generator, PDF/Word export |
| **FR-1.3**| Schema mapping/auto-detection | §4.4 Template Engine + ML Column Classifier |
| **FR-3.1**| Rules + ML for layering, structuring | §6.2 Rule Engine; §6.3 ML Layer (Isolation Forest) |
| **BP-1** | Automated STR generation (Bonus) | §8.2 STR Generator |
| **BP-2** | Cross-bank network / heat maps (Bonus) | §8.4 Multi-institution graph view + spatial heat maps |
| **BP-3** | Natural-language query (Bonus) | §7.6 Free LLM API (Groq/Gemini) NLQ intent parsing → Cypher/SQL |

---

## 3. TECHNOLOGY STACK

| Component | Technology | Why We Chose It |
|---|---|---|
| **Backend** | FastAPI (Python 3.11) | Async, fast, auto-generates Swagger docs. |
| **Processing** | Polars | 5–10x faster than Pandas. Won't crash on 5M+ row IPDRs. |
| **PDF/OCR** | `pdfplumber`, PaddleOCR | Instantly extracts text/tables. Runs locally on CPU. |
| **Relational** | PostgreSQL | System of record for raw entities, events, audit logs. |
| **Graph DB** | Neo4j (NetworkX fallback) | Persistent graph of accounts/UPIs. Cypher link analysis. |
| **Search/NLQ**| Elasticsearch + Free LLM API | Fuzzy entity search; Groq/Gemini API for intent parsing. |
| **Clustering** | ST-DBSCAN | Clusters CDR cell towers by location AND time. |
| **ML Models** | scikit-learn, PyTorch | Isolation Forest (unsupervised); GraphSAGE/Node2Vec (embeddings). |
| **Frontend** | React 18 + Vite + Tailwind | Modern UI, `vis-timeline` for events, Cytoscape.js for graph. |
| **Reporting** | WeasyPrint / python-docx | Auto-generates STR and legal documents. |

---

## 4. ARCHITECTURE & DATA PIPELINE

### 4.1 Multi-Format Ingestion
- **Bank Statement Parser:** 3-Tier fallback. Tier 1: `pdfplumber` (digital PDF). Tier 2: PaddleOCR (scanned PDF). Tier 3: Regex extraction of UPI narrations.
- **CDR/IPDR Parser:** Polars lazy-loads massive CSVs. IPDR parser maps NAT'd source-port + timestamp to private allocations.
- **Template Engine:** JSON templates describe column layout per bank. Unrecognized formats use a ML-classifier to guess columns, prompting the officer with a Manual Mapping UI. The mapped result is saved for future use.

### 4.2 Entity Resolution ("The Glue")
- **UPI Bridge:** Link Bank ↔ Phone via the 10-digit number in the UPI ID.
- **CGNAT Defeat:** Link Phone ↔ IP matching Bank Login IP to IPDR Public IP + NAT Port.
- **Two-Tier Matching:** Tier 1 (Exact Match), Tier 2 (Fuzzy Match via RapidFuzz).
- **Sync Strategy:** Entity resolution writes to Postgres first (Source of Truth). Background tasks push to Neo4j.

### 4.3 Fusion Engine ("The Brains")
- **Temporal Fusion:** Sliding ±30-min window around transactions to find calls/IP-sessions.
- **Graph Fusion:** Money-flow graph queried live via Cypher to find Circular laundering loops and Mastermind centrality.
- **Spatial Fusion:** ST-DBSCAN flags physically co-located suspects based on CDR tower pings.

---

## 5. INTELLIGENCE & ANOMALY ENGINE

### 5.1 Rule-Based Scoring (Primary)
- **Structuring:** Just under ₹50k reporting thresholds (+25 Risk).
- **Rapid Layering:** Money in/out same account within minutes (+25 Risk).
- **Circular Flow:** Wash trading detected via graph cycle (+20 Risk).

### 5.2 Machine Learning Layer (Secondary)
- **Isolation Forest:** Trained on 100k synthetic labeled transactions (velocity, amount variance).
- **Graph Embeddings:** GraphSAGE (or Node2Vec as CPU-safe fallback) to learn embeddings over the Neo4j money-flow graph to catch novel smurfing topologies.

---

## 6. VISUALIZATION & DASHBOARD

- **Timeline Panel (`vis-timeline`):** The "Smoking Gun" moment. Call + IP + Transfer aligned in seconds.
- **Network Panel (Cytoscape.js):** Nodes = entities, Edges = transfers. Cycles highlighted in red.
- **Risk Panel:** Complete rule + ML risk breakdown per entity.
- **Global Filter & NLQ Bar:** Type *"show transfers within 10 mins of a call to 9876543210"* → Free LLM API parses intent → Postgres/Neo4j query executes.

---

## 7. REPORTING & AUTOMATION

- **STR Generator:** Auto-fills FIU-IND STR template with entity details, risk score, and evidentiary hashes. Outputs PDF.
- **LERS Draft Generator:** Auto-fills Legal Emergency Request System template for telecom operators. Output is draft-only (no auto-send, keeping air-gap secure).
- **Evidentiary Timeline Export:** Full case timeline cited back to originating file rows (`raw_identifiers`).

---

## 8. DEMO SCENARIOS (Reproducible)

1. **Scenario A (UPI Scam):** Suspect calls victim → IP logs into victim's net-banking → ₹50k transferred → hops 3 mule accounts.
2. **Scenario B (Loan App Extortion):** Mastermind phone linked to 5 mule VPAs across different bank formats.
3. **Scenario C (SIM Swap):** CDR gap → new IMEI appears in IPDR → bank transfer follows immediately.
4. **Scenario D (Unknown Bank):** Officer manually maps columns in UI for an unsupported bank export, saving the template.
5. **Scenario E (Circular Flow):** Wash trading loop across multiple accounts highlighted natively by Neo4j graph traversal.
6. **Scenario F (NLQ Walkthrough):** Officer uses plain language query in the search bar.

---

## 9. EXECUTION TIMELINE & TEAM ROLES

### Roles
- **Person A (Ingestion Lead):** Parsers, Template Engine, synthetic data.
- **Person B (Fusion Lead):** Entity resolution, temporal correlation.
- **Person C (Intelligence/API):** ML layer, Isolation Forest, GraphSAGE, Neo4j, FastAPI.
- **Person D (Frontend/Reports):** React dashboard, STR generation, Demo rehearsal.

### Weekly Plan
**Week 1 — Foundation & Core Pipeline**
- Days 1–2: Docker Compose, synthetic data generation, package testing.
- Days 3–5: Ingestion, Template Engine, and Parsers (Polars).
- Days 6–7: Entity Resolution (UPI/CGNAT bridges).

**Week 2 — Fusion, ML & Frontend**
- Days 8–9: Temporal rules, Neo4j Cypher queries, ST-DBSCAN.
- Days 10–12: Train Isolation Forest + GraphSAGE. Finalize risk score engine.
- Days 13–14: React Dashboard, Timeline, Cytoscape, NLQ bar integration.

**Week 3 — Reporting & Hardening**
- Days 15–17: STR generator, LERS drafts, end-to-end testing of 6 scenarios.
- Days 18–19: Load testing (5M rows), air-gap security checks, error handling.
- Days 20+: Record backup demo video, dry runs, presentation prep.

---

## 10. SCALABILITY ROADMAP (Pitch Deck Material)
- **Now (Prototype):** 50K+ records. Single host (Postgres, Neo4j, Elasticsearch, FastAPI).
- **Surat (Deployment):** 10M records. Postgres read replicas + Redis cache + dedicated API tier.
- **Gujarat (Regional):** 500M records. Citus (Postgres sharding) + Neo4j/ES clustering.
- **India (National):** 3B+ records. Kafka streaming ingestion + Flink real-time correlation + ClickHouse analytics.
