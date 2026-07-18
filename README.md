# TRI-NETRA: E-RAKSHAK Forensic Fusion Engine (ERH26_PS_03)

TRI-NETRA is an advanced Data Science intelligence engine designed to crack multi-layered financial fraud by fusing disconnected bank statements, telecom call detail records (CDRs), and internet session logs (IPDRs) into a unified forensic topology.

## Intelligence Pipeline (Data Science Layer)
The Python Data Science pipeline successfully fulfills all functional requirements of the hackathon:
*   **Step 0: Ingestion Engine** (`pipeline/ingestion_engine.py`) - Cracks PDF statements and dynamically maps heterogeneous tables.
*   **Step A/C: Entity Resolution** (`pipeline/entity_resolution.py`) - Bypasses CGNAT and merges aliases using Union-Find graphs and fuzzy matching.
*   **Step B/D: Temporal Fusion** (`pipeline/temporal_fusion.py`) - Employs a 30-minute mathematical sliding window to find simultaneous Bank/CDR/IPDR anomalies.
*   **Step E: Mule Network Analysis** (`pipeline/network_analysis.py`) - Uses `networkx` directed graphs to mathematically isolate pass-through mule nodes.
*   **Step F: Device Farm Detection** (`pipeline/device_farm_detection.py`) - Maps physical IMEIs to multiple SIM cards to catch fraud operations.
*   **Step G: Impossible Travel** (`pipeline/impossible_travel.py`) - Physics-based Geo-Velocity engine using Haversine formulas to catch impossible physical jumps.
*   **Step H: Spatial Co-location** (`pipeline/spatial_colocation.py`) - 3D Space-Time DBSCAN clustering to locate shared physical criminal hideouts.
*   **Step I: Automated STR Generator** (`pipeline/str_generator.py`) - Consolidates all pipeline outputs into a professional FIU-IND law enforcement report.

## Documentation
Please see the `docs/` directory for exhaustive technical specifications:
*   `docs/PROJECT_PROGRESS_AND_HANDOFF.md` - The master architectural progression and task assignments.
*   `docs/Final_Dataset_Documentation.md` - The exact PostgreSQL schemas and data models.
*   `docs/TRINETRA_Master_Project_Handbook.md` - The overarching strategy and hackathon requirements matrix.

## Next Steps
The team will dynamically rotate roles to migrate the local JSON outputs into PostgreSQL/Neo4j and build the FastAPI layer for the React dashboard. Machine Learning extensions (Isolation Forest) are queued for tomorrow.
