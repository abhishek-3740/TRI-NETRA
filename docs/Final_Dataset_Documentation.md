# TRI-NETRA Final Dataset Documentation

## Location: `F:\ERAKSHAK\TRI-NETRA\data\final\`

---

## 1. Dataset Summary

| File | Rows | Columns | Size | Date Range |
|---|---|---|---|---|
| `bank_transactions.csv` | 100,324 | 42 | 44.1 MB | Jan 1 – Dec 31, 2025 |
| `cdr_final.csv` | 100,040 | 24 | 26.0 MB | Jan 1 – Dec 31, 2025 |
| `ipdr_final.csv` | 50,992 | 24 | 13.6 MB | Jan 1 – Dec 31, 2025 |

**Total: ~251K records across 3 datasets, all covering the full calendar year 2025.**

---

## 2. Schemas

### 2.1 Bank Transactions (`bank_transactions.csv`)

42 columns. Models a central payment ledger view of all bank-to-bank transactions.

| # | Column | Type | Nulls | Description |
|---|---|---|---|---|
| 1 | `Transaction_ID` | string | 0% | Unique ID (e.g., `TXN0000000001`, injected: `INJ_TXN_0001`) |
| 2 | `Timestamp` | datetime | 0% | Transaction timestamp (2025 full year) |
| 3 | `Txn_Ref_Number` | string | 0% | UTR / reference number |
| 4 | `Transaction_Mode` | string | 0% | `ATM` \| `UPI` \| `Cash Deposit` \| `IMPS` \| `POS` \| `CASH` \| `NEFT` \| `RTGS` |
| 5 | `Transaction_Status` | string | 0% | `SUCCESS` \| `FAILED` \| `PENDING` |
| 6 | `Currency` | string | 0% | Always `INR` |
| 7 | `Transaction_Amount` | float | 0% | Amount in INR (Rs 50 – Rs 38.9L) |
| 8 | `Sender_Customer_ID` | string | 0% | `CUSTxxxxxxx` |
| 9 | `Sender_Bank_Name` | string | 0% | 13 banks (SBI, HDFC, ICICI, Axis, PNB, Kotak, Canara, BoB, IndusInd, Union, etc.) |
| 10 | `Sender_City` | string | 7.3% null | City of sender |
| 11 | `Sender_Account_Number` | string | 0% | 12-digit account number |
| 12 | `Sender_IFSC` | string | 0% | IFSC code |
| 13 | `Sender_Phone_Number` | int | 0% | 10-digit Indian phone number |
| 14 | `Sender_UPI_ID` | string | 0% | UPI VPA (e.g., `name@ybl`, `9876543210@paytm`) |
| 15 | `Sender_Gender` | string | 0% | `Male` \| `Female` |
| 16 | `Sender_Customer_Name` | string | 0% | Full name |
| 17 | `Sender_Email` | string | 0% | Email address |
| 18 | `Sender_DOB` | date | 0% | Date of birth |
| 19 | `Sender_Customer_Since` | date | 0% | Account opening date |
| 20 | `Sender_Occupation` | string | 0% | Occupation |
| 21 | `Sender_KYC_Status` | string | 0% | `Verified` |
| 22–35 | `Receiver_*` | (same as Sender) | varies | Mirror of Sender fields for the receiving party |
| 36 | `Merchant_Name` | string | 57.3% null | Present only for UPI/IMPS/POS merchant payments |
| 37 | `Merchant_Category` | string | 57.0% null | Category (Groceries, Electronics, etc.) |
| 38 | `Channel` | string | 0% | `Mobile_App` \| `ATM` \| `Branch` \| `Net_Banking` |
| 39 | `Sender_Account_Type` | string | 0% | `Savings` \| `Current` \| `Salary` |
| 40 | `Receiver_Account_Type` | string | 0% | Same as above |
| 41 | `Sender_Monthly_Salary` | int | 0% | Monthly salary in INR |
| 42 | `Receiver_Monthly_Salary` | int | 0% | Monthly salary in INR |

**Key identifiers for entity resolution:** `Sender_Phone_Number`, `Sender_UPI_ID`, `Sender_Account_Number`, `Receiver_Phone_Number`, `Receiver_UPI_ID`, `Receiver_Account_Number`

**Note on UPI IDs:** ~32.5% of UPI IDs contain the raw 10-digit phone number as the handle (e.g., `9876543210@paytm`). This is a valid real-world linking path to CDR/IPDR via phone number extraction from UPI narration strings.

---

### 2.2 Call Detail Records (`cdr_final.csv`)

24 columns. Models telecom operator CDR exports.

