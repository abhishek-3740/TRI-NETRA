# 🎯 PROJECT TRINETRA — v2
## Master Architecture & Pipeline (2+ Week Build)

**Problem Statement:** AI-Powered Financial & Telecom Dataset Analyzer (Bank, CDR, IPDR Fusion)

**Core Constraint:** 100% Local, Air-Gapped, No Cloud APIs. Local/CPU training is now acceptable given the extended timeline — no GPU dependency required, but full local training pipelines are in scope.

**Timeline Context:** This version assumes a **2+ week hackathon window**, not a single 36-hour sprint. All upgrades below are scoped to be built properly rather than rushed, with real testing, real metrics, and real fallbacks.

---

## 📦 1. Technology Stack (v2)

| Component | Technology / Library | Why We Chose It |
|---|---|---|
| Backend Framework | FastAPI (Python 3.11) | Async, fast, auto-generates Swagger docs for judges to test. |
| Heavy Data Processing | Polars | 5–10x faster than Pandas. Won't crash on 5M+ row IPDR files. |
| Digital PDF Parsing | pdfplumber | Instantly extracts text/tables from digital-native PDFs. |
| Scanned PDF/Image OCR | PaddleOCR (PP-Structure) | Pre-trained table layout detection. Runs on CPU. No training needed. |
| **Template Engine (NEW)** | Custom config-driven mapper | Configurable column-mapping per bank format, extensible via UI. |
| Semantic Parsing | Regex & RapidFuzz | Extracts UPI IDs, normalizes bank column names fuzzily. |
| **Relational Store** | PostgreSQL | System of record: raw entities, events, audit logs, case metadata. |
| **Graph Database (NEW)** | Neo4j | Persistent, queryable graph of accounts/UPIs/transfers. Cypher-based link analysis. |
| Graph Engine (fallback) | NetworkX | Feature-flagged fallback if Neo4j is unavailable/fails during demo. |
| Spatio-Temporal Clustering | ST-DBSCAN | Clusters CDR cell towers by location AND time for physical co-location. |
| **ML: Anomaly Detection (NEW)** | Isolation Forest (scikit-learn) | Unsupervised outlier detection on transaction features. CPU-trainable. |
| **ML: Graph Embeddings (NEW)** | GraphSAGE (PyTorch Geometric) — **Node2Vec as safety-net fallback** | Learns node embeddings over the money-flow graph to catch novel mule patterns beyond hand-written rules. |
| Frontend | React 18 + Vite + TailwindCSS | Clean, fast, modern UI. |
| Timeline Visualization | vis-timeline | Millisecond-precise unified timeline of calls, IP sessions, and transfers. |
| Graph Visualization | Cytoscape.js | Interactive money-flow network graph, reads from Neo4j. |
| Map Visualization | Leaflet | ST-DBSCAN heatmap of suspect physical locations. |
| **Reporting (NEW)** | WeasyPrint / python-docx | Auto-generates STR (Suspicious Transaction Report) and LERS draft documents. |
| Deployment | Docker Compose | One command to spin up Frontend, Backend, Postgres, Neo4j. |

---

## 🔄 2. Data Pipeline (v2)

### STEP 1: Multi-Format Ingestion — Bulletproof Template Engine

**Input:** Raw Bank PDFs, CDR CSVs, IPDR CSVs.

**Bank Statement Parser — 3-Tier Fallback + Template Engine:**
1. **Tier 1:** `pdfplumber.extract_tables()` for digital-native PDFs.
2. **Tier 2:** PaddleOCR PP-Structure for scanned PDFs — converts pages to images, detects table grids, outputs HTML tables.
3. **Tier 3:** Regex extraction of UPI narrations (e.g., `9876543210@okhdfc`) from raw text.

