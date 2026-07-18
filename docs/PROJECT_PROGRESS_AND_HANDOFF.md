# TRI-NETRA: Project Progress & Team Handoff Log
**Last Updated:** July 2026
**Contributors:** Ayushman, Kalpit Nagar (aka gitkrypton18), Arpit, Abhishek 
**Purpose:** A detailed, simple, and mandatory guide for all teammates. This document tracks everything the Data Science/Pipeline team has accomplished so far, the files we created, and exactly what the Backend/Architecture team needs to do next.

---

## 1. The Starting Point (Ayushman's Initial Data)
When the project started, Ayushman pushed an initial batch of raw, unlinked CSV data. While it was a good starting point, we realized it had significant issues that prevented us from doing real data fusion:
- The locations (latitude/longitude) were completely random.
- Call durations and timestamps didn't logically match up.
- The `Subscriber_ID` column was corrupted (it mapped to different phones and IMEIs in different files).
- Most importantly, there were no guaranteed overlaps across the Bank, CDR (Call Details), and IPDR (Internet Sessions) datasets to actually test our fraud detection engine.

**Action Taken (by Kalpit):** We deprecated that initial raw data. Kalpit built a robust synthetic data generator to create a massive, perfectly interlocking dataset of **251,000 records** spanning the full calendar year of 2025. 

---

## 2. The Current Data Structure (Phase 0 Completed)
We successfully generated and cleaned the new data. You will find the final, ready-to-use data inside the `data/final/` folder.

### The Final Datasets
1. **`bank_transactions.csv` (100,000 rows):** A central payment ledger containing both sender and receiver metadata.
2. **`cdr_final.csv` (100,000 rows):** Telecom call detail records.
3. **`ipdr_final.csv` (50,000 rows):** ISP internet session logs.

### The "Ground Truth" (Do Not Expose to the Pipeline)
*   **File:** `data/internal/ground_truth.json`
*   **What it is:** During data generation, we secretly injected **40 coordinated fraud sequences** into the data.
*   **Why we need it:** We use this file to mathematically prove that our fusion algorithms are actually catching the bad guys.

---

## 3. The Intelligence Pipeline (Built by Kalpit Nagar / gitkrypton18)
With the data ready, **Kalpit Nagar (gitkrypton18)** wrote the core intelligence algorithms in raw Python. These scripts live in the `pipeline/` folder and do the heavy lifting of connecting the dots. Kalpit single-handedly fulfilled Hackathon requirements KO-1 through KO-5 by building the modules below.

### Step 0: Multi-Format Ingestion Engine
*   **The Script:** `pipeline/ingestion_engine.py`
*   **What Kalpit Built:** An Object-Oriented "Template Engine" that uses `pdfplumber` to crack open heterogeneous, messy PDF bank statements.
*   **Deep Technical Audit:**
    *   **Data Cleansing:** Functions like `_parse_amount` strip out commas, currency symbols, and accounting parentheses `(500)`.
    *   **Regex UPI Mining:** Uses the regex `[\w.-]+@[\w.-]+` to automatically mine hidden VPAs out of the unstructured narration text.
    *   **Fuzzy Mapping:** The absolute genius of this script is `_map_columns()`. Instead of hardcoding column indices, it dynamically searches the header row for words like "date", "narration", and "withdrawal", making the parser immune to format changes.
*   **The Output:** A standardized CSV file that aligns perfectly with our internal `bank_transactions.csv` schema, completely satisfying the KO-1 hackathon requirement.