| # | Column | Type | Nulls | Description |
|---|---|---|---|---|
| 1 | `CDR_ID` | string | 0% | Unique ID (e.g., `CDR_058991`, injected: `INJ_CDR_0001`) |
| 2 | `Call_Start_Time` | datetime | 0% | Call start (2025 full year) |
| 3 | `Call_End_Time` | datetime | 0% | Call end (= start for Missed/Failed) |
| 4 | `Call_Duration_Seconds` | int | 0% | Duration (0 for Missed/Failed, synced with timestamps) |
| 5 | `Call_Type` | string | 0% | `Outgoing` \| `Incoming` \| `Missed` |
| 6 | `Call_Status` | string | 0% | `Completed` \| `Missed` \| `Failed` \| `Dropped` |
| 7 | `Subscriber_ID` | string | 0% | Telecom subscriber ID (`SUB_xxxxxx`) |
| 8 | `Caller_MSISDN` | int | 0% | 10-digit caller phone number |
| 9 | `Receiver_MSISDN` | int | 0% | 10-digit receiver phone number |
| 10 | `Caller_Name` | string | 0% | Caller name |
| 11 | `Receiver_Name` | string | 0% | Receiver name |
| 12 | `SIM_Number` | int | 0% | SIM serial |
| 13 | `IMSI` | int | **2.5%** | IMSI number |
| 14 | `IMEI` | int/float | **2.5%** | Device IMEI (key linking field to IPDR) |
| 15 | `Device_Model` | string | 0% | Phone model |
| 16 | `Device_OS` | string | 0% | `Android` \| `iOS` |
| 17 | `Network_Provider` | string | 0% | `Airtel` \| `Jio` \| `Vodafone Idea` \| `BSNL` |
| 18 | `Network_Type` | string | 0% | `4G` \| `5G` |
| 19 | `Cell_Tower_ID` | string | **2.5%** | Tower identifier (e.g., `TOWER_MUM_123`) |
| 20 | `Tower_City` | string | **2.5%** | City name (coordinates now match city) |
| 21 | `Latitude` | float | **2.5%** | Latitude (realistic, city-matched) |
| 22 | `Longitude` | float | **2.5%** | Longitude (realistic, city-matched) |
| 23 | `International_Call_Flag` | int | 0% | 0/1 flag (~1% flagged) |
| 24 | `Roaming_Flag` | int | 0% | 0/1 flag (~5% flagged) |

**Key identifiers:** `Caller_MSISDN` (links to Bank phone), `IMEI` (links to IPDR), `Subscriber_ID` (internal CDR only — does NOT reliably link to IPDR)

**Call logic (fixed):**
- Missed calls: `Duration=0`, `Status=Missed`, `End=Start` — 100% consistent
- Failed calls: `Duration=0`, `End=Start` — 100% consistent
- Completed calls: `Duration = End - Start` — 0 mismatches

---

### 2.3 Internet Protocol Detail Records (`ipdr_final.csv`)

24 columns. Models ISP session logs.

| # | Column | Type | Nulls | Description |
|---|---|---|---|---|
| 1 | `IPDR_ID` | string | 0% | Unique ID (e.g., `IPDR_000001`, injected: `INJ_IPDR_0001`) |
| 2 | `Session_ID` | string | 0% | Session identifier |
| 3 | `Subscriber_ID` | string | 0% | ISP subscriber ID (`SUB_xxxxxx`) |
| 4 | `User_MSISDN` | int | 0% | 10-digit phone number (key link to Bank + CDR) |
| 5 | `User_Name` | string | 0% | User name |
| 6 | `Session_Start_Time` | datetime | 0% | Session start (2025 full year) |
| 7 | `Session_End_Time` | datetime | 0% | Session end |
| 8 | `Session_Duration_Seconds` | int | 0% | Duration in seconds |
| 9 | `Data_Usage_MB` | float | 0% | Total data in MB |
| 10 | `Upload_MB` | float | 0% | Upload portion |
| 11 | `Download_MB` | float | 0% | Download portion |
| 12 | `Public_IP_Address` | string | **2.5%** | Public IP (e.g., `115.132.98.28`) |
| 13 | `Private_IP_Address` | string | 0% | NAT private IP (e.g., `192.168.x.x`) |
| 14 | `ISP_Name` | string | 0% | `Airtel Broadband` \| `JioFiber` \| `BSNL` \| `Vodafone Idea` \| `ACT Fibernet` |
| 15 | `Network_Type` | string | 0% | `WiFi` \| `4G` \| `5G` \| `Fiber` |
| 16 | `Connection_Type` | string | 0% | `Mobile_Data` \| `Public_WiFi` \| `Home_Broadband` |
| 17 | `Device_ID` | string | **2.5%** | Device identifier |
| 18 | `IMEI` | int/float | **2.5%** | Device IMEI (key link to CDR) |
| 19 | `Device_Model` | string | 0% | Phone model |
| 20 | `Operating_System` | string | 0% | `Android` \| `iOS` |
| 21 | `Browser` | string | 0% | `Chrome` \| `Safari` \| `Firefox` \| `Edge` \| `App_WebView` |
| 22 | `IP_Location_City` | string | **2.5%** | City name |
| 23 | `Latitude` | float | **2.5%** | Latitude |
| 24 | `Longitude` | float | **2.5%** | Longitude |