**Template Engine (new, full scope):**
- Pre-configure **10–15 real Indian bank statement formats** (SBI, HDFC, ICICI, Axis, BoB, Kotak, PNB, Union Bank, Canara, IDBI, co-operative bank formats, etc.), each mapped to a JSON template describing column layout, header row offsets, date formats, and debit/credit conventions.
- **Manual Mapping UI:** if a new/unknown format is uploaded and auto-detection fails, the officer is shown a raw table preview with dropdowns to map columns (`this column = Date`, `this column = Debit Amount`, etc.). Once mapped, the template is saved and reused automatically for future files of that format.
- Template store lives in Postgres (`bank_templates` table) so it grows over time without code changes.

**CDR Parser:** Polars loads CSV, extracts Calling/Called Party, Time, Cell ID, Lat/Lon.

**IPDR Parser:** Polars lazy-loads massive CSVs, extracts Public IP, NAT Port, Private IP, Session Start/End.

---

### STEP 2: Entity Resolution ("The Glue")

**Input:** Raw parsed rows → **Output:** Unified Entities and Events tables.

- **UPI Bridge:** Link Bank Account ↔ Phone Number via the 10-digit number embedded in the UPI ID.
- **CGNAT Defeat:** Link Phone Number ↔ IP Address by matching Bank Login IP to IPDR Public IP + NAT Port session mapping.
- **Normalization:** Convert all timestamps to IST Epoch. Standardize column names (e.g., "Withdrwl Amt" and "Debit" → `amount_debit`) using the Template Engine's per-bank mapping plus RapidFuzz for anything unmapped.
- **Sync strategy — Postgres is the absolute source of truth; Neo4j is a read-model/projection, never written to first:**
  1. On file upload, entity resolution writes to **Postgres first**, inside a transaction.
  2. **Only after that Postgres transaction commits**, a background task pushes the new nodes/edges into Neo4j.
  3. If Neo4j is down or the push fails, Postgres data is untouched and safe — the graph can be **fully rebuilt from Postgres at any time** via a replay script.
  - This avoids race conditions from trying to keep two databases in lockstep, and means a Neo4j crash is never a data-loss event — it's just a "rebuild the projection" event.

---

### STEP 3: Cross-Dataset Fusion ("The Brains")

**Input:** Unified timeline → **Output:** Correlations, Anomalies, Suspect Networks.

**Temporal Fusion (Timeline Rules):**
| Rule | Condition |
|---|---|
| Grooming Call | Suspect calls victim → Victim transfers money within 30 mins. |
| Digital Alibi | Suspect IP session active during bank login/transfer. |
| Rapid Layering | Money lands in Account A → Moves to Account B within 10 mins. |

**Graph Fusion — Neo4j (primary), NetworkX (fallback):**

Money-flow graph (Accounts/UPIs as nodes, transfers as edges) is built and queried live via Cypher:

```cypher
// Circular laundering loop (smurfing ring)
MATCH p=(a:Account)-[:TRANSFER*2..5]->(a)
RETURN p

// Mastermind detection: high in-degree, low out-degree
MATCH (n:Account)
RETURN n,
       size((n)<-[:TRANSFER]-()) AS in_deg,
       size((n)-[:TRANSFER]->()) AS out_deg
ORDER BY in_deg DESC, out_deg ASC
LIMIT 5

// Shortest laundering path between two flagged accounts
MATCH p = shortestPath((a:Account {id:$id1})-[:TRANSFER*]-(b:Account {id:$id2}))
RETURN p
```

A `USE_NEO4J` feature flag lets the backend fall back to in-memory NetworkX (`nx.simple_cycles`, `nx.in_degree_centrality`) if Neo4j is unreachable — a safety net for demo day.

**Spatio-Temporal Fusion (ST-DBSCAN):**
- Feed CDR Lat/Lon/Time into ST-DBSCAN.
- If Suspect A and Suspect B ping the same tower within a 5-minute window, flag as **"Physically Co-located."**

---

### STEP 4: Anomaly & Risk Scoring — Real ML

**Input:** Fusion outputs, entity feature vectors → **Output:** Risk scores per entity.

