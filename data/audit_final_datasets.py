"""
TRINETRA - Comprehensive Final Dataset Audit
Analyses data/final/ against every PS_03 requirement.
"""
import pandas as pd
import numpy as np
import json
import os

FINAL = r"F:\ERAKSHAK\TRI-NETRA\data\final"
GT = r"F:\ERAKSHAK\TRI-NETRA\data\internal\ground_truth.json"

print("=" * 80)
print("TRINETRA — COMPREHENSIVE FINAL DATASET AUDIT")
print("=" * 80)

# ─── LOAD ────────────────────────────────────────────────────────────
bank = pd.read_csv(os.path.join(FINAL, "bank_transactions.csv"))
cdr = pd.read_csv(os.path.join(FINAL, "cdr_final.csv"))
ipdr = pd.read_csv(os.path.join(FINAL, "ipdr_final.csv"))

with open(GT, "r") as f:
    gt = json.load(f)

bank["Timestamp"] = pd.to_datetime(bank["Timestamp"])
cdr["Call_Start_Time"] = pd.to_datetime(cdr["Call_Start_Time"])
cdr["Call_End_Time"] = pd.to_datetime(cdr["Call_End_Time"])
ipdr["Session_Start_Time"] = pd.to_datetime(ipdr["Session_Start_Time"])
ipdr["Session_End_Time"] = pd.to_datetime(ipdr["Session_End_Time"])

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: SCHEMA ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 1: SCHEMAS")
print("=" * 80)

for name, df in [("BANK", bank), ("CDR", cdr), ("IPDR", ipdr)]:
    print(f"\n--- {name} ({df.shape[0]:,} rows x {df.shape[1]} cols) ---")
    for i, col in enumerate(df.columns):
        dtype = df[col].dtype
        nulls = df[col].isna().sum()
        nunique = df[col].nunique()
        null_pct = f"{nulls/len(df)*100:.1f}%" if nulls > 0 else "0%"
        sample = str(df[col].dropna().iloc[0])[:50] if df[col].notna().any() else "ALL NULL"
        print(f"  {i+1:2d}. {col:35s} {str(dtype):10s} nulls={null_pct:>5s}  unique={nunique:>7,}  sample={sample}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: TEMPORAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 2: TEMPORAL COVERAGE")
print("=" * 80)

