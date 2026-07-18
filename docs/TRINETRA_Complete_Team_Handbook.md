# TRI-NETRA — Master Project Handbook (v3.0)
## AI-Powered Financial & Telecom Dataset Analyzer (Bank + CDR + IPDR Fusion)
### Official Problem Statement: ERH26_PS_03 | Domain: Big Data and Analytics

**Event:** E-RAKSHAK Hackathon 2026 — Organized by Surat City Police in collaboration with NEXUS NIT Surat
**Team:** Mismatch | **Mentor:** Tanish Panchal
**Build Window:** 1–28 Jul 2026 | **Presentation:** 1st week Aug 2026, SVNIT Surat
**Document Status:** Single Source of Truth — full-scope build, no artificial time/tooling constraints

---

## 0. HOW TO USE THIS HANDBOOK

This is a top-to-bottom build specification, not a slide-deck summary. It is organized so that:

- **Section 2** proves — line by line — that every sentence of the official PS03 document is answered by a named module in our system. This is the document you open if a judge or mentor asks "where in your system does requirement X live?"
- **Sections 3–10** are the engineering spec: what each module does, its inputs/outputs, its schema, its algorithms.
- **Sections 11–15** cover the bonus features, security/forensics, and scale story.
- **Sections 16–21** are team/process: roles, build plan, deployment, deliverables, risk register.
- **Appendices** hold reference material: sample formats, formulas, STR template, glossary.

Golden rule for anyone reading or building from this doc: **every feature must trace back to a row in Section 2.** If you're building something that isn't in that table, stop and ask why — either the table is missing a row (fix the table) or the feature is scope creep (cut it or park it in the bonus backlog).

---

## 1. THE PROBLEM, IN OUR OWN WORDS

### 1.1 What the official PS03 says (condensed)

> *"Cybercrimes and financial scams involve parsing mountains of raw data across different formats — thousands of rows of bank statements (Excel/PDF), Call Detail Records (CDR), and Internet Protocol Detail Records (IPDR). Manually cross-referencing these logs to find the exact moment a suspect talked on the phone, used an IP address, and moved money is an overwhelming challenge. There is a need for a tool that ingests all three dataset types, normalizes them onto a common timeline and entity model, and automatically surfaces correlations, anomalies, and money-flow networks."*

### 1.2 What Surat Police actually experiences today

An investigating officer working a financial-fraud case must:

1. Requisition bank transaction data (via legal request to the bank / RBI channel)
2. Requisition Call Detail Records (CDR) from the telecom operator (Airtel / Jio / Vi / BSNL)
3. Requisition Internet Protocol Detail Records (IPDR) from the same or a different operator
4. Open three separate Excel/PDF/CSV files, each in a different format, from a different provider
5. Manually scan thousands of rows to find moments where a call, an internet session, and a bank transfer line up in time
6. **This takes days to weeks. By the time patterns are found, mule accounts are drained and the trail is cold.**

### 1.3 What TRI-NETRA builds

A single platform where an officer uploads (or is handed) raw Bank + CDR + IPDR exports and, within minutes, sees:

- **WHO** — every identifier (phone, bank account, UPI ID, IP address, IMEI, email) resolved into one entity profile
- **WHEN** — every call, SMS, transaction, and internet session on one unified, zoomable timeline
- **WHY** — every cross-dataset link and every anomaly flag comes with a plain-language, numerically-broken-down reason — never a black-box score
- **WHO ELSE** — an interactive money-flow / communication network graph showing mule chains, masterminds, and circular flows
- **PROOF** — a one-click, evidence-grade, exportable forensic report (PDF/Word) with source citations, integrity hashes, and a court-ready evidentiary timeline

### 1.4 The one-sentence pitch

**Not three dashboards. One fused, explainable, court-ready investigation surface — where a call at 14:02, a login at 14:03, and a ₹50,000 transfer at 14:04 render as one connected, provable story.**

---

## 2. PS03 REQUIREMENTS TRACEABILITY MATRIX

This is the master cross-check. Every bullet from the official document is listed verbatim (left) against the exact module/table/screen that satisfies it (right). Nothing in this build exists outside this table; nothing in this table is left unbuilt.

### 2.1 Key Objectives

| # | Official Requirement (verbatim) | Satisfied By |
|---|---|---|
| KO-1 | Ingest and parse bank statements (Excel/PDF/CSV), CDR, and IPDR from multiple provider formats | §4 Ingestion Engine — Format Sniffer, 3 dedicated parsers, Template Engine |
| KO-2 | Normalize records onto a unified entity (number/account/IP) and time model | §5 Entity Resolution + `entities` table; §4.5 Normalizer (UTC epoch, E.164 phone, decimal amount) |
| KO-3 | Automatically correlate events across the three datasets on a common timeline | §5.3–5.4 Unified Timeline + Temporal Correlation Engine; `events` + `correlation_links` tables |
| KO-4 | Detect suspicious patterns and visualize money-and-communication networks | §6 Anomaly Engine; §7.2 Money-Flow & Comms Network Graph |
| KO-5 | Produce an investigation-ready report | §8 Reporting Engine — PDF/Word export, STR generator |

### 2.2 Functional Requirements