**Layer 1 — Rule-based scoring (baseline, always on):**
- Rapid Layering = **+0.9 Risk**
- Circular Flow = **+0.8 Risk**

**Layer 2 — Isolation Forest (unsupervised anomaly detection):**
- Generate 50,000–100,000 synthetic labeled transactions (mule vs. legitimate) covering realistic Indian banking patterns.
- Train scikit-learn `IsolationForest` on transaction-level features: amount, frequency, in/out ratio, time-of-day, layering depth, degree centrality (pulled from Neo4j).
- Evaluate with a held-out synthetic test set. Produce a **precision/recall table and ROC curve** for the pitch deck — this is a real, defensible metric, not a hand-wave.

**Layer 3 — GraphSAGE (graph neural network, primary goal) with Node2Vec as safety net:**
- Build node feature vectors (transaction volume, degree, centrality, temporal patterns) over the Neo4j money-flow graph.
- Train a GraphSAGE model (PyTorch Geometric, CPU) to learn embeddings that separate mule accounts from legitimate ones, catching patterns the hand-written rules miss (e.g., novel smurfing topologies).
- **⚠️ Build Checkpoint — Day 11:** PyTorch Geometric on CPU-only environments can hit dependency hell (especially `torch-scatter`/`torch-sparse` needing a working C++ toolchain). Set a hard cutoff: if PyG isn't cleanly installed and training by Day 11, **pivot immediately to `Node2Vec`** instead of burning more days on the install.
  - Node2Vec runs directly on top of NetworkX or Neo4j using standard Python — no C++ compiler dependency.
  - It generates graph embeddings much faster on CPU.
  - The demo narrative is unaffected either way: **Graph embeddings → Logistic Regression → Mule Classification** still gives judges the same "wow" factor, whether the embeddings come from GraphSAGE or Node2Vec.
- Report embedding-based classification metrics alongside the Isolation Forest baseline — showing a genuine model progression (rules → unsupervised ML → graph ML) is a strong technical narrative for judges, regardless of which embedding method ships.

**Aggregation:** Combine rule-based + Isolation Forest + GraphSAGE scores into a final weighted risk score per entity. Flag accounts with **Risk > 0.8** as **"Mule Accounts."**

---

### STEP 5: Visualization & Reporting

| Panel | Description |
|---|---|
| Timeline Panel | `vis-timeline` — the "Smoking Gun" moment (Call + IP + Transfer aligned in seconds). |
| Network Panel | Cytoscape.js — cycles highlighted in red. **Never queries Neo4j directly**; see data flow note below. |
| Map Panel | Leaflet — ST-DBSCAN heatmaps of suspect locations. |
| Risk Panel (NEW) | Model breakdown per entity: rule score, Isolation Forest score, GraphSAGE score, final weighted risk. |
| Report Panel | Auto-generated investigation report, STR, and LERS draft (see Step 6). |

**⚠️ Data Flow Rule — React never talks to Neo4j directly:**

```
React Frontend  ➔  FastAPI Backend  ➔  Neo4j (Cypher query)
                                    ➔  FastAPI formats result as JSON,
                                       applies risk scores & node colors
                ⬅  React Frontend  ⬅  (Cytoscape.js renders the JSON)
```

- Neo4j is never exposed to the browser — it sits entirely behind FastAPI.
- This keeps the architecture secure (no direct DB access from client-side code) and lets the backend enrich the raw graph (attach risk scores, assign node colors for flagged/mule accounts, etc.) before the frontend ever sees it.
- All Cytoscape.js rendering in the Network Panel consumes a plain JSON payload from a FastAPI route (`routes_fusion.py`), not a Neo4j driver in the browser.

---

### STEP 6: Automation — STR Generation & LERS Drafting (NEW)

**STR (Suspicious Transaction Report) Generator:**
- Auto-fills the FIU-IND STR template from case data: entity details, transaction chain, risk score, evidentiary hashes.
- Outputs a formatted PDF, ready for officer review and filing.

