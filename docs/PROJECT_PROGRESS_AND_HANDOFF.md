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
With the data ready, **Kalpit Nagar (gitkrypton18)** wrote the core intelligence algorithms in raw Python. These scripts live in the `pipeline/` folder and do the heavy lifting of connecting the dots. 

Below is a plain-English explanation of exactly what Kalpit built:

### Step 0: Multi-Format Ingestion Engine
*   **The Script:** `pipeline/ingestion_engine.py`
*   **What it does (Plain English):** A smart tool that reads messy PDF bank statements and automatically turns them into clean Excel-style rows. It is smart enough to figure out which column is the "Date" or "Amount" even if the bank changes their PDF format, and it even searches the text to find hidden UPI IDs.

### Step A & C: Entity Resolution (Finding the Real Person)
*   **The Script:** `pipeline/entity_resolution.py`
*   **What it does (Plain English):** A script that figures out if scattered records belong to the exact same criminal. It looks for shared phone numbers, bank accounts, or physical phones (IMEIs). It also uses fuzzy matching to catch typos (like "Ayushman" vs "Ayushmann") so criminals can't hide behind fake names.
*   **Output:** `data/final/entities.json`

### Step B & D: Temporal Fusion (Catching the Timing)
*   **The Script:** `pipeline/temporal_fusion.py`
*   **What it does (Plain English):** It watches the timeline. If a single person makes a phone call, logs onto the internet, and transfers money all within a 30-minute window, this script flags it as highly suspicious.
*   **Output:** `data/final/fusion_events.json`

### Step E: Mule Account Network Analysis
*   **The Script:** `pipeline/network_analysis.py`
*   **What it does (Plain English):** It builds a map of who sent money to who. It looks for "Pass-Through Nodes" (Mules)—people who receive money from lots of victims and immediately forward it to a mastermind.
*   **Output:** `data/final/mule_accounts.json`

### Step F: Device Farm Detection
*   **The Script:** `pipeline/device_farm_detection.py`
*   **What it does (Plain English):** It tracks physical cell phones (IMEIs). If it sees that 10 different SIM cards were plugged into the exact same physical phone today, it flags it as a massive fraud device farm.
*   **Output:** `data/final/device_farms.json`

### Step G: Impossible Travel Detection
*   **The Script:** `pipeline/impossible_travel.py`
*   **What it does (Plain English):** It uses GPS and physics. If a person logs in from Delhi and then makes a transaction from Mumbai 5 minutes later, the script calculates that they would have to be traveling at 2,000 km/h. Since that's impossible, it flags them for using fake locations or sharing accounts.
*   **Output:** `data/final/impossible_travel.json`

### Step H: Spatial-Temporal Co-location (Hideout Detection)
*   **The Script:** `pipeline/spatial_colocation.py`
*   **What it does (Plain English):** It looks for physical meetings. If 5 different criminals all ping the exact same cell tower at the exact same hour, the script flags that location as a shared criminal hideout or call center.
*   **Output:** `data/final/criminal_hideouts.json`

### Step I: Automated Law Enforcement Report (STR Generator)
*   **The Script:** `pipeline/str_generator.py`
*   **What it does (Plain English):** It gathers all the flags from the scripts above and automatically writes a professional, PDF-ready Suspicious Transaction Report (STR) for the police, complete with a total Risk Score for the criminal.
*   **Output:** `data/reports/`

---

## 4. Teammate Rules & Handoff Instructions

🚨 **STRICT RULE FOR ALL TEAMMATES:** 🚨
**DO NOT modify any of the Python scripts created by Kalpit in the `pipeline/` folder.** Kalpit has heavily tested these algorithms. If you need something changed, or if you don't understand how a script works, **ask Kalpit directly.** Review the codebase before you start your own tasks.

### 🌿 Git Branching Strategy (CRITICAL)
To avoid merge conflicts, we are strictly using branch isolation for the next phases:

1.  **`main` Branch (Kalpit's Domain):** Kalpit will continue using the `main` branch tomorrow to build the final Machine Learning models (Isolation Forest). **Do not push your work to main.**
2.  **`backend` Branch (Arpit & Abhishek):** You must create and checkout a new branch named `backend`. Do all your Docker, PostgreSQL, Neo4j, and FastAPI work here.
3.  **`frontend` Branch:** We will use a totally separate branch for the React/Vite dashboard and LLM chat integrations later.

### What the Backend Team Must Do Next (on the `backend` branch):
1. **Read the Docs:** You MUST read the exact dataset specifications, column types, and schemas located in [docs/Final_Dataset_Documentation.md](file:///f:/ERAKSHAK/TRI-NETRA/docs/Final_Dataset_Documentation.md). This document contains everything you need to build the PostgreSQL tables.
2. **Infrastructure Setup:** Write a `docker-compose.yml` to spin up PostgreSQL and Neo4j. 
3. **Database Ingestion:** Write the SQL schemas and a bulk-insert script to push the 250,000 rows from `data/final/` into PostgreSQL.
4. **FastAPI Backend:** Scaffold out a `backend/` directory using FastAPI to serve this data to our future dashboard.