for name, df, col in [("Bank", bank, "Timestamp"), ("CDR", cdr, "Call_Start_Time"), ("IPDR", ipdr, "Session_Start_Time")]:
    monthly = df[col].dt.month.value_counts().sort_index()
    print(f"\n{name}: {df[col].min()} to {df[col].max()}")
    print(f"  Monthly distribution:")
    for m, c in monthly.items():
        bar = "#" * (c // 200)
        print(f"    Month {m:2d}: {c:>6,} {bar}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: ENTITY OVERLAP (THE FUSION STORY)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 3: ENTITY OVERLAP ANALYSIS")
print("=" * 80)

# Phone overlap
bank_sender_phones = set(bank["Sender_Phone_Number"].dropna().astype(int))
bank_receiver_phones = set(bank["Receiver_Phone_Number"].dropna().astype(int))
bank_all_phones = bank_sender_phones | bank_receiver_phones
cdr_caller_phones = set(cdr["Caller_MSISDN"].dropna().astype(int))
cdr_receiver_phones = set(cdr["Receiver_MSISDN"].dropna().astype(int))
cdr_all_phones = cdr_caller_phones | cdr_receiver_phones
ipdr_phones = set(ipdr["User_MSISDN"].dropna().astype(int))

print(f"\nPhone Numbers:")
print(f"  Bank (sender+receiver): {len(bank_all_phones):,}")
print(f"  CDR (caller+receiver):  {len(cdr_all_phones):,}")
print(f"  IPDR (user):            {len(ipdr_phones):,}")
print(f"  Bank AND CDR:           {len(bank_all_phones & cdr_all_phones):,}")
print(f"  Bank AND IPDR:          {len(bank_all_phones & ipdr_phones):,}")
print(f"  CDR AND IPDR:           {len(cdr_all_phones & ipdr_phones):,}")
print(f"  ALL THREE:              {len(bank_all_phones & cdr_all_phones & ipdr_phones):,}")

# IMEI overlap
cdr_imei = set(cdr["IMEI"].dropna().astype(str))
ipdr_imei = set(ipdr["IMEI"].dropna().astype(str))
print(f"\nIMEI:")
print(f"  CDR unique:  {len(cdr_imei):,}")
print(f"  IPDR unique: {len(ipdr_imei):,}")
print(f"  CDR AND IPDR: {len(cdr_imei & ipdr_imei):,}")

# UPI overlap (bank has UPI IDs, can they link to phones?)
bank_upi_sender = set(bank["Sender_UPI_ID"].dropna())
bank_upi_receiver = set(bank["Receiver_UPI_ID"].dropna())
print(f"\nUPI IDs:")
print(f"  Sender UPIs:   {len(bank_upi_sender):,}")
print(f"  Receiver UPIs: {len(bank_upi_receiver):,}")

# Check UPIs that contain phone numbers
phone_in_upi = 0
for upi in list(bank_upi_sender)[:2000]:
    parts = upi.split("@")[0]
    if parts.isdigit() and len(parts) == 10:
        phone_in_upi += 1
print(f"  Sender UPIs containing a 10-digit phone (sample 2000): {phone_in_upi}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: CROSS-DATASET TEMPORAL COINCIDENCE TEST
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 4: TEMPORAL COINCIDENCE FEASIBILITY")
print("=" * 80)

linked_phones = sorted(bank_all_phones & cdr_all_phones & ipdr_phones)
print(f"\n100 phones in all 3 datasets. Testing temporal proximity...")

coincidences_found = 0
sample_coincidences = []

for phone in linked_phones[:20]:  # Test first 20
    b = bank[(bank["Sender_Phone_Number"] == phone) | (bank["Receiver_Phone_Number"] == phone)]
    c = cdr[(cdr["Caller_MSISDN"] == phone) | (cdr["Receiver_MSISDN"] == phone)]
    i = ipdr[ipdr["User_MSISDN"] == phone]
    
    for _, btxn in b.iterrows():
        bt = btxn["Timestamp"]
        # Find CDR within +/- 30 min
        c_near = c[(c["Call_Start_Time"] >= bt - pd.Timedelta(minutes=30)) & 
                    (c["Call_Start_Time"] <= bt + pd.Timedelta(minutes=30))]
        i_near = i[(i["Session_Start_Time"] >= bt - pd.Timedelta(minutes=30)) & 
                    (i["Session_Start_Time"] <= bt + pd.Timedelta(minutes=30))]
        
        if len(c_near) > 0 and len(i_near) > 0:
            coincidences_found += 1
            if len(sample_coincidences) < 3:
                sample_coincidences.append({
                    "phone": phone,
                    "bank_time": str(bt),
                    "bank_amount": btxn["Transaction_Amount"],
                    "cdr_time": str(c_near.iloc[0]["Call_Start_Time"]),
                    "ipdr_time": str(i_near.iloc[0]["Session_Start_Time"]),
                })

print(f"\n  3-way coincidences found (within +/-30min, first 20 phones): {coincidences_found}")
if sample_coincidences:
    print(f"\n  Sample coincidences:")
    for sc in sample_coincidences:
        print(f"    Phone {sc['phone']}:")
        print(f"      Bank:  {sc['bank_time']} (Rs {sc['bank_amount']:,.0f})")
        print(f"      CDR:   {sc['cdr_time']}")
        print(f"      IPDR:  {sc['ipdr_time']}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: ANOMALY PATTERN FEASIBILITY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 5: ANOMALY DETECTION FEASIBILITY")
print("=" * 80)

# Structuring: multiple txns just below thresholds
struct_10k = bank[(bank["Transaction_Amount"] >= 9000) & (bank["Transaction_Amount"] < 10000)]
struct_50k = bank[(bank["Transaction_Amount"] >= 45000) & (bank["Transaction_Amount"] < 50000)]
print(f"\n  Structuring candidates (just below thresholds):")
print(f"    Rs 9,000-9,999:  {len(struct_10k):,} transactions")
print(f"    Rs 45,000-49,999: {len(struct_50k):,} transactions")

# Rapid in-out: same account receives then sends within short window
print(f"\n  Rapid in-out analysis:")
# For top 10 accounts, check receive-then-send patterns
top_accounts = bank["Sender_Account_Number"].value_counts().head(10).index
rapid_count = 0
for acc in top_accounts:
    acc_txns = bank[(bank["Sender_Account_Number"] == acc) | (bank["Receiver_Account_Number"] == acc)].sort_values("Timestamp")
    for idx in range(len(acc_txns) - 1):
        gap = (acc_txns.iloc[idx+1]["Timestamp"] - acc_txns.iloc[idx]["Timestamp"]).total_seconds()
        if gap < 3600:  # within 1 hour
            rapid_count += 1
print(f"    Accounts with <1hr receive-then-send (top 10 accounts): {rapid_count}")

# Device sharing (IMEI used by multiple subscribers)
cdr_imei_subs = cdr.dropna(subset=["IMEI"]).groupby("IMEI")["Subscriber_ID"].nunique()
shared_imei = cdr_imei_subs[cdr_imei_subs >= 2]
print(f"\n  Device sharing (CDR):")
print(f"    IMEIs used by 2+ subscribers: {len(shared_imei):,}")
print(f"    IMEIs used by 3+ subscribers: {(cdr_imei_subs >= 3).sum():,}")

# Night activity
cdr_hours = cdr["Call_Start_Time"].dt.hour
night_calls = ((cdr_hours >= 23) | (cdr_hours <= 5)).sum()
print(f"\n  Night activity (11PM-5AM):")
print(f"    CDR night calls: {night_calls:,} ({night_calls/len(cdr)*100:.1f}%)")

bank_hours = bank["Timestamp"].dt.hour
night_txns = ((bank_hours >= 23) | (bank_hours <= 5)).sum()
print(f"    Bank night txns: {night_txns:,} ({night_txns/len(bank)*100:.1f}%)")

# Circular flow candidates
print(f"\n  Circular flow feasibility:")
# Check A->B->A patterns
ab_pairs = bank.groupby(["Sender_Account_Number", "Receiver_Account_Number"]).size().reset_index(name="count")
ba_pairs = ab_pairs.rename(columns={"Sender_Account_Number": "B", "Receiver_Account_Number": "A", "count": "ba_count"})
circular = ab_pairs.merge(
    ba_pairs, 
    left_on=["Sender_Account_Number", "Receiver_Account_Number"],
    right_on=["A", "B"],
    how="inner"
)
print(f"    A->B and B->A pairs found: {len(circular):,}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: LOCATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 6: GEOSPATIAL CONSISTENCY")
print("=" * 80)

for name, df, city_col in [("CDR", cdr, "Tower_City"), ("IPDR", ipdr, "IP_Location_City")]:
    print(f"\n  {name} location check (non-null only):")
    df_valid = df.dropna(subset=[city_col, "Latitude", "Longitude"])
    cities = df_valid.groupby(city_col).agg(
        lat_min=("Latitude", "min"), lat_max=("Latitude", "max"),
        lon_min=("Longitude", "min"), lon_max=("Longitude", "max"),
        count=("Latitude", "count")
    )
    for city, row in cities.head(5).iterrows():
        lat_spread = row["lat_max"] - row["lat_min"]
        lon_spread = row["lon_max"] - row["lon_min"]
        print(f"    {city:12s}: lat {row['lat_min']:.2f}-{row['lat_max']:.2f} (spread {lat_spread:.2f}), "
              f"lon {row['lon_min']:.2f}-{row['lon_max']:.2f} (spread {lon_spread:.2f}), n={int(row['count']):,}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: GROUND TRUTH VERIFICATION
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 7: GROUND TRUTH INTEGRITY")
print("=" * 80)

print(f"\n  Population size: {gt['population_size']}")
print(f"  Person identifiers: {len(gt['person_identifiers'])}")
print(f"  CDR overlap entries: {len(gt['cdr_overlap_map'])}")
print(f"  IPDR overlap entries: {len(gt['ipdr_overlap_map'])}")
print(f"  Device anomaly cases: {len(gt['cdr_device_anomaly_cases'])}")

# Verify overlap phones still present in final data
cdr_overlap_persons = set(gt["cdr_overlap_map"].values())
ipdr_overlap_persons = set(gt["ipdr_overlap_map"].values())
all_overlap_persons = cdr_overlap_persons | ipdr_overlap_persons

verified = 0
for person_id in list(all_overlap_persons)[:20]:
    p = gt["person_identifiers"][person_id]
    phone = p["phone"]
    in_bank = phone in bank_sender_phones
    in_cdr = phone in cdr_caller_phones
    in_ipdr = phone in ipdr_phones
    if in_bank:
        verified += 1

print(f"  Overlap persons verified in bank (sample 20): {verified}/20")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: INJECTED FRAUD SEQUENCE VERIFICATION
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 8: INJECTED FRAUD SEQUENCES")
print("=" * 80)

inj_bank = bank[bank["Transaction_ID"].str.startswith("INJ_", na=False)]
inj_cdr = cdr[cdr["CDR_ID"].str.startswith("INJ_", na=False)]
inj_ipdr = ipdr[ipdr["IPDR_ID"].str.startswith("INJ_", na=False)]
print(f"\n  Injected rows: Bank={len(inj_bank)}, CDR={len(inj_cdr)}, IPDR={len(inj_ipdr)}")

# Show 3 sample sequences
print(f"\n  Sample injected sequences:")
for i in range(min(3, len(inj_cdr))):
    c = inj_cdr.iloc[i]
    phone = int(c["Caller_MSISDN"])
    b_match = inj_bank[inj_bank["Sender_Phone_Number"] == phone]
    i_match = inj_ipdr[inj_ipdr["User_MSISDN"] == phone]
    print(f"\n    Sequence {i+1} (phone={phone}):")
    print(f"      CDR:  {c['Call_Start_Time']} (call, {c['Call_Duration_Seconds']}s)")
    if len(i_match) > 0:
        ip = i_match.iloc[0]
        print(f"      IPDR: {ip['Session_Start_Time']} (session)")
    if len(b_match) > 0:
        bk = b_match.iloc[0]
        print(f"      Bank: {bk['Timestamp']} (Rs {bk['Transaction_Amount']:,.0f})")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 9: DATA QUALITY SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SECTION 9: DATA QUALITY SUMMARY")
print("=" * 80)

# Call logic
missed = cdr[cdr["Call_Type"] == "Missed"]
failed = cdr[cdr["Call_Status"] == "Failed"]
print(f"\n  Call logic:")
print(f"    Missed calls with dur=0: {(missed['Call_Duration_Seconds'] == 0).sum():,}/{len(missed):,}")
print(f"    Failed calls with dur=0: {(failed['Call_Duration_Seconds'] == 0).sum():,}/{len(failed):,}")

# Duration consistency (for completed calls)
completed = cdr[(cdr["Call_Status"] == "Completed") & (cdr["Call_Type"].isin(["Incoming", "Outgoing"]))]
calc = (completed["Call_End_Time"] - completed["Call_Start_Time"]).dt.total_seconds()
mismatch = (abs(completed["Call_Duration_Seconds"] - calc) > 1).sum()
print(f"    Completed call duration mismatches: {mismatch}")

# Missing values
print(f"\n  Missing values:")
for name, df in [("Bank", bank), ("CDR", cdr), ("IPDR", ipdr)]:
    total_nulls = df.isnull().sum().sum()
    null_cols = (df.isnull().sum() > 0).sum()
    print(f"    {name}: {total_nulls:,} nulls across {null_cols} columns")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