**LERS (Legal Emergency Request System) Draft Generator:**
- Auto-fills a LERS request template (suspect phone number, IMEI, date range, requesting officer, case ID) from case data.
- Outputs a `.docx`/`.pdf` **draft only** — the officer reviews, signs, and sends manually through proper legal channels.
- **Deliberately no auto-send/email automation.** Auto-dispatching legal requests to telecom operators from a prototype breaks the air-gapped pitch (it requires an outbound network call) and creates an operational/legal liability. The tool's job is to save the officer's paperwork time, not to act autonomously on legal instruments.

---

## 🗺️ 3. Demo Scenarios

### Scenario A: UPI Investment Scam ("The Smoking Gun")
- **Data:** Victim's Bank PDF, Suspect's CDR, Suspect's IPDR.
- **Story:** Suspect calls victim at 14:02 → IP logs into victim's net-banking at 14:05 → ₹50,000 transferred at 14:08 → Money hops to 3 mule accounts by 14:12.
- **UI Highlight:** Unified timeline aligning perfectly + Isolation Forest flags the mule accounts independently of the rules.

### Scenario B: Loan App Extortion (The Network)
- **Data:** 5 different Bank CSVs (in 5 different real bank formats, to show off the Template Engine), 1 Mastermind CDR.
- **Story:** Mastermind phone linked to 5 different mule VPAs.
- **UI Highlight:** Network Panel (fed by a FastAPI route running the Cypher query server-side) showing the mastermind at the center, circular flows highlighted in red, plus a graph-embedding plot (GraphSAGE or Node2Vec) showing mule accounts clustering separately from legitimate ones.

### Scenario C: SIM-Swap + Physical Co-location (The Bonus)
- **Data:** CDR showing a sudden gap (SIM swap), IPDR showing new IMEI, Bank CSV showing NEFT transfer.
- **Story:** Suspect A and Suspect B meet at a location, then SIM swap happens.
- **UI Highlight:** ST-DBSCAN heatmap on Leaflet map proving physical co-location before the fraud.

### Scenario D (NEW, if time allows): Unknown Bank Format
- **Data:** A deliberately "unsupported" bank statement format not in the pre-built template list.
- **Story:** Upload fails auto-detection → officer manually maps 4-5 columns in the UI → template is saved → system parses correctly and reuses the mapping for a second file of the same format.
- **UI Highlight:** Demonstrates the self-healing Template Engine live — a strong "robustness" story for judges beyond the three core fraud scenarios.

---

## 🚀 4. Execution Timeline (2+ Week Plan)

### Week 1 — Foundation & Core Pipeline

**Days 1–2: Setup & Data Prep**
- [ ] Docker Compose: FastAPI + Postgres + Neo4j + React.
- [ ] Source/generate 10–15 real bank statement format samples.
- [ ] Write synthetic data generators for Scenarios A, B, C, D.
- [ ] Install and smoke-test: pdfplumber, paddleocr, polars, neo4j-driver, networkx, st-dbscan, scikit-learn, PyTorch Geometric.

**Days 3–5: Ingestion & Template Engine**
- [ ] Build Bank Parser (Tier 1 pdfplumber, Tier 2 PaddleOCR, Tier 3 regex).
- [ ] Build Template Engine: JSON template schema, 10–15 pre-built templates.
- [ ] Build Manual Mapping UI (column-mapping dropdowns, save-as-template flow).
- [ ] Build CDR Parser and IPDR Parser (Polars).

**Days 6–7: Entity Resolution**
- [ ] UPI Bridge (bank ↔ phone).
- [ ] CGNAT Defeat (phone ↔ IP).
- [ ] Timestamp/column normalization.
- [ ] Postgres ↔ Neo4j sync (ETL on entity resolution).

### Week 2 — Fusion, ML & Frontend