| # | Official Requirement | Satisfied By |
|---|---|---|
| **Multi-Format Ingestion** | | |
| FR-1.1 | Parse heterogeneous bank statement layouts (Excel, PDF, CSV) | §4.1 Bank Parser — 3-tier: structured XLSX/CSV reader, `pdfplumber`/Camelot table extraction, OCR fallback |
| FR-1.2 | Parse CDR and IPDR exports from major Indian telecom operators | §4.2, §4.3 — Airtel / Jio / Vi / BSNL column-mapping profiles |
| FR-1.3 | Schema mapping/auto-detection to a canonical internal model | §4.4 Template Engine + ML Column Classifier (bonus-grade auto-detect) |
| **Cross-Dataset Fusion** | | |
| FR-2.1 | Build a unified timeline linking calls, IP series, and transactions per entity | §5.3 Unified Timeline (`events` table, entity-partitioned) |
| FR-2.2 | Detect temporal coincidences (e.g., call + IP + transfer within a window) | §5.4 Temporal Correlation Engine — sliding ±30-min window, multi-signal scorer |
| FR-2.3 | Link accounts and numbers via shared identifiers (UPI ID, IP, IMEI, beneficiary) | §5.1–5.2 Canonical Entity Model + Exact/Fuzzy Match Tiers |
| **Anomaly & Pattern Detection** | | |
| FR-3.1 | Rules + ML for layering, rapid in-and-out transfers, structuring, and circular flows | §6.2 Rule Engine (5 detectors incl. layering & circular-flow); §6.3 ML Layer (Isolation Forest + autoencoder) |
| FR-3.2 | Risk scoring for accounts/numbers | §6.4 Risk Scoring Engine — weighted, transparent, configurable |
| FR-3.3 | Detection of mule-account behavioral signatures | §6.5 Mule Signature Detector |
| **Visualization & Reporting** | | |
| FR-4.1 | Money-flow and communication network graphs with drill-down | §7.2 Network Graph (Cytoscape.js + Neo4j backing store) |
| FR-4.2 | Filter/search by entity, amount, time window, or location | §7.4 Global Filter Bar (all dashboard views) |
| FR-4.3 | Exportable forensic report (PDF/Word) with charts and the evidentiary timeline | §8.1, §8.3 Report Generator (python-docx + WeasyPrint) |

### 2.3 Evaluation Criteria — Self-Assessment Targets

| # | Official Criterion | Our Target / Evidence |
|---|---|---|
| EC-1 | Accuracy and robustness of multi-format parsing | ≥98% row-level parse success across 6 synthetic bank templates + malformed/edge-case injected files; §19.1 |
| EC-2 | Quality of cross-dataset correlation on the unified timeline | Every correlation ships a stored, inspectable confidence breakdown (never a bare score); §19.2 |
| EC-3 | Relevance of detected anomalies (true vs. false positives) | Per-entity behavioral baselines (not global thresholds) to suppress false positives; precision/recall reported on planted cases; §19.3 |
| EC-4 | Clarity of network and timeline visualizations | Non-technical-judge test: a fresh reviewer identifies the fraud story from the dashboard alone in <60 seconds; §19.4 |
| EC-5 | Performance and scalability on large datasets | Live demo on 50K+ synthetic rows on commodity hardware + documented scale roadmap to 3B+ records; §19.5, §15 |

### 2.4 Bonus Points

| # | Official Bonus | Satisfied By |
|---|---|---|
| BP-1 | Automated Suspicious Transaction Report (STR) generation | §8.2 — full STR generator, RBI/FIU-IND-style structured template |
| BP-2 | Cross-bank and cross-operator network visualization with risk heat maps | §8.4 — multi-institution graph view + geospatial/temporal heat maps |
| BP-3 | Natural-language query ("show every transfer within 10 minutes of a call to X") | §7.6 — NLQ engine (grammar + LLM-assisted intent parsing → SQL/Cypher) |

### 2.5 Deliverables

| # | Official Deliverable | Satisfied By |
|---|---|---|
| D-1 | Working prototype/demo ingesting all three dataset types | Live deployment, §17 Deployment; §13 Demo Scenarios |
| D-2 | Fusion dashboard with a worked correlation example | §7 Dashboard; Demo Scenario A walkthrough, §13.1 |
| D-3 | Sample forensic report and visual exports | §8 sample STR + PDF export shipped in repo `/samples` |
| D-4 | Documentation (parsers, correlation logic, scoring rules) | This handbook — §4 (parsers), §5.4 (correlation logic), §6.4 (scoring rules) |

**Every cell in this table has an owner and a build-week assignment — see §18 Build Plan.**

---

## 3. SYSTEM ARCHITECTURE — OVERVIEW

```
                         ┌───────────────────────────────────────────┐
                         │              REACT DASHBOARD               │
                         │  Timeline · Network Graph · Risk Panel ·   │
                         │  Entity Profile · Heat Maps · NLQ Bar      │
                         └───────────────────┬─────────────────────┘
                                              │ REST + WebSocket
                         ┌───────────────────▼─────────────────────┐
                         │           FASTAPI APPLICATION LAYER        │
                         │  /ingest  /entities  /timeline  /graph     │
                         │  /anomalies  /reports  /nlq  /admin        │
                         └───┬──────────┬──────────┬──────────┬─────┘
                             │          │          │          │
                 ┌───────────▼──┐ ┌─────▼─────┐ ┌──▼─────┐ ┌──▼──────────┐
                 │  INGESTION    │ │  FUSION   │ │  RISK  │ │  REPORTING  │
                 │  ENGINE       │ │  ENGINE   │ │ ENGINE │ │  ENGINE     │
                 │ (parsers +    │ │ (entity   │ │ (rules │ │ (STR, PDF,  │
                 │  template     │ │ resolve + │ │ + ML)  │ │  DOCX gen)  │
                 │  engine)      │ │ correlate)│ │        │ │             │
                 └───────┬───────┘ └─────┬─────┘ └───┬────┘ └──────┬─────┘
                         │               │            │             │
        ┌────────────────▼───────────────▼────────────▼─────────────▼───────┐
        │                          DATA LAYER                                │
        │  PostgreSQL (system of record, partitioned events)                 │
        │  Neo4j (identity + money-flow + comms graph, Cypher queries)       │
        │  Elasticsearch (full-text / fuzzy entity search, NLQ index)        │
        └──────────────────────────────────────────────────────────────────┘
```

**Design principle:** a **modular monolith** at the FastAPI layer (one deployable process, five internal modules with clean function-call boundaries) sitting on **three purpose-built data stores** — Postgres for transactional integrity, Neo4j for graph traversal, Elasticsearch for search/NLQ. This gets us production-grade capability (per the suggested tech stack in PS03: *NetworkX/Neo4j, Elasticsearch, PostgreSQL/MongoDB*) without the operational overhead of splitting the application layer into network-hopping microservices before there's a scaling reason to.

---

## 4. STAGE 1 — INGESTION ENGINE

### 4.1 Bank Statement Parser (Excel / PDF / CSV)

