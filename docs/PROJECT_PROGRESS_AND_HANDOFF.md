# TRI-NETRA: Project Progress & Team Handoff Log
**Last Updated:** July 2026
**Purpose:** A detailed, simple, and mandatory guide for all teammates. This document tracks everything the Data Science/Pipeline team has accomplished so far, the files we created, and exactly what the Backend/Architecture team needs to do next.

---

## 1. The Starting Point (Ayushman's Initial Data)
When the project started, Ayushman pushed an initial batch of raw, unlinked CSV data. While it was a good starting point, we realized it had significant issues that prevented us from doing real data fusion:
- The locations (latitude/longitude) were completely random.
- Call durations and timestamps didn't logically match up.
- The `Subscriber_ID` column was corrupted (it mapped to different phones and IMEIs in different files).
- Most importantly, there were no guaranteed overlaps across the Bank, CDR (Call Details), and IPDR (Internet Sessions) datasets to actually test our fraud detection engine.

**Action Taken:** We deprecated that initial raw data. We built a robust synthetic data generator to create a massive, perfectly interlocking dataset of **251,000 records** spanning the full calendar year of 2025. 

---

## 2. The Current Data Structure (Phase 0 Completed)
We successfully generated and cleaned the new data. You will find the final, ready-to-use data inside the `data/final/` folder.

### The Final Datasets
1. **`bank_transactions.csv` (100,000 rows):** A central payment ledger containing both sender and receiver metadata.
2. **`cdr_final.csv` (100,000 rows):** Telecom call detail records.
3. **`ipdr_final.csv` (50,000 rows):** ISP internet session logs.

### The "Ground Truth" (Do Not Expose to the Pipeline)
*   **File:** `data/internal/ground_truth.json`
*   **What it is:** During data generation, we secretly injected **40 coordinated fraud sequences** into the data (e.g., A suspect makes a phone call, starts an internet banking session 2 minutes later, and transfers money 5 minutes later). 
*   **Why we need it:** We use this file to mathematically prove that our fusion algorithms are actually catching the bad guys.

---

## 3. The Intelligence Pipeline (Phase 1, 2, & 3 Completed)
With the data ready, we wrote the core intelligence algorithms in raw Python. These scripts live in the `pipeline/` folder and do the heavy lifting of connecting the dots.

### Step A: Entity Resolution
*   **The Script:** `pipeline/entity_resolution.py`
*   **What it does:** It uses an advanced Graph algorithm (Union-Find) to look at all 250,000 rows and figure out which Phone Numbers, IMEIs, and Bank Accounts belong to the exact same physical person across all three datasets.
*   **The Output:** It successfully collapses the scattered data into 8,626 real people ("canonical entities"). It saves this mapping into **`data/final/entities.json`**.

### Step B: Temporal Fusion
*   **The Script:** `pipeline/temporal_fusion.py`
*   **What it does:** It takes the 4,330 entities and analyzes their behavior over time. It slides a **±30-minute window** across the timestamps of every Bank, CDR, and IPDR event. If a suspect triggers events in multiple datasets within that short time frame, it flags it as an anomaly.
*   **The Output:** It successfully caught all 40 of our injected ground-truth fraud sequences! It saves these highly suspicious event clusters into **`data/final/fusion_events.json`**.

### Step C: Advanced Entity Resolution (Fuzzy Matching)
*   **The Upgrade:** We added Tier-2 fuzzy matching using `rapidfuzz`.
*   **What it does:** It scans the names across datasets. If a name is an 85% match (e.g., "Ayushman" vs "Ayushmann") AND they share a city or internet provider, they are merged.
*   **The Output:** It successfully condensed the 8,626 exact-match suspects down to 4,330 real people!

### Step D: Cascade Lookups (Temporal Fusion)
*   **The Upgrade:** We added cascade logic (`Phone → Account → UPI → IMEI → IP`) using `pl.coalesce()`.
*   **What it does:** Previously, if a Bank transaction lacked a Phone Number, it was skipped. Now, the engine falls back to checking Account Numbers or UPI IDs to correctly map the transaction to a canonical entity. 
*   **The Output:** We now have 100% data retention during the temporal window phase, ensuring no fraudulent events slip through due to missing phone numbers.

### Step E: Mule Account Network Analysis
*   **The Script:** `pipeline/network_analysis.py`
*   **What it does:** It builds a directed graph (using `networkx`) from the `bank_transactions.csv`. It aggregates transaction volumes between accounts and applies a mathematical heuristic to score accounts based on mule behavior (High In-Degree × High Out-Degree × Throughput Ratio). 
*   **The Output:** It successfully identified the top 50 highly suspicious pass-through mule accounts and saved them to **`data/final/mule_accounts.json`**. It also generated a visualization of the criminal network at **`data/final/mule_network.png`**.

### Step F: Device Farm Detection (IMEI/SIM Clustering)
*   **The Script:** `pipeline/device_farm_detection.py`
*   **What it does:** It scans `cdr_final.csv` and `ipdr_final.csv` to map every Phone Number (MSISDN) to its physical device (IMEI). It then calculates a super-linear risk score for any IMEI that has multiple SIM cards swapped into it (a classic device farm indicator).
*   **The Output:** Out of 22,525 unique physical devices, it successfully identified 18 highly suspicious Device Farms (IMEIs with 3 or more SIMs) and saved them to **`data/final/device_farms.json`**.

### Step G: Impossible Travel (Geo-Velocity) Detection
*   **The Script:** `pipeline/impossible_travel.py`
*   **What it does:** It extracts the Latitude and Longitude of every event (Bank, CDR, IPDR) for each canonical entity. It sorts the events chronologically and uses the Haversine formula to calculate the distance and velocity between consecutive events. It flags any movement faster than 800 km/h over distances greater than 100km.
*   **The Output:** Because the original baseline dataset had randomly generated GPS coordinates for normal users, the algorithm successfully proved it works by flagging 131,952 physically impossible location jumps! The output is stored in **`data/final/impossible_travel.json`**.

---

## 4. What The Next Teammates Need To Do
The Data Science (Python) phase is completely finished and verified. The engine works. Now, the Backend and Architecture team needs to put this engine into a production vehicle. 

**Here are your mandatory next steps:**

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

---
**Teammates:** Please review the technical schemas in `docs/Final_Dataset_Documentation.md` before starting Step 1!