**Key identifiers:** `User_MSISDN` (links to Bank phone + CDR phone), `IMEI` (links to CDR)

---

## 3. Cross-Dataset Linking Map

This is how the three datasets connect — the core of the PS_03 "Fusion" requirement.

```
                    BANK                          CDR                         IPDR
            ┌────────────────┐           ┌────────────────┐          ┌────────────────┐
            │ Sender_Phone   │──phone──▶│ Caller_MSISDN  │◀──phone──│ User_MSISDN    │
            │ Receiver_Phone │           │ Receiver_MSISDN│          │                │
            │ Sender_UPI_ID  │──extract─▶│                │          │                │
            │ Sender_Account │           │ IMEI           │──IMEI───▶│ IMEI           │
            │ Timestamp      │──time────▶│ Call_Start_Time│◀──time──│ Session_Start   │
            │ Sender_City    │           │ Tower_City     │          │ IP_Location_City│
            └────────────────┘           └────────────────┘          └────────────────┘
```

### Verified Overlap Numbers

| Link Type | Count | Notes |
|---|---|---|
| Phone: Bank ∩ CDR | 1,145 | Sender/Receiver phones found as CDR Caller/Receiver |
| Phone: Bank ∩ IPDR | 100 | These are the "investigation targets" |
| Phone: CDR ∩ IPDR | 100 | Same 100 as above |
| Phone: All three | **100** | 100 entities discoverable across all datasets |
| IMEI: CDR ∩ IPDR | **100** | Same 100 entities, also linkable via device |
| UPI→Phone extraction | ~32.5% of UPIs | `9876543210@paytm` → phone `9876543210` |

> **CRITICAL WARNING:** `Subscriber_ID` appears in both CDR and IPDR (7,634 overlapping IDs) but maps to DIFFERENT phones and IMEIs. It is NOT a valid join key. Only `Phone Number` and `IMEI` are reliable cross-dataset identifiers.

---

## 4. Temporal Coincidence — Verified Working

The audit confirmed that the ±30-minute sliding window correlation works. Sample:

```
Phone 6060422207:
  CDR:  2025-03-05 17:52:00  (call placed)
  IPDR: 2025-03-05 17:54:00  (internet session started — 2 min later)
  Bank: 2025-03-05 17:59:00  (Rs 25,470 transferred — 7 min later)
```

**20 three-way coincidences found in just the first 20 phones tested.** This includes both the 40 deliberately injected fraud sequences and naturally occurring overlaps from the data redistribution.

---

## 5. Anomaly Detection Feasibility

The datasets contain sufficient signal for every anomaly type in PS_03 FR-3:

| Anomaly Type (PS_03) | Available Signal | Count |
|---|---|---|
| **Structuring** (below Rs 10K threshold) | Transactions Rs 9,000–9,999 | 3,590 |
| **Structuring** (below Rs 50K threshold) | Transactions Rs 45,000–49,999 | 2,672 |
| **Rapid in-out (Layering)** | Receive-then-send within 1 hour | 4+ patterns (top 10 accounts) |
| **Circular flow** | A→B and B→A pairs | **306 pairs** |
| **Device sharing** | IMEI used by 2+ subscribers | 18 IMEIs (3+ subs each) |
| **Odd-hour activity** | Night calls (11PM–5AM) | 29,218 CDR (29.2%) |
| **Odd-hour activity** | Night bank txns | 29,106 (29.0%) |
| **Mule-account signatures** | Composite of rapid-in-out + device sharing + odd-hour | Derivable from above |

---

## 6. Ground Truth (Internal Only)

**File:** `data/internal/ground_truth.json` — **NEVER exposed to the pipeline.**