**Days 8–9: Fusion Engine**
- [ ] Temporal Rules (Grooming Call, Digital Alibi, Rapid Layering).
- [ ] Neo4j Cypher queries for cycle detection & mastermind centrality (+ NetworkX fallback flag).
- [ ] ST-DBSCAN spatio-temporal clustering.

**Days 10–12: Machine Learning Layer**
- [ ] Generate 50k–100k synthetic labeled transactions.
- [ ] Train and evaluate Isolation Forest (precision/recall, ROC curve).
- [ ] Build node features over the Neo4j graph and train GraphSAGE.
- [ ] Combine rule-based + ML scores into final weighted risk engine.

**Days 13–14: Frontend Dashboard**
- [ ] React + Tailwind + Cytoscape (Neo4j-backed) + vis-timeline + Leaflet.
- [ ] File Upload UI with Template Engine integration.
- [ ] 4-panel Fusion Dashboard: Timeline / Network / Map / Risk Breakdown.
- [ ] Entity Profile View.

### Week 3 (buffer, if 3-week window) — Reporting & Polish

**Days 15–17: Automation & Reporting**
- [ ] STR PDF generator (FIU-IND format, evidentiary hashes).
- [ ] LERS draft generator (docx/PDF, manual send only).
- [ ] End-to-end test across all 4 scenarios.

**Days 18–19: Hardening**
- [ ] Load-test with 5M+ row IPDR files (Polars lazy eval).
- [ ] Error handling/UX for parser failures, Neo4j downtime fallback.
- [ ] Security pass: input validation, file type checks, no external calls.

**Days 20+: Demo Prep**
- [ ] Record 2-minute backup demo video (in case live demo fails).
- [ ] Precompute/cache all 4 scenarios' fusion outputs as instant-load fallbacks.
- [ ] Prepare "Air-Gapped Forensic Integrity" and "Model Progression" pitch slides.
- [ ] Dry-run the full pitch + demo at least twice.

---

## 🗂️ 5. Folder Structure (v2)