| Sub-component | What It Does |
|---|---|
| **Format Sniffer** | Detects file type by magic bytes + extension, encoding (UTF-8/UTF-16/ISO-8859), delimiter for CSV, and whether a PDF has a text layer (`pdffonts`) or is scanned |
| **XLSX/CSV Reader** | `openpyxl` / Polars-based reader; handles merged header cells, multi-row headers, trailing summary rows, multiple sheets per workbook |
| **PDF Table Extractor** | `pdfplumber` primary, Camelot (lattice mode) fallback for ruled tables; handles multi-page statements, repeated headers per page |
| **OCR Fallback** | Tesseract + layout-aware post-processing for scanned/photographed statements (common with smaller cooperative banks) |
| **Narration Mining** | Regex + NER extractor over free-text narration fields to pull UPI IDs (`name@bank`), phone numbers, and reference numbers buried in strings like `UPI/501234567890/rahul@okaxis/PAYMENT` |
| **Hindi/Gujarati Text Handling** | Unicode-safe parsing so vernacular payee names / narrations don't corrupt column alignment; transliteration normalization for entity matching (see §5.2) |

**Bank formats explicitly supported at launch:** SBI, HDFC, ICICI, Axis, PNB, and one cooperative-bank-style unstructured PDF layout (6 templates total, expandable via the Template Engine below without new code).

### 4.2 CDR Parser (Call Detail Records)

Handles CSV/XML exports from **Airtel, Jio, Vi, BSNL** — each ships different column names, timestamp formats (some Unix epoch, some `DD-MM-YYYY HH:MM:SS`), and duration units (seconds vs. `HH:MM:SS` strings). Extracted fields: caller number, callee number, timestamp, duration, call type (voice/SMS/data), cell tower ID (CGI/LAC), IMEI, IMSI.

### 4.3 IPDR Parser (Internet Protocol Detail Records)

Handles the harder problem of **NAT'd port-mapping** — thousands of subscribers sharing a handful of public IPs, resolved via source-port + timestamp to the correct private allocation. Extracted fields: subscriber MSISDN, public IP, private IP, source port, destination IP/port, session start/end, data volume, IMEI (when present — flagged as missing when absent, never silently dropped).

### 4.4 Template Engine — Schema Auto-Detection

This is the direct build-out of **FR-1.3 ("Schema mapping/auto-detection to a canonical internal model")**.

**Two-layer approach:**

1. **Deterministic layer (fast path):** YAML/JSON template per known provider — e.g. `hdfc_savings_v2.yaml` maps `"Txn Date"`, `"Value Dt"`, `"Value Date"` → canonical `date`. New provider format = new YAML file, zero code change.
2. **ML-assisted layer (unknown format fallback — bonus-grade robustness):** when no template matches, a lightweight column-type classifier (trained on header text + sample-value statistics: date-likeness, currency-likeness, phone-likeness) proposes a best-guess mapping and surfaces it to the officer as a **one-screen manual-mapping UI** — drag each detected column onto a canonical field once, and the mapping is saved as a new template for every future file from that source. This is Demo Scenario D (§13.4): *"Unknown Bank."*

### 4.5 Normalizer

| Raw | Normalized |
|---|---|
| Mixed timestamp formats, timezones, Unix epoch | UTC epoch (ms), IST offset stored separately for display |
| `9876543210`, `+91 98765 43210`, `098765-43210` | `+91XXXXXXXXXX` (E.164) |
| `Rs. 50,000.00`, `50000/-`, `₹50,000` | Decimal, paise-precision |
| Free-text UPI narration | Structured `upi_id`, `payee_name`, `reference_no` |

**Output of Stage 1:** clean, source-tagged `raw_records` rows in PostgreSQL, each linked back to its originating file + row number (audit trail — see `raw_identifiers` table, §9).

---

## 5. STAGE 2 — FUSION ENGINE

### 5.1 Canonical Entity Model

Every phone number, bank account, UPI ID, IMEI, IP address, and email that appears anywhere in the ingested data becomes a **candidate identifier**. The Fusion Engine's job is to decide which candidate identifiers belong to the *same real-world person or device* and merge them into one `entities` row — the "who" of the investigation (satisfies **KO-2**, **FR-2.3**).

### 5.2 Entity Resolution — Two-Tier Matching

| Tier | Method | Example | Confidence |
|---|---|---|---|
| **Tier 1 — Exact Match** | Identical normalized string across sources | Phone `+919876543210` = UPI `9876543210@upi` = CDR subscriber ID `9876543210` | 1.0 — auto-merge |
| **Tier 2 — Fuzzy Match** | `rapidfuzz` token-set similarity on names, with Hindi/Gujarati transliteration normalization | "Rahul Sharma" ↔ "R. Sharma" ↔ "राहुल शर्मा" (transliterated) | >90% → suggest merge; <90% → flagged for human review in the Entity Review queue (never silently auto-merged below threshold) |

Every merge decision — automatic or human-confirmed — is logged with its evidence, so an officer (or a defense lawyer) can always ask "why does the system say these are the same person?" and get a concrete answer.

### 5.3 Event Canonicalization — The Unified Timeline

Every raw record, regardless of source, becomes one row in a single `events` table with a standard shape: `entity_id, event_type (call | sms | txn_debit | txn_credit | ip_session), timestamp_utc, amount/duration, counterparty, location, source_file_ref`. This is what makes **"one query, one timeline"** possible instead of three separate systems (**FR-2.1**).

### 5.4 Temporal Correlation Engine

**This is the heart of the "FUSION" promise and the primary evaluation criterion (EC-2).**

- **Sliding window:** ±30 minutes (configurable) around every transaction event, scanning for calls/SMS/IP-sessions involving the same or linked entities
- **Multi-signal confidence scorer** — every candidate correlation is scored on four independent, weighted signals, and the breakdown is stored, not discarded:

| Signal | What It Measures | Typical Weight |
|---|---|---|
| Temporal proximity | How close in time (closer = higher) | up to 0.35 |
| Shared identifier | Same IMEI > same cell tower > same city | up to 0.30 |
| Geospatial consistency | Locations within a configurable radius (default 5 km) | up to 0.20 |
| Behavioral pattern | Has this specific entity-pair co-occurred before? | up to 0.15 |