### Step A & C: Entity Resolution (Exact & Fuzzy Matching)
*   **The Script:** `pipeline/entity_resolution.py`
*   **What Kalpit Built:** An advanced Graph algorithm (Union-Find) equipped with fuzzy string matching.
*   **Deep Technical Audit:**
    *   **Union-Find Graph:** The mathematical heart of the entity resolver. It uses Disjoint Set Data Structures with "Path Compression" to merge A ↔ B and B ↔ C, automatically proving A ↔ C.
    *   **Exact Matching:** Iterates over Bank, CDR, and IPDR. Any shared exact Phone, Account, IP, or IMEI instantly unions the distinct records into one physical person (satisfying Handbook Section 4.2 CGNAT matching).
    *   **Tier 2 Fuzzy Matching:** If `rapidfuzz.fuzz.token_sort_ratio` > 85 (e.g. "Ayushman" vs "Ayushmann"), it merges them, saving us from typos and alias evasion.
*   **The Output:** It successfully collapses 250,000 scattered rows into exactly 4,330 real people ("canonical entities") and saves this mapping to **`data/final/entities.json`**.

### Step B & D: Temporal Fusion & Cascade Lookups
*   **The Script:** `pipeline/temporal_fusion.py`
*   **What Kalpit Built:** A mathematical sliding window engine with high-retention fallback lookups.
*   **Deep Technical Audit:**
    *   **Cascade Lookups:** Uses `pl.coalesce()` to guarantee 100% data retention. If a transaction lacks a phone number, it seamlessly falls back to searching by Account, then UPI, to find the canonical Entity ID.
    *   **Sliding Window Logic:** Groups events by `entity_id` and sorts chronologically. It opens a 30-minute mathematical window. If an entity has a Bank event, a CDR event, AND an IPDR event all inside that 30-minute span, it generates a `FusionEvent` flag.
*   **The Output:** It successfully caught all 40 of our injected ground-truth fraud sequences! Suspicious event clusters are saved to **`data/final/fusion_events.json`**.

### Step E: Mule Account Network Analysis
*   **The Script:** `pipeline/network_analysis.py`
*   **What Kalpit Built:** A directed network-graph heuristic designed to find "Pass-Through" laundering nodes.
*   **Deep Technical Audit:**
    *   **Edge Aggregation:** Uses Polars to group every transaction from Sender `X` to Receiver `Y`, summing the total money flow into a single directed edge.
    *   **Mule Heuristic:** Calculates In-Degree (victims sending money in) and Out-Degree (masterminds receiving money out). The mathematical formula `(in_deg * out_deg) * throughput_ratio * log(total_volume)` isolates mules from regular users.
    *   **Graph Plotting:** Uses `matplotlib` to draw the network, scaling node sizes by total money moved.
*   **The Output:** Identified the top 50 suspicious mule accounts (**`data/final/mule_accounts.json`**) and mapped them visually (**`data/final/mule_network.png`**).

### Step F: Device Farm Detection (IMEI/SIM Clustering)
*   **The Script:** `pipeline/device_farm_detection.py`
*   **What Kalpit Built:** An IMEI tracking tool designed to spot massive SIM-swapping.
*   **Deep Technical Audit:**
    *   **Mapping:** Scans CDRs and IPDRs. For every IMEI (physical phone), it counts exactly how many different MSISDNs (SIM cards) were plugged into it. 
    *   **Super-Linear Scoring:** The formula `(sim_count - 1)^1.8` ensures that 2 SIMs is low risk (dual-sim phone), but 7 SIMs is an exponentially massive risk.
*   **The Output:** Out of 22,525 unique devices, it found 18 highly suspicious Device Farms (**`data/final/device_farms.json`**).

### Step G: Impossible Travel (Geo-Velocity) Detection
*   **The Script:** `pipeline/impossible_travel.py`
*   **What Kalpit Built:** An absolute-physics validator for spatial coordinates.
*   **Deep Technical Audit:**
    *   **Haversine Math:** Uses trigonometry over the Earth's radius (`6371 km`) to calculate the exact distance between two GPS coordinates.
    *   **Geo-Velocity Logic:** Measures distance and time elapsed between `Event A` and `Event B`. If the calculated velocity exceeds 800 km/h (faster than a commercial jet), the person is flagged as account-sharing or using spoofed IPs.
*   **The Output:** Flagged 131,952 physically impossible location jumps (**`data/final/impossible_travel.json`**).

