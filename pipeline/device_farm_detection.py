"""
pipeline/device_farm_detection.py
Device Farm Detection (IMEI/SIM Clustering) for TRI-NETRA (ERH26_PS_03).

Analyzes CDR and IPDR to find physical devices (IMEIs) shared by
multiple SIM cards (MSISDNs) — a classic mule-account / fraud-farm signal.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import polars as pl


# ── Config ───────────────────────────────────────────────────────────────────

TOP_N = 50


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class DeviceFarm:
    imei: str
    risk_score: float
    risk_tier: str
    sim_count: int
    msisdns: List[str]
    cdr_record_count: int
    ipdr_record_count: int
    total_record_count: int

    def to_dict(self) -> Dict:
        return {
            "imei": self.imei,
            "risk_score": round(self.risk_score, 4),
            "risk_tier": self.risk_tier,
            "sim_count": self.sim_count,
            "msisdns": self.msisdns,
            "cdr_record_count": self.cdr_record_count,
            "ipdr_record_count": self.ipdr_record_count,
            "total_record_count": self.total_record_count,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _norm_imei(v) -> Optional[str]:
    """Normalize IMEI from int/float/null to clean string."""
    if v is None:
        return None
    s = str(int(v)) if isinstance(v, (float, int)) else str(v)
    s = s.strip().split(".")[0]
    return s if s.isdigit() and len(s) >= 14 else None


def _risk_tier(sim_count: int) -> str:
    if sim_count >= 6:
        return "critical"
    if sim_count >= 4:
        return "high"
    if sim_count >= 3:
        return "medium"
    return "low"


def _compute_risk_score(sim_count: int, total_records: int) -> float:
    """
    Mule risk heuristic:
      • 1 SIM  → normal device (score 0)
      • 2 SIMs → minor flag (linear)
      • 3+ SIMs → super-linear penalty (device farm territory)
    Volume factor: log1p(total_records) so high-usage farms score higher.
    """
    if sim_count <= 1:
        return 0.0
    base = (sim_count - 1) ** 1.8
    volume = math.log1p(total_records)
    return base * volume


# ── Core Engine ──────────────────────────────────────────────────────────────

def detect_device_farms(
    cdr_path: str | Path,
    ipdr_path: str | Path,
    top_n: int = TOP_N,
) -> List[DeviceFarm]:
    """
    1. Load CDR + IPDR
    2. Build IMEI → MSISDN mappings (CDR: Caller_MSISDN, IPDR: User_MSISDN)
    3. Aggregate per IMEI: unique SIM count, record counts
    4. Score and rank
    """
    print("[DF] Loading CDR and IPDR...")
    cdr = pl.read_csv(cdr_path, try_parse_dates=True, infer_schema_length=1000000)
    ipdr = pl.read_csv(ipdr_path, try_parse_dates=True, infer_schema_length=1000000)

    # ── Clean IMEIs ────────────────────────────────────────────────────────
    # Filter nulls and normalize to string
    cdr = cdr.filter(pl.col("IMEI").is_not_null()).with_columns(
        pl.col("IMEI").map_elements(_norm_imei, return_dtype=pl.Utf8).alias("imei_clean")
    ).filter(pl.col("imei_clean").is_not_null())

    ipdr = ipdr.filter(pl.col("IMEI").is_not_null()).with_columns(
        pl.col("IMEI").map_elements(_norm_imei, return_dtype=pl.Utf8).alias("imei_clean")
    ).filter(pl.col("imei_clean").is_not_null())

    print(f"[DF] CDR rows with valid IMEI: {cdr.height}")
    print(f"[DF] IPDR rows with valid IMEI: {ipdr.height}")

    # ── Build unified IMEI↔MSISDN pairs ────────────────────────────────────
    # CDR: IMEI belongs to the caller device (consistent with entity_resolution.py)
    cdr_pairs = cdr.select([
        pl.col("imei_clean").alias("imei"),
        pl.col("Caller_MSISDN").cast(pl.Utf8).alias("msisdn"),
        pl.lit("cdr").alias("source"),
    ])

    # IPDR: IMEI belongs to the user device
    ipdr_pairs = ipdr.select([
        pl.col("imei_clean").alias("imei"),
        pl.col("User_MSISDN").cast(pl.Utf8).alias("msisdn"),
        pl.lit("ipdr").alias("source"),
    ])

    all_pairs = pl.concat([cdr_pairs, ipdr_pairs])

    # ── Aggregate per IMEI ─────────────────────────────────────────────────
    grouped = all_pairs.group_by("imei").agg(
        pl.col("msisdn").unique().alias("unique_msisdns"),
        pl.col("msisdn").count().alias("total_record_count"),
        (pl.col("source") == "cdr").sum().alias("cdr_record_count"),
        (pl.col("source") == "ipdr").sum().alias("ipdr_record_count"),
    )

    print(f"[DF] Unique IMEIs found: {grouped.height}")

    # ── Score and rank ─────────────────────────────────────────────────────
    farms: List[DeviceFarm] = []
    for row in grouped.iter_rows(named=True):
        imei = row["imei"]
        msisdns = row["unique_msisdns"]  # Polars list
        if msisdns is None:
            continue

        # Convert to Python list and deduplicate (safety)
        msisdn_list: List[str] = sorted(set(str(m) for m in msisdns if m is not None))
        sim_count = len(msisdn_list)

        cdr_cnt = int(row["cdr_record_count"] or 0)
        ipdr_cnt = int(row["ipdr_record_count"] or 0)
        total_cnt = int(row["total_record_count"] or 0)

        risk = _compute_risk_score(sim_count, total_cnt)
        tier = _risk_tier(sim_count)

        farms.append(
            DeviceFarm(
                imei=imei,
                risk_score=risk,
                risk_tier=tier,
                sim_count=sim_count,
                msisdns=msisdn_list,
                cdr_record_count=cdr_cnt,
                ipdr_record_count=ipdr_cnt,
                total_record_count=total_cnt,
            )
        )

    # Sort descending by risk
    farms.sort(key=lambda f: f.risk_score, reverse=True)

    suspicious = [f for f in farms if f.sim_count >= 3]
    print(f"[DF] Total IMEIs analyzed: {len(farms)}")
    print(f"[DF] Suspicious IMEIs (>=3 SIMs): {len(suspicious)}")
    print(f"[DF] Returning top {top_n} by risk score.")

    return farms[:top_n]


# ── Persistence ──────────────────────────────────────────────────────────────

def save_device_farms(farms: List[DeviceFarm], path: str | Path) -> None:
    out = {
        "generated_at": datetime.now().isoformat(),
        "total_imeis_analyzed": len(farms),  # note: this is top_n after slicing
        "suspicious_imei_count": len([f for f in farms if f.sim_count >= 3]),
        "top_50_device_farms": [f.to_dict() for f in farms],
    }
    Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[DF] Saved results to {path}")


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_device_farm_detection(
    cdr_path: str | Path,
    ipdr_path: str | Path,
    out_json: str | Path,
    top_n: int = TOP_N,
) -> List[DeviceFarm]:
    farms = detect_device_farms(cdr_path, ipdr_path, top_n=top_n)
    save_device_farms(farms, out_json)
    return farms


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent

    run_device_farm_detection(
        cdr_path=ROOT / "data" / "final" / "cdr_final.csv",
        ipdr_path=ROOT / "data" / "final" / "ipdr_final.csv",
        out_json=ROOT / "data" / "final" / "device_farms.json",
        top_n=50,
    )