**Worked example (this exact output is what ships in the demo and in every exported report):**

```
Confidence: 0.91
Breakdown:
  • temporal_proximity:    0.35  (events 2.3 minutes apart)
  • shared_identifier:     0.30  (same IMEI: 123456789012345)
  • geospatial_consistency: 0.16  (locations 0.6 km apart)
  • behavioral_pattern:    0.10  (this device/entity pair has co-occurred 4 times before)
Plain-language reason: "Call at 14:02, IP session at 14:01, transfer at 14:03 —
same device, same location, 2-minute window."
```

**Output of Stage 2:** `correlation_links` rows in PostgreSQL, mirrored as edges in Neo4j for graph traversal (multi-hop mule chains, cycle detection) — satisfies **FR-2.2** and feeds directly into §7.2's network graph.

---

## 6. STAGE 3 — INTELLIGENCE / ANOMALY ENGINE

### 6.1 Behavioral Baselines

Every resolved entity gets a **personal baseline**, not a global one: typical active hours, typical transaction amounts (mean + variance), regular contacts, common cell towers/locations. New activity is scored against *that entity's own history* — this is the single biggest lever for keeping false positives low (**EC-3**), because "large transaction at 11 PM" only means something different for a salaried employee than for a business owner who always transacts late.

### 6.2 Rule-Based Anomaly Detection (Primary — Fully Explainable)

Directly implements **FR-3.1** ("layering, rapid in-and-out transfers, structuring, and circular flows"):

| Rule | Definition | What It Catches |
|---|---|---|
| **Structuring** | Multiple transactions individually just under the ₹10,000 (or ₹50,000 KYC/reporting) threshold within a short window | Deliberate threshold evasion |
| **Rapid In-Out (Layering)** | Money arrives and leaves the same account within minutes, repeated across multiple hops | Classic mule-account layering behavior |
| **Circular Flow** | A → B → C → A money loop, detected via graph cycle detection (NetworkX / Neo4j GDS) | Wash trading / fake liquidity trails |
| **Odd-Hour Activity** | Activity outside *that entity's own* typical active hours (per §6.1 baseline) | Compromised accounts, remote-controlled mule activity |
| **Device Sharing** | Same IMEI appearing across 5+ distinct phone numbers within 24 hours | Mule-farm SIM cycling, common in loan-app scam rings |

### 6.3 ML-Based Anomaly Detection (Secondary — Catches What Rules Miss)

- **Isolation Forest** (scikit-learn) on engineered features: transaction velocity, amount variance, network centrality (degree/betweenness from the Neo4j graph), night-activity ratio — CPU-only, fast, and interpretable via feature-contribution output
- **Optional deep layer (PyTorch autoencoder):** for teams with GPU access or cloud credits, a reconstruction-error autoencoder over the same feature set catches subtler multivariate anomalies that Isolation Forest's axis-aligned splits miss. Presented strictly as a *secondary, supporting* signal — **"unusual pattern flagged by ML"** sits alongside rule-based flags on the dashboard, never replaces them, so every alert an officer sees always has at least a partially rule-explainable reason.

### 6.4 Risk Scoring Engine

Weighted, transparent, fully configurable (no black box — satisfies the explainability half of **EC-3**):

```
Structuring detected            +25
Rapid in-out transfers          +25
Circular flow participant       +20
Odd-hour activity               +15
Shared device with flagged peer +30
ML anomaly (secondary signal)   +10
──────────────────────────────────
TOTAL: 87 / 100 → CRITICAL
```

Every point on that scale is clickable in the UI and expands to the specific transaction(s)/event(s) that earned it.

### 6.5 Mule-Account Behavioral Signature Detector

Directly implements **FR-3.3**. Composite signature built from several of the above signals firing together within a short window on a *newly opened or previously dormant* account: rapid in-out + odd-hour + shared-device-with-flagged-peer + low transaction history. Accounts matching the composite signature are surfaced in a dedicated **"Suspected Mule Accounts"** watchlist view, ranked by composite score, distinct from the general risk-score list.

---

## 7. VISUALIZATION & INVESTIGATOR DASHBOARD

### 7.1 Unified Timeline View

`vis-timeline`-based, millisecond-precision, zoomable from "whole case" down to "this specific minute." Calls, SMS, transactions, and IP sessions render as distinct, color-coded, clickable markers on one shared axis — this is the single screen most likely to make a judge instantly understand the fusion story (**EC-4**).

### 7.2 Money-Flow & Communication Network Graph

Cytoscape.js frontend, backed by Neo4j for traversal — directly implements **FR-4.1**.

- Nodes = entities (phone/account/UPI), sized by risk score, colored by role (source / mule / destination / unresolved)
- Edges = money transfers (weighted by amount) or communication events (weighted by frequency), toggleable independently or overlaid
- **Drill-down:** click any node → entity profile card; click any edge → the exact correlated event(s) with confidence breakdown from §5.4
- **Cycle highlighting:** circular-flow rings (from §6.2) auto-highlighted in red

### 7.3 Entity Profile Card

Consolidated "who is this" panel: all resolved identifiers, current risk score with breakdown, baseline behavior summary, and a mini-timeline of just this entity's activity.

### 7.4 Global Filter/Search Bar

Present on every view — filter by entity, amount range, time window, or location (implements **FR-4.2**) — and backed by Elasticsearch for fast fuzzy entity lookup even on partial names/numbers.

### 7.5 Risk Panel & Heat Maps

Sortable, filterable list of all entities by current risk score/tier (LOW/MEDIUM/HIGH/CRITICAL), each row expandable to its full scoring breakdown from §6.4. Geospatial heat map (Leaflet) shows activity density by location; temporal heat map shows activity density by hour/day — both feed into the bonus cross-institution view (§8.4).

### 7.6 Natural-Language Query Bar (Bonus — BP-3)

Implements the exact example given in the official document: *"show every transfer within 10 minutes of a call to X."*