### Step H: Spatial-Temporal Co-location (ST-DBSCAN)
*   **The Script:** `pipeline/spatial_colocation.py`
*   **What Kalpit Built:** A 3D clustering engine to find physical criminal hideouts.
*   **Deep Technical Audit:**
    *   **Matrix Projection:** Projects curved GPS coordinates into a flat Cartesian Kilometer grid and standardizes Time into Hours.
    *   **StandardScaler Linkage:** Feeds both space and time into `StandardScaler` to create a unified 3-Dimensional Space-Time matrix where 1km ≈ 1 hour.
    *   **DBSCAN Filter:** Runs `DBSCAN` clustering, specifically filtering for `len(entity_ids) >= 2` to only flag clusters where *multiple different criminals* ping the exact same cell tower at the exact same moment.
*   **The Output:** Identified coordinated meetings and shared call-centers (**`data/final/criminal_hideouts.json`**).

### Step I: Automated STR Generation
*   **The Script:** `pipeline/str_generator.py`
*   **What Kalpit Built:** The ultimate data consolidator. A script that converts our raw anomalies into professional FIU-IND law enforcement reports.
*   **Deep Technical Audit:**
    *   **Global Gatherer:** Traverses the JSON outputs of *every* previous intelligence script to gather a complete "Intelligence Package" on a suspect.
    *   **Dynamic Risk Scoring:** Dynamically computes a final Composite Risk Score by summing the point values of every anomaly triggered.
    *   **Evidentiary Timeline:** Forensic chronological logging of exactly when the suspect triggered the anomaly windows.
    *   **Hash Integrity:** Generates a SHA256 integrity hash for legal compliance.
*   **The Output:** A beautifully formatted Markdown file (e.g., `data/reports/STR_phone6812910123.md`) satisfying Hackathon requirement KO-5 (Produce investigation-ready report).

---

## 4. What The Next Teammates Need To Do
Kalpit Nagar has completely finished the Data Engineering and Rule-Based AI Pipeline. The engine works. Now, the Backend and Architecture team needs to put this engine into a production vehicle. 

*Note: The Machine Learning Risk Scorer (Isolation Forest) mentioned in Handbook Section 5.2 has been queued for tomorrow. Do not wait for it to begin the infrastructure setup.*

**Here are the mandatory next steps for Arpit and Abhishek:**

### Step 1: Infrastructure Setup (Docker & Databases)
*   Our python scripts currently save their outputs to `.json` files. We need to upgrade this to real databases.
*   **Action:** Write a `docker-compose.yml` to spin up **PostgreSQL** (for relational data) and **Neo4j** (for graph visualization). 
*   *Note: If the team prefers cloud infrastructure, you can use Supabase instead of local PostgreSQL.*

### Step 2: Database Ingestion
*   **Action:** Write the SQL schemas and a bulk-insert script to push the 250,000 rows from `bank_transactions.csv`, `cdr_final.csv`, and `ipdr_final.csv` into the new PostgreSQL database.

### Step 3: Upgrade the Pipeline to SQL
*   **Action:** Modify `entity_resolution.py`, `temporal_fusion.py`, and `network_analysis.py` so that instead of outputting to local JSON files, they insert their results directly into PostgreSQL and map the network relationships in Neo4j via Cypher queries.

### Step 4: FastAPI Backend
*   **Action:** Scaffold out a `backend/` directory using FastAPI. Build the API endpoints that the Frontend React/Vite dashboard will use to query the PostgreSQL and Neo4j databases.

### 🚨 Important Note for Backend Team 🚨
**Before you write your SQL schemas or database ingestion scripts**, you MUST read the exact dataset specifications, column types, and schemas located in [docs/Final_Dataset_Documentation.md](file:///f:/ERAKSHAK/TRI-NETRA/docs/Final_Dataset_Documentation.md). This document contains everything you need to build the PostgreSQL tables.