```
trinetra/
├── docker-compose.yml          # FastAPI + Postgres + Neo4j + React
├── README.md
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                  # includes USE_NEO4J feature flag
│   │   ├── api/
│   │   │   ├── routes_upload.py
│   │   │   ├── routes_templates.py     # manual mapping UI endpoints
│   │   │   ├── routes_entities.py
│   │   │   ├── routes_fusion.py
│   │   │   ├── routes_risk.py          # ML risk breakdown endpoint
│   │   │   └── routes_report.py        # STR + LERS draft endpoints
│   │   │
│   │   ├── parsers/
│   │   │   ├── bank_parser.py
│   │   │   ├── template_engine.py      # NEW: config-driven column mapping
│   │   │   ├── cdr_parser.py
│   │   │   ├── ipdr_parser.py
│   │   │   └── ocr_engine.py
│   │   │
│   │   ├── resolution/
│   │   │   ├── upi_bridge.py
│   │   │   ├── cgnat_bridge.py
│   │   │   └── normalizer.py
│   │   │
│   │   ├── fusion/
│   │   │   ├── temporal_rules.py
│   │   │   ├── graph_engine_neo4j.py   # NEW: Cypher queries
│   │   │   ├── graph_engine_networkx.py# fallback
│   │   │   └── spatial_engine.py
│   │   │
│   │   ├── ml/
│   │   │   ├── data_generator.py       # NEW: synthetic labeled transactions
│   │   │   ├── isolation_forest.py     # NEW
│   │   │   ├── graphsage_model.py      # NEW
│   │   │   └── risk_aggregator.py      # NEW: combines rule + ML scores
│   │   │
│   │   ├── models/
│   │   │   ├── db_models.py            # Postgres (SQLAlchemy)
│   │   │   ├── graph_models.py         # NEW: Neo4j node/edge schema
│   │   │   └── schemas.py              # Pydantic
│   │   │
│   │   ├── reports/
│   │   │   ├── str_generator.py        # NEW
│   │   │   └── lers_draft_generator.py # NEW, draft-only
│   │   │
│   │   └── db/
│   │       ├── postgres.py
│   │       ├── neo4j_client.py         # NEW
│   │       └── migrations/
│   │
│   └── tests/
│       ├── test_parsers.py
│       ├── test_template_engine.py
│       ├── test_resolution.py
│       ├── test_fusion.py
│       └── test_ml.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── TemplateMappingModal.jsx  # NEW: manual column mapping UI
│   │   │   ├── TimelinePanel.jsx
│   │   │   ├── NetworkPanel.jsx
│   │   │   ├── MapPanel.jsx
│   │   │   ├── RiskBreakdownPanel.jsx    # NEW
│   │   │   ├── EntityProfile.jsx
│   │   │   └── ReportButtons.jsx         # STR + LERS draft downloads
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   └── ScenarioSelect.jsx
│   │   └── styles/index.css
│   └── public/
│
├── data/
│   ├── synthetic_generators/
│   │   ├── gen_scenario_a.py
│   │   ├── gen_scenario_b.py
│   │   ├── gen_scenario_c.py
│   │   ├── gen_scenario_d.py             # NEW: unknown format demo
│   │   └── gen_ml_training_data.py       # NEW: 50k-100k transactions
│   ├── bank_templates/                   # NEW: 10-15 JSON templates
│   │   ├── sbi.json
│   │   ├── hdfc.json
│   │   ├── icici.json
│   │   └── ...
│   ├── scenario_a/
│   ├── scenario_b/
│   ├── scenario_c/
│   └── scenario_d/
│
├── ml_artifacts/                         # NEW
│   ├── isolation_forest.pkl
│   ├── graphsage_model.pt
│   └── metrics/
│       ├── roc_curve.png
│       └── precision_recall.json
│
├── scripts/
│   ├── seed_demo.sh
│   ├── reset_db.sh
│   ├── train_ml_models.sh                # NEW
│   └── rebuild_neo4j_from_postgres.sh    # NEW: replay Postgres → Neo4j projection
│
└── docs/
    ├── PROJECT_TRINETRA_v2.md            # this doc
    ├── pitch_slide.md
    ├── model_progression_slide.md        # NEW: rules → IF → GraphSAGE story
    └── architecture_diagram.png
```

---

## 🎤 6. The Pitch (v2)

> "We built TRINETRA, a 100% local, air-gapped forensic fusion engine. For Surat Police, data privacy is non-negotiable — nothing leaves the network, ever.
>
> Our ingestion layer isn't a fragile one-off parser — it's a self-healing template engine covering 15 major Indian bank formats out of the box, and any new format can be onboarded by a non-technical officer in under a minute, with zero code changes.
>
> On the fusion side, we defeat CGNAT masking to bridge IPDR sessions to UPI narrations, and we back our money-flow graph with Neo4j — running real Cypher queries for cycle detection and mastermind centrality, not just an in-memory script.
>
> And critically, we don't stop at hand-written rules. We trained an Isolation Forest on transaction-level features, and layered a GraphSAGE graph neural network on top to catch mule account patterns no rule ever anticipated — with real ROC curves to back it up. TRINETRA doesn't just show data; it reconstructs the exact millisecond a suspect called, logged in, and moved money — and it learns to spot the fraud patterns we haven't even thought to write rules for yet."

---

### 📌 Summary
With a 2+ week build window, every "stretch" upgrade from the original 36-hour plan is now core scope: Neo4j as the primary graph layer (NetworkX kept only as a fallback), a real multi-bank template engine with a self-service mapping UI, a genuine ML progression (rules → Isolation Forest → GraphSAGE), and STR/LERS draft automation that respects the air-gapped constraint by keeping a human in the loop for anything leaving the system. Focus the final week entirely on hardening, precomputed demo fallbacks, and rehearsal — technical ambition means nothing if the live demo breaks.