**Architecture:**
1. Officer types a query in plain English (or Hindi/Gujarati transliteration)
2. A constrained-grammar parser first attempts to match common investigation query patterns (transfer/call/session within N minutes of Y, entity X's activity between date A and B, all entities sharing IMEI Z) — fast, deterministic, no hallucination risk
3. For queries outside the grammar, an LLM-assisted intent parser (via the Anthropic API, function-calling to a fixed set of safe query templates — **never** free-form SQL generation) extracts structured parameters and maps them onto the same safe template set
4. Templates compile to parameterized SQL (Postgres) or Cypher (Neo4j) depending on whether the query is timeline-shaped or graph-shaped, and results render on the existing timeline/graph views — the NLQ bar is a *front door* to the same visualizations, not a separate feature

This keeps the natural-language layer forensically safe: every NLQ result is traceable to a specific, auditable, parameterized query — never an opaque LLM-generated answer standing alone as evidence.

---

## 8. REPORTING & EXPORT ENGINE

### 8.1 Evidentiary Timeline Export

One-click export of the full case timeline with every event source-cited back to its originating file + row (`raw_identifiers` table) — this is what makes the output usable as **legal evidence**, not just an internal working view. Satisfies the "evidentiary timeline" clause of **FR-4.3**.

### 8.2 Automated Suspicious Transaction Report — STR Generator (Bonus — BP-1)

A structured, FIU-IND/RBI-STR-style auto-generated report, built with `python-docx`, containing:

- Case header (entities involved, date range, reporting officer, case ID)
- Narrative summary in plain language (auto-composed from the highest-weight risk factors + top correlation links)
- Full transaction schedule of the flagged account(s), with amounts, dates, and counterparties
- Risk score breakdown table (from §6.4), reproduced in full
- Correlation evidence appendix (from §5.4), each entry with its confidence breakdown
- Source citation footer on every data point, referencing the original file/row
- Officer sign-off block

A worked, filled-in sample STR ships in `/samples/sample_STR_report.docx` as part of Deliverable D-3.

### 8.3 PDF/Word Forensic Report with Charts

Full case report combining: entity profile cards, the network graph (rendered as static SVG/PNG for print), the timeline (rendered as an image strip for print), and the risk panel — generated via `python-docx` (Word) and WeasyPrint (PDF from the same HTML template, so both formats stay in sync). Satisfies the "PDF/Word... with charts and the evidentiary timeline" clause of **FR-4.3** precisely.

### 8.4 Cross-Bank & Cross-Operator Network Visualization with Risk Heat Maps (Bonus — BP-2)

Where §7.2's graph is scoped to one active case, this view aggregates **across every ingested bank and every ingested telecom operator simultaneously** — built for exactly the scenario in Demo Scenario B (§13.2): one mastermind phone linked to mule VPAs spread across five different banks, invisible if you only ever look at one bank's data at a time. Rendered as:

- A combined network graph with bank/operator shown as a node attribute (icon/color), so cross-institution mule chains are visually obvious
- A risk heat map (geospatial + temporal) aggregated across all sources, surfacing hotspot branches/cell-towers/time-windows across the whole ingested dataset, not just one case

---

## 9. DATABASE SCHEMA (Core Tables — PostgreSQL)

| Table | Stores | Why It Matters |
|---|---|---|
| `entities` | Resolved people/devices — phone, account, UPI, IP, IMEI merged into one identity | The "who" of every investigation (§5.1) |
| `events` | Unified timeline — calls, SMS, transactions, IP sessions | The "when" — partitioned by month for scale (§5.3) |
| `correlation_links` | Cross-dataset connections with confidence scores + full breakdown | The "why" — explainable fusion (§5.4) |
| `anomaly_flags` | Detected suspicious patterns with plain-language reasons | The "what" — actionable alerts (§6) |
| `risk_scores` | Current + historical risk score per entity, with component breakdown | Feeds §6.4 and §7.5 |
| `behavioral_baselines` | Per-entity normal behavior patterns | Reduces false positives (§6.1) |
| `raw_identifiers` | Audit trail — which raw file + row each entity/event came from | Legal evidence citation (§8.1) |
| `ingestion_jobs` | Tracks file upload + processing status, per-file error log | Pipeline observability (§4) |
| `entity_review_queue` | Fuzzy-match candidates below auto-merge threshold, pending human confirmation | Human-in-the-loop safety on §5.2 |
| `str_reports` | Generated STR reports, status, and officer sign-off metadata | Supports §8.2 case management |

**Graph mirror (Neo4j):** `entities` become `(:Entity)` nodes; `correlation_links` and transfer/communication events become typed relationships (`:TRANSFERRED_TO`, `:CALLED`, `:CORRELATED_WITH`), enabling native multi-hop and cycle-detection queries that would otherwise require expensive recursive SQL.

**Search mirror (Elasticsearch):** entity display names, all known identifiers, and free-text narration fields are indexed for fuzzy/partial search, powering both §7.4's search bar and the NLQ engine's entity-resolution step.

---

## 10. API DESIGN (FastAPI)

| Endpoint | Method | Purpose |
|---|---|---|
| `/ingest/upload` | POST | Upload a raw file (bank/CDR/IPDR); kicks off async ingestion job |
| `/ingest/jobs/{id}` | GET | Poll ingestion job status/errors |
| `/ingest/map-columns` | POST | Submit manual column mapping for an unrecognized template (§4.4) |
| `/entities/{id}` | GET | Full entity profile card |
| `/entities/{id}/review` | POST | Confirm/reject a fuzzy-match suggestion (§5.2) |
| `/timeline` | GET | Unified timeline, filterable by entity/time/type |
| `/graph` | GET | Network graph data (scoped to case or cross-institution per §8.4) |
| `/anomalies` | GET | List anomaly flags, filterable by rule/entity/severity |
| `/risk/{entity_id}` | GET | Full risk score breakdown |
| `/reports/str/{entity_id}` | POST | Generate an STR for an entity (§8.2) |
| `/reports/case/{case_id}` | POST | Generate full forensic PDF/Word case report (§8.3) |
| `/nlq` | POST | Natural-language query endpoint (§7.6) |
| `/admin/templates` | GET/POST | Manage bank/CDR/IPDR parsing templates |

Auto-generated interactive Swagger documentation at `/docs` — satisfies the "API docs" presentation requirement (§20).

---

## 11. TECH STACK

Aligned directly to the "Suggested Tools/Technologies" list in the official PS03 document — every suggested tool is used with a stated purpose, nothing is included decoratively:

| Layer | Tool | Role |
|---|---|---|
| Backend framework | Python + FastAPI | Async application layer, auto Swagger docs |
| Data processing | Pandas / Polars | Parsing, cleaning, feature engineering |
| Relational store | PostgreSQL | System of record — entities, events, correlations, audit trail |
| Graph store | **Neo4j** (+ NetworkX for local algorithmic work — cycle detection, centrality) | Money-flow/comms graph, multi-hop mule-chain traversal |
| Search | **Elasticsearch** | Fuzzy entity search, NLQ entity resolution |
| ML — anomaly detection | scikit-learn (Isolation Forest, primary) / PyTorch (autoencoder, secondary) | Explainable-first anomaly detection |
| PDF parsing | pdfplumber (primary), Camelot / Apache PDFBox-equivalent fallback | Bank statement table extraction |
| Spreadsheet parsing | OpenpyXL / Polars | XLSX ingestion |
| Frontend | React + Vite + Tailwind | Dashboard application |
| Timeline | vis-timeline | Millisecond-precision unified timeline |
| Network graph (frontend) | Cytoscape.js | Interactive link analysis |
| Charts (reports) | D3.js | Report chart rendering |
| Maps | Leaflet | Geospatial heat maps |
| Reports | python-docx + WeasyPrint | STR + forensic PDF/Word generation |
| NLQ | Constrained grammar parser + Anthropic API (function-calling, template-bound) | Natural-language query bar |
| Data (demo) | Synthetic generator (Python, Faker + custom fraud-pattern injectors) | Controls the demo narrative, guarantees planted cases are always present |

---

## 12. BONUS FEATURES — CONSOLIDATED SUMMARY

All three official bonus points are treated as **first-class, fully built features**, not slide-only aspirations:

| Bonus | Status | Detail Section |
|---|---|---|
| Automated STR generation | Built | §8.2 |
| Cross-bank/cross-operator network + risk heat maps | Built | §8.4 |
| Natural-language query | Built | §7.6 |

**Additional self-initiated enhancements (beyond the official bonus list), included because they materially strengthen the four evaluation criteria without adding architectural risk:**

| Enhancement | Why It's Worth Building | Strengthens |
|---|---|---|
| ML-assisted schema auto-detection for unknown bank formats | Turns "self-healing robustness" into a live-demoable capability, not just a claim | EC-1, EC-5 |
| Suspected Mule Accounts watchlist view | Gives investigators a standing, always-updated view rather than requiring them to re-run analysis per case | EC-3 |
| Chain-of-custody hashing on every export | Makes exported reports admissible-evidence-grade, not just readable | EC-2, D-3 |
| Case-wise tagging & notes | Lets multiple officers collaborate on one case over time | Usability (soft factor under EC-4) |

---

## 13. DEMO SCENARIOS (Planted, Synthetic, Reproducible)

| Scenario | Story | What It Proves |
|---|---|---|
| **A — UPI Scam** | Suspect calls victim → victim logs into net-banking → ₹50,000 transferred → money hops through 3 mule accounts within minutes | Core temporal fusion (§5.4) end-to-end |
| **B — Loan-App Mule Network** | One mastermind phone linked to 5 mule VPAs spread across different banks | Multi-template ingestion (§4.4) + cross-bank graph (§8.4) |
| **C — SIM Swap** | CDR shows a service gap → a new IMEI appears in IPDR under the same MSISDN → a bank transfer follows immediately | Device-sharing / odd-pattern anomaly detection (§6.2) |
| **D — Unknown Bank Format** | An unsupported bank export is uploaded → officer manually maps 4 columns once in the UI → instant, correct parsing thereafter | Template Engine self-healing robustness (§4.4) |
| **E — Circular Flow (bonus scenario)** | A → B → C → A money loop across three accounts at two different banks | Cycle detection (§6.2) + cross-bank graph (§8.4) |
| **F — NLQ Walkthrough (bonus scenario)** | Officer types *"show every transfer within 10 minutes of a call to [suspect number]"* into the NLQ bar | Natural-language query engine (§7.6) end-to-end |

Every scenario is generated by the synthetic data pipeline with a **fixed random seed**, so the exact same fraud story reproduces identically on every demo run — no dependence on live data or network conditions for the core narrative.

---

## 14. SECURITY, PRIVACY & FORENSIC INTEGRITY

Because this system is designed to produce *evidence*, not just insight, integrity controls are treated as core requirements, not afterthoughts:

- **Chain of custody:** every ingested file is SHA-256 hashed on upload; the hash is stored and re-verified on every export, so tampering after ingestion is detectable
- **Audit logging:** every query, export, and entity-merge decision is logged with actor, timestamp, and the exact parameters used
- **Source provenance:** every fact displayed anywhere in the UI carries a pointer back to `raw_identifiers` — the specific file and row it came from
- **Access control (production roadmap item):** role-based access (Investigating Officer / SHO / Legal Advisor tiers) — designed now, enforced fully at the "Surat scale" phase (§15)
- **Data privacy:** all processing is local/on-prem in the prototype; no case data leaves the deployment environment; the NLQ LLM call (§7.6) is template-bound and never receives raw case data beyond the specific structured parameters needed for a single query

---

## 15. SCALABILITY ROADMAP

| Phase | Scale | Infrastructure | What Changes |
|---|---|---|---|
| **Now (Prototype)** | 50K+ records | Single host: PostgreSQL + Neo4j + Elasticsearch + FastAPI | This is the live-demoed build — nothing here is a slide-only claim |
| **Surat (Deployment)** | 10M records | Postgres read replicas + Redis cache + dedicated API tier | Add caching, connection pooling, RBAC enforcement |
| **Gujarat (Regional)** | 500M records | Citus (Postgres sharding) + Neo4j cluster + Elasticsearch cluster | Database shards, distributed graph queries, distributed search |
| **India (National)** | 3B+ records | Kafka streaming ingestion + Flink real-time correlation + ClickHouse analytics + Kubernetes orchestration | Streaming ingestion replaces batch upload, distributed compute, auto-scaling |

**Key message for judges:** *"The architecture doesn't change shape as it scales — only the infrastructure underneath does. The modular monolith's five internal modules map 1:1 onto the microservices we'd extract at national scale."*

### What Ships Live vs. What's Documented-Only

| Feature | Built & Demoed | Documented (Architecture Slide) |
|---|---|---|
| PostgreSQL partitioning | ✅ | — |
| Neo4j graph queries | ✅ | — |
| Elasticsearch fuzzy search | ✅ | — |
| Modular monolith (FastAPI) | ✅ | — |
| Kafka + Flink streaming ingestion | — | ✅ "Future: real-time ingestion at national scale" |
| Kubernetes orchestration | — | ✅ "Future: auto-scaling" |
| Citus sharding | — | ✅ "Future: 500M+ record horizontal scale" |
| ClickHouse analytics layer | — | ✅ "Future: sub-second aggregate queries at 3B+ rows" |

---

## 16. TEAM STRUCTURE & ROLES

| Person | Role | Core Responsibility |
|---|---|---|
| **A** | Ingestion Lead | Bank/CDR/IPDR parsers, Template Engine, synthetic data generator, timezone/normalization policy |
| **B** | Fusion Lead | Entity resolution, temporal correlation engine, confidence scoring *(most evaluation-critical role — owns EC-2)* |
| **C** | Intelligence + API Lead | Anomaly rules, ML layer, risk scoring, FastAPI endpoints, Neo4j/Elasticsearch integration |
| **D** | Frontend + Reporting Lead | React dashboard (timeline, graph, risk panel, NLQ bar), STR/PDF report generator, demo narrative & rehearsal |

**Daily sync:** 15-minute standup anchored on the shared schema (`entities` + `events` + `correlation_links`). Schema changes require full-team agreement before merging — this is the one rule that protects every other team's work.

---

## 17. BUILD PLAN

| Phase | Focus | Deliverable | Traces to |
|---|---|---|---|
| **1** | Data + Parsing | Synthetic generators working; 6 bank templates; CDR/IPDR parsers ingest correctly | FR-1.1, FR-1.2 |
| **2** | Fusion + Anomaly | Entity resolution, temporal correlation with confidence breakdowns, 5 rule-based anomaly detectors | FR-2.*, FR-3.1 |
| **3** | Graph + Search Infrastructure | Neo4j graph mirror live, Elasticsearch index live, ML anomaly layer (Isolation Forest) | FR-3.1, FR-4.1 |
| **4** | API + Frontend Core | FastAPI endpoints, React timeline + network graph, risk score UI | §10, §7.1–7.5 |
| **5** | Reporting + Bonus Features | STR generator, PDF/Word export, cross-institution heat map view, NLQ bar | BP-1, BP-2, BP-3 |
| **6** | Hardening + Polish | Error handling, chain-of-custody hashing everywhere, pre-computed demo data, backup screenshots | §14, §19 |
| **7** | Demo Prep | Dry runs against all 6 scenarios, pitch refinement, Q&A prep, backup video | §13 |

**The final phase is sacred — no new features. Only polish, hardening, and rehearsal.**

---

## 18. DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND: Vercel (Always-On, Global CDN, HTTPS/HTTP2)       │
│  └── React static build                                      │
└───────────────────────────────┬───────────────────────────────┘
                                 │
┌───────────────────────────────▼───────────────────────────────┐
│  BACKEND: Dedicated host (cloud VM, never-sleeping)            │
│  └── FastAPI (systemd-managed, auto-restart on crash)          │
│  └── PostgreSQL + Neo4j + Elasticsearch co-located              │
└─────────────────────────────────────────────────────────────┘
```

**Keep-alive:** scheduled health-check ping every 10 minutes; explicit pre-warm 30 seconds before any live demo.

**Backup plans (in order of preference if the live system falters mid-demo):**
1. Full-resolution screenshots of every dashboard view, per scenario
2. 2–3 minute pre-recorded demo video covering all 6 scenarios
3. Local machine with an identical, pre-seeded deployment (nuclear option)

---

## 19. EVALUATION CRITERIA — SELF-ASSESSMENT DETAIL

### 19.1 EC-1: Parsing accuracy & robustness
Tested against 6 bank templates + deliberately malformed injected files (missing columns, merged cells, mixed encodings, scanned PDFs). Target: ≥98% row-level parse success, 100% graceful failure (no silent data loss) on the remaining rows, with every failure logged to `ingestion_jobs`.

### 19.2 EC-2: Cross-dataset correlation quality
Every correlation link ships with the full 4-signal breakdown from §5.4 — never a bare number. This is the single highest-weighted evaluation criterion and the reason the Fusion Lead role (§16) is explicitly called out as most evaluation-critical.

### 19.3 EC-3: Anomaly relevance
Per-entity behavioral baselines (§6.1) rather than global thresholds. On the planted demo cases, we report precision and recall of each rule-based detector against the known-planted ground truth, and show the ML layer's flags as a clearly-labeled secondary signal, never conflated with the primary rule-based findings.

### 19.4 EC-4: Visualization clarity
"60-second test": a reviewer with no prior context on the case is shown only the dashboard (no verbal narration) and asked to describe what happened. Success criterion: they can name the suspect, the victim, and the money's final destination within 60 seconds, using the timeline + graph alone.

### 19.5 EC-5: Performance & scale
Live demo runs on 50K+ synthetic rows on ordinary hardware, with the documented (not just claimed) scale roadmap in §15 showing exactly what infrastructure change is needed at each order-of-magnitude jump.

---

## 20. FINAL DELIVERABLES CHECKLIST

### Mapped 1:1 to the official PS03 deliverables (D-1 through D-4)

- [ ] **D-1** Working prototype/demo ingesting all three dataset types (Bank + CDR + IPDR), live-deployed
- [ ] **D-2** Fusion dashboard with a fully worked correlation example (Demo Scenario A minimum; all 6 scenarios ideally)
- [ ] **D-3** Sample forensic report (PDF + Word) and sample STR report, plus visual exports (graph/timeline images)
- [ ] **D-4** Documentation: parsers (§4), correlation logic (§5.4), scoring rules (§6.4) — this handbook

### Presentation-Day Checklist

- [ ] Live demo: 5–7 minute walkthrough of at least one fraud case start to finish
- [ ] Architecture slides: "Built for prototype, designed for production" (§15)
- [ ] API docs: auto-generated Swagger at `/docs`
- [ ] Q&A prep: be ready to explain the correlation confidence formula, the timezone/normalization policy, and the false-positive mitigation strategy in plain language
- [ ] Backup screenshots + video for every demo scenario
- [ ] Bonus features explicitly called out during the pitch (STR generator, cross-institution heat map, NLQ) — don't let judges discover them only if they ask

---

## 21. RISK REGISTER & ANTICIPATED PRODUCTION QUESTIONS

| Risk / Likely Judge Question | Prototype Answer | Production Answer |
|---|---|---|
| "What happens with 10M+ rows?" | Pre-computed demo dataset at 50K rows, documented Postgres partitioning | Citus sharding + read replicas (§15) |
| "Isn't your correlation just coincidence?" | Every link shows its 4-signal breakdown — challenge any single link live | Same methodology, tuned weights per crime-pattern type over time with officer feedback |
| "How do you avoid false positives?" | Per-entity baselines, not global thresholds; rule-based primary + ML secondary, never inverted | Ensemble models + structured feedback loop from investigating officers |
| "What if a new bank format shows up?" | Live-demoable manual column-mapping UI (Scenario D), becomes a reusable template | Same, plus the ML column classifier improves with volume |
| "Is this admissible in court?" | Every fact traces to a hashed source file/row; STR follows structured reporting format | Add formal digital-evidence certification workflow, RBAC + MFA, encryption at rest/transit |
| "What about data privacy?" | Local/on-prem processing, no data leaves environment, NLQ is template-bound | Air-gapped deployment option, anonymization pipeline for training/testing data |
| "Concurrent users?" | Single demo login | Load balancer + read replicas + connection pooling |
| "System reliability?" | systemd auto-restart | Kubernetes health checks + circuit breakers + graceful degradation |

---

## 22. WHAT ACTUALLY WINS THIS COMPETITION

### The Golden Rules

1. **Explainability beats complexity.** A correlation with a full confidence breakdown beats a black-box neural network every time — this is why the rule-based layer is always primary and the ML layer is always clearly labeled secondary.
2. **Build less, explain more, but build all four bonus-worthy features.** A working timeline + graph + risk panel + STR + heat map + NLQ, all genuinely functional, beats twenty half-built features.
3. **The demo tells a story.** Never "here are our features" — always "here's how we caught this fraudster, and here's the exact evidence."
4. **Always have backups.** Screenshots, video, a local machine. When something fails during a live demo — not if — you keep going without losing the room.

---

## APPENDIX A — Glossary

| Term | Meaning |
|---|---|
| CDR | Call Detail Record — telecom log of calls/SMS: who, when, duration, tower |
| IPDR | Internet Protocol Detail Record — telecom log of internet sessions: who, when, IP, data volume |
| UPI | Unified Payments Interface — India's real-time payment rail; identifiers look like `name@bank` |
| IMEI | International Mobile Equipment Identity — unique per physical handset |
| IMSI | International Mobile Subscriber Identity — unique per SIM |
| CGI / LAC | Cell Global Identity / Location Area Code — identifies the serving cell tower |
| Mule account | A bank account used to receive and forward stolen/scammed funds, often opened using a stolen/rented identity |
| Structuring | Splitting a large transaction into several smaller ones to stay under a reporting threshold |
| Layering | Rapidly moving money through several accounts to obscure its origin |
| STR | Suspicious Transaction Report — the formal document banks/investigators file to flag suspected financial crime |
| E.164 | International standard format for phone numbers, e.g. `+919876543210` |

## APPENDIX B — Sample Data Formats (Canonical Fields)

**Bank transaction (canonical):** `date, value_date, description, debit, credit, balance, upi_id, payee_name, reference_no, source_bank`

**CDR (canonical):** `caller_msisdn, callee_msisdn, timestamp_utc, duration_sec, call_type, cgi, imei, imsi, operator`

**IPDR (canonical):** `subscriber_msisdn, public_ip, private_ip, src_port, dst_ip, dst_port, session_start, session_end, data_volume_mb, imei, operator`

## APPENDIX C — Confidence Score Formula Reference

```
confidence = w1·temporal_proximity + w2·shared_identifier
           + w3·geospatial_consistency + w4·behavioral_pattern

where  w1=0.35, w2=0.30, w3=0.20, w4=0.15  (default, tunable per crime-pattern type)
       each component ∈ [0, 1], normalized within its own signal
```

## APPENDIX D — Sample STR Narrative Snippet (Illustrative)

> *Entity [ID redacted] received ₹50,000 via UPI on [date/time] from an account previously uninvolved in prior transaction history with the recipient. Within 4 minutes, the full amount was forwarded across three further accounts (structuring pattern, +25), two of which share a device IMEI previously flagged in an unrelated case (+30). Total composite risk score: 87/100 — CRITICAL. Full transaction and correlation evidence follows in Appendix A of this report.*

## APPENDIX E — NLQ Grammar Examples (Deterministic Fast-Path)

```
show every transfer within <N> minutes of a call to <ENTITY>
show all activity for <ENTITY> between <DATE1> and <DATE2>
show all entities sharing IMEI <IMEI>
show the shortest path between <ENTITY_A> and <ENTITY_B>
show all accounts with risk score above <THRESHOLD>
```

---

*Document Version 3.0 — Master Handbook, Full-Scope Build.*
*Single Source of Truth for Team Mismatch. Every section traces to ERH26_PS_03. Do Not Distribute Outside Team/Mentor.*
