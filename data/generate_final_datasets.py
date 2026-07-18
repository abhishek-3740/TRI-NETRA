"""
TRINETRA - Generate Final Clean Datasets (Proper Fix)
=====================================================
Fixes ALL problems identified in the dataset audit:

  P1 (CRITICAL) : Lat/Lon randomized to match actual city coordinates
  P2 (CRITICAL) : Missed/Failed calls get duration=0, correct status
  P2b(CRITICAL) : Call_Duration_Seconds recalculated from End-Start
  P4 (MODERATE) : Pre-computed analytics columns stripped
  P5 (MODERATE) : CDR/IPDR distributed across full year (DOW-preserving, paired start/end)
  P7 (MINOR)    : Missing values injected into CDR/IPDR (~2-5% nulls)
  BONUS         : 40 synchronized fraud sequences injected (call->session->transfer)

Output: F:\ERAKSHAK\TRI-NETRA\data\final\
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from calendar import monthrange

# ─── CONFIG ──────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)

BASE_DIR = r"F:\ERAKSHAK\TRI-NETRA\data"
PROC_DIR = os.path.join(BASE_DIR, "processed")
FINAL_DIR = os.path.join(BASE_DIR, "final")

# Use the ALIGNED files (2025, correct phone overlap already established)
BANK_IN = os.path.join(PROC_DIR, "bank_transactions_clean.csv")
CDR_IN = os.path.join(PROC_DIR, "cdr_clean_aligned.csv")
IPDR_IN = os.path.join(PROC_DIR, "ipdr_clean_aligned.csv")

BANK_OUT = os.path.join(FINAL_DIR, "bank_transactions.csv")
CDR_OUT = os.path.join(FINAL_DIR, "cdr_final.csv")
IPDR_OUT = os.path.join(FINAL_DIR, "ipdr_final.csv")

# Columns to strip (your Intelligence Engine must compute these itself)
CDR_STRIP_COLS = [
    "Calls_Per_Day", "Average_Call_Duration", "Unique_Contacts_Count",
    "Night_Call_Ratio",
]
IPDR_STRIP_COLS = [
    "Location_Change_Count", "Daily_Session_Count", "Unique_IP_Count",
    "Login_Frequency", "Suspicious_Login_Flag", "VPN_Proxy_Flag",
    "International_IP_Flag", "Data_Spike_Flag",
]

# Real Indian city coordinates (approximate city center + radius for jitter)
CITY_COORDS = {
    "Mumbai":     (19.0760, 72.8777),
    "Delhi":      (28.6139, 77.2090),
    "Bengaluru":  (12.9716, 77.5946),
    "Hyderabad":  (17.3850, 78.4867),
    "Ahmedabad":  (23.0225, 72.5714),
    "Chennai":    (13.0827, 80.2707),
    "Kolkata":    (22.5726, 88.3639),
    "Pune":       (18.5204, 73.8567),
    "Jaipur":     (26.9124, 75.7873),
    "Lucknow":    (26.8467, 80.9462),
    "Surat":      (21.1702, 72.8311),
    "Bhopal":     (23.2599, 77.4126),
    "Indore":     (22.7196, 75.8577),
    "Nagpur":     (21.1458, 79.0882),
    "Patna":      (25.6093, 85.1376),
}
CITY_RADIUS_DEG = 0.15  # ~15 km scatter around city center


N_FRAUD_SEQUENCES = 40


# ─── FIX FUNCTIONS ──────────────────────────────────────────────────

def fix_locations(df, city_col, lat_col="Latitude", lon_col="Longitude"):
    """P1: Replace random lat/lon with realistic coordinates matching the city label."""
    fixed = 0
    for city, (center_lat, center_lon) in CITY_COORDS.items():
        mask = df[city_col] == city
        n = mask.sum()
        if n == 0:
            continue
        df.loc[mask, lat_col] = center_lat + np.random.uniform(
            -CITY_RADIUS_DEG, CITY_RADIUS_DEG, size=n
        )
        df.loc[mask, lon_col] = center_lon + np.random.uniform(
            -CITY_RADIUS_DEG, CITY_RADIUS_DEG, size=n
        )
        fixed += n

    # Any city not in our map: assign random known city coords
    unknown = ~df[city_col].isin(CITY_COORDS.keys())
    n_unknown = unknown.sum()
    if n_unknown > 0:
        cities = list(CITY_COORDS.keys())
        for idx in df.index[unknown]:
            city = np.random.choice(cities)
            c_lat, c_lon = CITY_COORDS[city]
            df.at[idx, city_col] = city
            df.at[idx, lat_col] = c_lat + np.random.uniform(-CITY_RADIUS_DEG, CITY_RADIUS_DEG)
            df.at[idx, lon_col] = c_lon + np.random.uniform(-CITY_RADIUS_DEG, CITY_RADIUS_DEG)
        fixed += n_unknown

    return df, fixed


def fix_call_logic(df):
    """P2: Fix impossible call states - Missed/Failed must have 0 duration."""
    # Parse timestamps
    df["Call_Start_Time"] = pd.to_datetime(df["Call_Start_Time"], errors="coerce")
    df["Call_End_Time"] = pd.to_datetime(df["Call_End_Time"], errors="coerce")

    # --- Missed calls: duration = 0, status = "Missed", end = start ---
    missed = df["Call_Type"] == "Missed"
    df.loc[missed, "Call_Duration_Seconds"] = 0
    df.loc[missed, "Call_Status"] = "Missed"
    df.loc[missed, "Call_End_Time"] = df.loc[missed, "Call_Start_Time"]
    n_missed = missed.sum()

    # --- Failed calls: duration = 0, end = start ---
    failed = df["Call_Status"] == "Failed"
    df.loc[failed, "Call_Duration_Seconds"] = 0
    df.loc[failed, "Call_End_Time"] = df.loc[failed, "Call_Start_Time"]
    n_failed = failed.sum()

    # --- For all remaining (Completed Incoming/Outgoing): recalculate duration from timestamps ---
    valid = (df["Call_Type"].isin(["Incoming", "Outgoing"])) & (df["Call_Status"] == "Completed")
    calc_dur = (df.loc[valid, "Call_End_Time"] - df.loc[valid, "Call_Start_Time"]).dt.total_seconds()

    # If calculated duration is negative or zero, fix end_time using stored duration
    bad_dur = calc_dur <= 0
    if bad_dur.any():
        bad_idx = calc_dur[bad_dur].index
        df.loc[bad_idx, "Call_End_Time"] = (
            df.loc[bad_idx, "Call_Start_Time"]
            + pd.to_timedelta(df.loc[bad_idx, "Call_Duration_Seconds"], unit="s")
        )

    # Now recalculate all valid durations from timestamps
    df.loc[valid, "Call_Duration_Seconds"] = (
        (df.loc[valid, "Call_End_Time"] - df.loc[valid, "Call_Start_Time"])
        .dt.total_seconds()
        .astype(int)
    )
    n_synced = valid.sum()

    return df, n_missed, n_failed, n_synced


def distribute_full_year(df, start_col, end_col=None, year=2025):
    """
    P5: Redistribute records across all 12 months of `year`.
    Preserves: day-of-week, time-of-day, and start-to-end duration.
    """
    df[start_col] = pd.to_datetime(df[start_col], errors="coerce")
    if end_col and end_col in df.columns:
        df[end_col] = pd.to_datetime(df[end_col], errors="coerce")
        durations = df[end_col] - df[start_col]  # preserve exact gap

    n = len(df)
    target_months = np.random.randint(1, 13, size=n)

    new_starts = []
    for i in range(n):
        dt = df[start_col].iloc[i]
        if pd.isna(dt):
            new_starts.append(pd.NaT)
            continue
        m = target_months[i]
        dow = dt.weekday()
        max_day = monthrange(year, m)[1]
        candidates = [d for d in range(1, max_day + 1)
                       if datetime(year, m, d).weekday() == dow]
        day = candidates[np.random.randint(0, len(candidates))]
        new_starts.append(datetime(year, m, day, dt.hour, dt.minute, dt.second))

    df[start_col] = pd.to_datetime(new_starts)

    # Shift end_col by the SAME offset to keep duration intact
    if end_col and end_col in df.columns:
        df[end_col] = df[start_col] + durations

    return df


def inject_missing_values(df, cols_to_null, frac=0.03, dataset_name=""):
    """P7: Inject realistic missing values into specified columns."""
    total_injected = 0
    for col in cols_to_null:
        if col not in df.columns:
            continue
        n_null = int(len(df) * frac)
        null_idx = np.random.choice(df.index, size=n_null, replace=False)
        df.loc[null_idx, col] = np.nan
        total_injected += n_null
    return df, total_injected


def strip_columns(df, cols, name):
    """P4: Remove pre-computed analytics columns."""
    to_drop = [c for c in cols if c in df.columns]
    if to_drop:
        df = df.drop(columns=to_drop)
        print(f"    Stripped {len(to_drop)} columns: {to_drop}")
    else:
        print(f"    No matching columns to strip")
    return df


def add_bank_ip_device(df):
    """Add Sender_IP_Address and Sender_Device_ID to Bank dataset for digital channels."""
    df["Sender_IP_Address"] = pd.Series(dtype="object")
    df["Sender_Device_ID"] = pd.Series(dtype="object")
    
    mask = df["Channel"].isin(["Mobile_App", "Net_Banking"])
    n = mask.sum()
    if n > 0:
        import random
        ips = [f"{np.random.randint(1,255)}.{np.random.randint(0,255)}.{np.random.randint(0,255)}.{np.random.randint(0,255)}" for _ in range(n)]
        devices = [str(random.randint(100000000000000, 999999999999999)) for _ in range(n)]
        df.loc[mask, "Sender_IP_Address"] = ips
        df.loc[mask, "Sender_Device_ID"] = devices
        
    return df


def inject_fraud_sequences(df_bank, df_cdr, df_ipdr, n=40):
    """
    Inject n synchronized fraud sequences.
    Each: CDR call at T -> IPDR session at T+2..5min -> Bank transfer at T+5..10min
    Uses phones that exist in ALL THREE datasets.
    """
    bank_phones = set(df_bank["Sender_Phone_Number"].dropna().astype(int))
    cdr_phones = set(df_cdr["Caller_MSISDN"].dropna().astype(int))
    ipdr_phones = set(df_ipdr["User_MSISDN"].dropna().astype(int))
    linked = sorted(bank_phones & cdr_phones & ipdr_phones)

    if len(linked) == 0:
        print("    WARNING: No linked phones found! Skipping injection.")
        return df_bank, df_cdr, df_ipdr, 0

    new_cdr_rows, new_ipdr_rows, new_bank_rows = [], [], []

    for i in range(n):
        phone = int(linked[i % len(linked)])

        # Random base time across the year
        month = np.random.randint(1, 13)
        day = np.random.randint(1, 29)
        hour = np.random.randint(9, 22)
        minute = np.random.randint(0, 60)
        base_time = datetime(2025, month, day, hour, minute, 0)

        # Get city for this phone from CDR (for location consistency)
        cdr_match = df_cdr[df_cdr["Caller_MSISDN"] == phone]
        if len(cdr_match) == 0:
            continue
        city = cdr_match.iloc[0]["Tower_City"]
        lat, lon = CITY_COORDS.get(city, (21.17, 72.83))  # default Surat
        lat += np.random.uniform(-0.02, 0.02)
        lon += np.random.uniform(-0.02, 0.02)

        # --- CDR row ---
        cdr_tmpl = cdr_match.iloc[0].copy()
        call_dur = int(np.random.randint(60, 300))
        cdr_tmpl["CDR_ID"] = f"INJ_CDR_{i+1:04d}"
        cdr_tmpl["Call_Start_Time"] = base_time
        cdr_tmpl["Call_End_Time"] = base_time + timedelta(seconds=call_dur)
        cdr_tmpl["Call_Duration_Seconds"] = call_dur
        cdr_tmpl["Call_Type"] = "Outgoing"
        cdr_tmpl["Call_Status"] = "Completed"
        cdr_tmpl["Latitude"] = lat
        cdr_tmpl["Longitude"] = lon
        new_cdr_rows.append(cdr_tmpl)

        # --- IPDR row ---
        ipdr_match = df_ipdr[df_ipdr["User_MSISDN"] == phone]
        if len(ipdr_match) == 0:
            continue
        ipdr_tmpl = ipdr_match.iloc[0].copy()
        session_offset = int(np.random.randint(2, 6))  # 2-5 min after call
        session_dur = int(np.random.randint(120, 600))
        ipdr_tmpl["IPDR_ID"] = f"INJ_IPDR_{i+1:04d}"
        ipdr_tmpl["Session_Start_Time"] = base_time + timedelta(minutes=session_offset)
        ipdr_tmpl["Session_End_Time"] = base_time + timedelta(minutes=session_offset, seconds=session_dur)
        ipdr_tmpl["Session_Duration_Seconds"] = session_dur
        ipdr_tmpl["Latitude"] = lat + np.random.uniform(-0.01, 0.01)
        ipdr_tmpl["Longitude"] = lon + np.random.uniform(-0.01, 0.01)
        new_ipdr_rows.append(ipdr_tmpl)

        # --- Bank row ---
        bank_match = df_bank[df_bank["Sender_Phone_Number"] == phone]
        if len(bank_match) == 0:
            continue
        bank_tmpl = bank_match.iloc[0].copy()
        txn_offset = int(np.random.randint(5, 11))  # 5-10 min after call
        bank_tmpl["Transaction_ID"] = f"INJ_TXN_{i+1:04d}"
        bank_tmpl["Timestamp"] = base_time + timedelta(minutes=txn_offset)
        bank_tmpl["Transaction_Amount"] = float(np.random.randint(5000, 100001))
        bank_tmpl["Transaction_Mode"] = np.random.choice(["UPI", "IMPS", "NEFT"])
        bank_tmpl["Transaction_Status"] = "SUCCESS"
        bank_tmpl["Channel"] = "Mobile_App"
        
        # Link IP and Device ID explicitly from IPDR
        if len(ipdr_match) > 0:
            bank_tmpl["Sender_IP_Address"] = ipdr_tmpl.get("Public_IP_Address", np.nan)
            bank_tmpl["Sender_Device_ID"] = ipdr_tmpl.get("IMEI", np.nan)
            
        new_bank_rows.append(bank_tmpl)

    df_cdr = pd.concat([df_cdr, pd.DataFrame(new_cdr_rows)], ignore_index=True)
    df_ipdr = pd.concat([df_ipdr, pd.DataFrame(new_ipdr_rows)], ignore_index=True)
    df_bank = pd.concat([df_bank, pd.DataFrame(new_bank_rows)], ignore_index=True)

    return df_bank, df_cdr, df_ipdr, len(new_cdr_rows)


# ─── MAIN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("TRINETRA - Final Dataset Generator (Comprehensive Fix)")
    print("=" * 70)

    # --- [1] Setup ---
    os.makedirs(FINAL_DIR, exist_ok=True)
    print(f"\n[1/8] Output folder: {FINAL_DIR}")

    # --- [2] Load ---
    print("\n[2/8] Loading datasets...")
    df_bank = pd.read_csv(BANK_IN)
    df_cdr = pd.read_csv(CDR_IN)
    df_ipdr = pd.read_csv(IPDR_IN)
    print(f"  Bank : {len(df_bank):,} rows x {df_bank.shape[1]} cols")
    print(f"  CDR  : {len(df_cdr):,} rows x {df_cdr.shape[1]} cols")
    print(f"  IPDR : {len(df_ipdr):,} rows x {df_ipdr.shape[1]} cols")

    # --- [3] Strip pre-computed columns (P4) ---
    print("\n[3/8] Stripping pre-computed analytics columns (P4)...")
    print("  CDR:")
    df_cdr = strip_columns(df_cdr, CDR_STRIP_COLS, "CDR")
    print("  IPDR:")
    df_ipdr = strip_columns(df_ipdr, IPDR_STRIP_COLS, "IPDR")

    # --- [4] Fix locations (P1 - CRITICAL) ---
    print("\n[4/8] Fixing locations to match city labels (P1)...")
    df_cdr, n_cdr_loc = fix_locations(df_cdr, "Tower_City")
    df_ipdr, n_ipdr_loc = fix_locations(df_ipdr, "IP_Location_City")
    print(f"  CDR:  {n_cdr_loc:,} coordinates fixed")
    print(f"  IPDR: {n_ipdr_loc:,} coordinates fixed")

    # --- [4.5] Add Bank IP/Device ---
    print("\n[4.5/8] Adding IP and Device IDs to Bank digital transactions...")
    df_bank = add_bank_ip_device(df_bank)

    # --- [5] Fix call logic (P2 - CRITICAL) ---
    print("\n[5/8] Fixing call logic - Missed/Failed durations (P2)...")
    df_cdr, n_missed, n_failed, n_synced = fix_call_logic(df_cdr)
    print(f"  Missed calls zeroed:    {n_missed:,}")
    print(f"  Failed calls zeroed:    {n_failed:,}")
    print(f"  Valid calls synced:     {n_synced:,}")

    # --- [6] Distribute across full year (P5) ---
    print("\n[6/8] Distributing CDR/IPDR across full 2025 (P5)...")
    df_cdr = distribute_full_year(df_cdr, "Call_Start_Time", "Call_End_Time")
    df_ipdr = distribute_full_year(df_ipdr, "Session_Start_Time", "Session_End_Time")

    cdr_months = pd.to_datetime(df_cdr["Call_Start_Time"]).dt.month
    ipdr_months = pd.to_datetime(df_ipdr["Session_Start_Time"]).dt.month
    print(f"  CDR  months: {cdr_months.min()}-{cdr_months.max()} ({cdr_months.nunique()} unique)")
    print(f"  IPDR months: {ipdr_months.min()}-{ipdr_months.max()} ({ipdr_months.nunique()} unique)")

    # --- [7] Inject missing values (P7) ---
    print("\n[7/8] Injecting missing values into CDR/IPDR (P7)...")
    df_cdr, n_cdr_null = inject_missing_values(
        df_cdr,
        ["Cell_Tower_ID", "Tower_City", "Latitude", "Longitude", "IMEI", "IMSI"],
        frac=0.025,
        dataset_name="CDR",
    )
    df_ipdr, n_ipdr_null = inject_missing_values(
        df_ipdr,
        ["Public_IP_Address", "IP_Location_City", "Latitude", "Longitude", "IMEI", "Device_ID"],
        frac=0.025,
        dataset_name="IPDR",
    )
    print(f"  CDR:  {n_cdr_null:,} null values injected across 6 columns (~2.5% each)")
    print(f"  IPDR: {n_ipdr_null:,} null values injected across 6 columns (~2.5% each)")

    # --- [8] Inject fraud sequences ---
    print("\n[8/8] Injecting synchronized fraud sequences...")
    df_bank, df_cdr, df_ipdr, n_injected = inject_fraud_sequences(
        df_bank, df_cdr, df_ipdr, n=N_FRAUD_SEQUENCES
    )
    print(f"  Injected {n_injected} synchronized sequences (call->session->transfer)")

    # ─── VALIDATION & SAVE ───────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    # Date ranges
    df_bank["Timestamp"] = pd.to_datetime(df_bank["Timestamp"])
    df_cdr["Call_Start_Time"] = pd.to_datetime(df_cdr["Call_Start_Time"])
    df_ipdr["Session_Start_Time"] = pd.to_datetime(df_ipdr["Session_Start_Time"])

    print(f"\n  Bank range:  {df_bank['Timestamp'].min()} to {df_bank['Timestamp'].max()}")
    print(f"  CDR range:   {df_cdr['Call_Start_Time'].min()} to {df_cdr['Call_Start_Time'].max()}")
    print(f"  IPDR range:  {df_ipdr['Session_Start_Time'].min()} to {df_ipdr['Session_Start_Time'].max()}")

    # Phone overlap
    bp = set(df_bank["Sender_Phone_Number"].dropna().astype(int))
    cp = set(df_cdr["Caller_MSISDN"].dropna().astype(int))
    ip = set(df_ipdr["User_MSISDN"].dropna().astype(int))
    print(f"\n  Phone overlaps:")
    print(f"    Bank AND CDR:  {len(bp & cp)}")
    print(f"    Bank AND IPDR: {len(bp & ip)}")
    print(f"    CDR AND IPDR:  {len(cp & ip)}")
    print(f"    All three:     {len(bp & cp & ip)}")

    # Missed/Failed call check
    missed_dur = df_cdr[df_cdr["Call_Type"] == "Missed"]["Call_Duration_Seconds"]
    failed_dur = df_cdr[df_cdr["Call_Status"] == "Failed"]["Call_Duration_Seconds"]
    print(f"\n  Missed calls max duration: {missed_dur.max()} (should be 0)")
    print(f"  Failed calls max duration: {failed_dur.max()} (should be 0)")

    # Location check (sample)
    sample_city = "Mumbai"
    mumbai_cdr = df_cdr[df_cdr["Tower_City"] == sample_city]
    if len(mumbai_cdr) > 0:
        print(f"\n  Location check ({sample_city} CDR):")
        print(f"    Lat: {mumbai_cdr['Latitude'].min():.2f} to {mumbai_cdr['Latitude'].max():.2f} (expected ~18.9-19.2)")
        print(f"    Lon: {mumbai_cdr['Longitude'].min():.2f} to {mumbai_cdr['Longitude'].max():.2f} (expected ~72.7-73.0)")

    # Null check
    cdr_nulls = df_cdr.isnull().sum()
    cdr_nulls = cdr_nulls[cdr_nulls > 0]
    ipdr_nulls = df_ipdr.isnull().sum()
    ipdr_nulls = ipdr_nulls[ipdr_nulls > 0]
    print(f"\n  CDR columns with nulls: {len(cdr_nulls)}")
    for col, cnt in cdr_nulls.items():
        print(f"    {col}: {cnt:,} ({cnt/len(df_cdr)*100:.1f}%)")
    print(f"  IPDR columns with nulls: {len(ipdr_nulls)}")
    for col, cnt in ipdr_nulls.items():
        print(f"    {col}: {cnt:,} ({cnt/len(df_ipdr)*100:.1f}%)")

    # Final shapes
    print(f"\n  Final shapes:")
    print(f"    Bank: {df_bank.shape}")
    print(f"    CDR:  {df_cdr.shape}")
    print(f"    IPDR: {df_ipdr.shape}")

    # ─── SAVE ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SAVING")
    print("=" * 70)

    df_bank.to_csv(BANK_OUT, index=False)
    df_cdr.to_csv(CDR_OUT, index=False)
    df_ipdr.to_csv(IPDR_OUT, index=False)

    for path in [BANK_OUT, CDR_OUT, IPDR_OUT]:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  {os.path.basename(path):30s} {size_mb:.1f} MB")

    print("\n" + "=" * 70)
    print("DONE. Final datasets: F:\\ERAKSHAK\\TRI-NETRA\\data\\final\\")
    print("=" * 70)