| Field | Count | Purpose |
|---|---|---|
| `population_size` | 7,000 | Master population of generated identities |
| `person_identifiers` | 7,000 entries | Maps `PERSON_xxx` → `{phone, imei, upi_id, bank_customer_id}` |
| `cdr_overlap_map` | 120 entries | Maps CDR `SUB_xxx` → `PERSON_xxx` (which bank person they are) |
| `ipdr_overlap_map` | 100 entries | Maps IPDR `SUB_xxx` → `PERSON_xxx` |
| `cdr_device_anomaly_cases` | 54 entries | Planted IMEI-sharing cases for device-sharing detection testing |

This is used only to **validate** whether the Entity Resolution and Anomaly Detection engines are finding the right people.

---

## 7. Injected Fraud Sequences (40 Planted Cases)

40 synchronized fraud sequences were injected, each following the pattern:

```
T+0min:     CDR call placed (Outgoing, Completed, 60-300s)
T+2..5min:  IPDR internet session (accessing banking/app)
T+5..10min: Bank transfer (Rs 5,000 - Rs 1,00,000)
```

All three events share the **same phone number** and are **within the same city** (consistent lat/lon). These are identifiable by `Transaction_ID` / `CDR_ID` / `IPDR_ID` starting with `INJ_`.

These sequences are the minimum demonstration payload for PS_03 evaluation criterion EC-2 ("Quality of cross-dataset correlation on the unified timeline").

---

## 8. Data Quality Fixes Applied

| Fix | Problem | Resolution | Verification |
|---|---|---|---|
| **P1: Locations** | Lat/lon was random noise (8°–37°N) for all cities | Remapped to real city coordinates ±15km | Mumbai CDR: lat 18.93–19.23 ✅ |
| **P2: Call logic** | 33K missed calls had 7-min durations | All Missed/Failed → duration=0, end=start | 33,583/33,583 correct ✅ |
| **P2b: Duration sync** | 18,745 duration mismatches | Recalculated from timestamps | 0 mismatches ✅ |
| **P4: CDR analytics** | 4 pre-computed columns leaked | Stripped: `Calls_Per_Day`, `Average_Call_Duration`, `Unique_Contacts_Count`, `Night_Call_Ratio` | 28→24 cols ✅ |
| **P4: IPDR analytics+flags** | 8 pre-computed/flag columns leaked | Stripped: `Location_Change_Count`, `Daily_Session_Count`, `Unique_IP_Count`, `Login_Frequency` + all 4 fraud flags | 32→24 cols ✅ |
| **P5: Temporal window** | CDR/IPDR covered October only | Redistributed across Jan–Dec 2025 (DOW-preserving, paired start/end) | 12 months each ✅ |
| **P7: Missing values** | CDR/IPDR had zero nulls | Injected ~2.5% nulls in location, IMEI, tower, IP fields | CDR: 15K nulls, IPDR: 7.6K ✅ |

---

## 9. PS_03 Requirements Traceability

| Requirement | Dataset Support |
|---|---|
| **KO-1:** Ingest bank/CDR/IPDR | 3 distinct CSV files with different schemas ✅ |
| **KO-2:** Normalize to unified entity+time | Shared phone numbers (100 all-three), shared IMEIs (100), extractable UPI phones ✅ |
| **KO-3:** Correlate on common timeline | All 3 datasets cover Jan–Dec 2025; 20+ verified ±30min coincidences ✅ |
| **KO-4:** Detect patterns, visualize networks | 306 circular-flow pairs, 18 shared-IMEI cases, 3.5K+ structuring candidates ✅ |
| **KO-5:** Investigation-ready report | Source-traceable IDs, timestamps, amounts in every row ✅ |
| **FR-2.b:** Temporal coincidences | 40 planted + natural overlaps confirmed ✅ |
| **FR-2.c:** Shared identifiers | Phone, IMEI, UPI ID linking paths all verified ✅ |
| **FR-3.a:** Layering, structuring, circular flows | All detectable from the data ✅ |
| **FR-3.c:** Mule-account signatures | Device sharing + rapid in-out + odd-hour composable ✅ |
| **EC-5:** 50K+ records performance | 251K total records ✅ |

---

## 10. Remaining Known Limitations

| Item | Severity | Detail |
|---|---|---|
| Bank is a "god-view" ledger | Moderate | Contains both Sender and Receiver full metadata on every row. Real bank statements are one-sided. The ingestion engine won't need to parse messy narration strings for the receiver. |
| No PDF/Excel test files | Moderate | All data is CSV. The FR-1.1 PDF/Excel parsing capability needs separate test files created. |
| IPDR injected rows may have stale coordinates | Minor | The 40 injected IPDR fraud rows copied template lat/lon from original data before the city-fix pass. These are <0.08% of total IPDR rows. |
| Subscriber_ID naming collision | Awareness | Same IDs exist in CDR and IPDR but map to different people. Pipeline must NOT join on this field. |
