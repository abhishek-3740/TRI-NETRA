"""
pipeline/impossible_travel.py
Geo-Velocity / Impossible Travel Detection for TRI-NETRA (ERH26_PS_03).

Flags canonical entities whose location trail implies physically
impossible travel speeds (> 800 km/h over > 100 km).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import polars as pl


# ── Config ───────────────────────────────────────────────────────────────────

VELOCITY_THRESHOLD_KMH = 800.0   # faster than commercial jet
MIN_DISTANCE_KM = 100.0            # ignore GPS jitter below this
EARTH_RADIUS_KM = 6371.0


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class GeoEvent:
    entity_id: str
    timestamp: datetime
    lat: float
    lon: float
    source: str
    event_id: str
    city: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "lat": self.lat,
            "lon": self.lon,
            "source": self.source,
            "event_id": self.event_id,
            "city": self.city,
        }


@dataclass
class ImpossibleTravelAnomaly:
    entity_id: str
    from_event: GeoEvent
    to_event: GeoEvent
    distance_km: float
    time_delta_hours: float
    velocity_kmh: float
    severity: str

    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "from_event": self.from_event.to_dict(),
            "to_event": self.to_event.to_dict(),
            "distance_km": round(self.distance_km, 2),
            "time_delta_hours": round(self.time_delta_hours, 4),
            "velocity_kmh": round(self.velocity_kmh, 2),
            "severity": self.severity,
        }


# ── Haversine ────────────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth (km).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


# ── Time parser ───────────────────────────────────────────────────────────────

def _to_dt(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


# ── Entity mapping ───────────────────────────────────────────────────────────

def _build_phone_dict(entities: Dict) -> Dict[str, str]:
    """phone -> entity_id"""
    phone_dict: Dict[str, str] = {}
    for eid, ent in entities.items():
        for phone in ent.get("phones", []):
            phone_dict[str(phone)] = eid
    return phone_dict


# ── Geo-event extractors ─────────────────────────────────────────────────────

def _extract_cdr_geo(cdr: pl.DataFrame, phone_dict: Dict[str, str]) -> pl.DataFrame:
    """
    Extract CDR rows with valid lat/lon.
    Emits TWO geo events per row: one for caller, one for receiver
    (both were at the tower location during the call).
    """
    base = cdr.filter(
        pl.col("Latitude").is_not_null() & pl.col("Longitude").is_not_null()
    ).with_columns(
        pl.col("Call_Start_Time").map_elements(_to_dt, return_dtype=pl.Datetime).alias("timestamp"),
        pl.col("Latitude").alias("lat"),
        pl.col("Longitude").alias("lon"),
        pl.col("CDR_ID").alias("event_id"),
        pl.col("Tower_City").alias("city"),
    )

    # Caller side
    caller = base.with_columns(
        pl.col("Caller_MSISDN").cast(pl.Utf8).replace_strict(phone_dict, default=None).alias("entity_id"),
        pl.lit("cdr_caller").alias("source"),
    ).filter(pl.col("entity_id").is_not_null() & pl.col("timestamp").is_not_null())

    # Receiver side
    receiver = base.with_columns(
        pl.col("Receiver_MSISDN").cast(pl.Utf8).replace_strict(phone_dict, default=None).alias("entity_id"),
        pl.lit("cdr_receiver").alias("source"),
    ).filter(pl.col("entity_id").is_not_null() & pl.col("timestamp").is_not_null())

    return pl.concat([caller, receiver])


def _extract_ipdr_geo(ipdr: pl.DataFrame, phone_dict: Dict[str, str]) -> pl.DataFrame:
    """
    Extract IPDR rows with valid lat/lon and map to entity via User_MSISDN.
    """
    return ipdr.filter(
        pl.col("Latitude").is_not_null() & pl.col("Longitude").is_not_null()
    ).with_columns(
        pl.col("Session_Start_Time").map_elements(_to_dt, return_dtype=pl.Datetime).alias("timestamp"),
        pl.col("User_MSISDN").cast(pl.Utf8).replace_strict(phone_dict, default=None).alias("entity_id"),
        pl.col("Latitude").alias("lat"),
        pl.col("Longitude").alias("lon"),
        pl.lit("ipdr").alias("source"),
        pl.col("IPDR_ID").alias("event_id"),
        pl.col("IP_Location_City").alias("city"),
    ).filter(pl.col("entity_id").is_not_null() & pl.col("timestamp").is_not_null())


def _extract_bank_geo(bank: pl.DataFrame, phone_dict: Dict[str, str]) -> pl.DataFrame:
    """
    Extract Bank rows with valid lat/lon (if present in the dataset).
    If lat/lon columns are absent, returns an empty frame gracefully.
    """
    cols = bank.columns
    lat_col = None
    lon_col = None
    city_col = "Sender_City"

    for c in cols:
        lc = c.lower()
        if "lat" in lc and "sender" in lc:
            lat_col = c
        elif "lat" in lc and lat_col is None:
            lat_col = c
        if "lon" in lc and "sender" in lc:
            lon_col = c
        elif "lon" in lc and lon_col is None:
            lon_col = c

    if lat_col is None or lon_col is None:
        # Bank schema in this dataset does not include lat/lon
        return pl.DataFrame(schema={
            "entity_id": pl.Utf8, "timestamp": pl.Datetime,
            "lat": pl.Float64, "lon": pl.Float64,
            "source": pl.Utf8, "event_id": pl.Utf8, "city": pl.Utf8,
        })

    return bank.filter(
        pl.col(lat_col).is_not_null() & pl.col(lon_col).is_not_null()
    ).with_columns(
        pl.col("Timestamp").map_elements(_to_dt, return_dtype=pl.Datetime).alias("timestamp"),
        pl.col("Sender_Phone_Number").cast(pl.Utf8).replace_strict(phone_dict, default=None).alias("entity_id"),
        pl.col(lat_col).alias("lat"),
        pl.col(lon_col).alias("lon"),
        pl.lit("bank").alias("source"),
        pl.col("Transaction_ID").alias("event_id"),
        pl.col(city_col).alias("city"),
    ).filter(pl.col("entity_id").is_not_null() & pl.col("timestamp").is_not_null())


# ── Core detection ───────────────────────────────────────────────────────────

def detect_impossible_travel(
    entities_path: str | Path,
    bank_path: str | Path,
    cdr_path: str | Path,
    ipdr_path: str | Path,
) -> List[ImpossibleTravelAnomaly]:
    """
    1. Load entities + 3 datasets
    2. Extract geo-tagged events per entity
    3. Sort chronologically per entity
    4. Haversine + velocity check between consecutive events
    5. Return flagged anomalies
    """
    print("[IT] Loading entities and datasets...")
    with open(entities_path, "r", encoding="utf-8") as f:
        entities = json.load(f)

    phone_dict = _build_phone_dict(entities)

    bank = pl.read_csv(bank_path, try_parse_dates=True, infer_schema_length=1000000)
    cdr = pl.read_csv(cdr_path, try_parse_dates=True, infer_schema_length=1000000)
    ipdr = pl.read_csv(ipdr_path, try_parse_dates=True, infer_schema_length=1000000)

    # Extract geo events from each dataset
    bank_geo = _extract_bank_geo(bank, phone_dict)
    cdr_geo = _extract_cdr_geo(cdr, phone_dict)
    ipdr_geo = _extract_ipdr_geo(ipdr, phone_dict)

    # Unify to common schema
    common_cols = ["entity_id", "timestamp", "lat", "lon", "source", "event_id", "city"]
    all_geo = pl.concat([
        bank_geo.select(common_cols),
        cdr_geo.select(common_cols),
        ipdr_geo.select(common_cols),
    ])

    print(f"[IT] Total geo-tagged events: {all_geo.height}")

    anomalies: List[ImpossibleTravelAnomaly] = []

    # Group by entity, sort chronologically within each group
    for entity_id, group in all_geo.group_by("entity_id"):
        group_sorted = group.sort("timestamp")
        rows = group_sorted.to_dicts()
        if len(rows) < 2:
            continue

        for i in range(1, len(rows)):
            prev = rows[i - 1]
            curr = rows[i]

            lat1, lon1 = float(prev["lat"]), float(prev["lon"])
            lat2, lon2 = float(curr["lat"]), float(curr["lon"])

            distance = haversine(lat1, lon1, lat2, lon2)

            t1 = prev["timestamp"]
            t2 = curr["timestamp"]
            if t1 is None or t2 is None:
                continue

            time_delta_hours = (t2 - t1).total_seconds() / 3600.0
            if time_delta_hours <= 0:
                continue  # same-time or out-of-order

            velocity = distance / time_delta_hours

            if velocity > VELOCITY_THRESHOLD_KMH and distance > MIN_DISTANCE_KM:
                severity = "critical" if velocity > 1200 else "high"
                anomalies.append(
                    ImpossibleTravelAnomaly(
                        entity_id=entity_id,
                        from_event=GeoEvent(
                            entity_id=entity_id,
                            timestamp=t1,
                            lat=lat1,
                            lon=lon1,
                            source=prev["source"],
                            event_id=prev["event_id"],
                            city=prev.get("city"),
                        ),
                        to_event=GeoEvent(
                            entity_id=entity_id,
                            timestamp=t2,
                            lat=lat2,
                            lon=lon2,
                            source=curr["source"],
                            event_id=curr["event_id"],
                            city=curr.get("city"),
                        ),
                        distance_km=distance,
                        time_delta_hours=time_delta_hours,
                        velocity_kmh=velocity,
                        severity=severity,
                    )
                )

    print(f"[IT] Analyzed {len(entities)} entities, found {len(anomalies)} impossible travel events.")
    return anomalies


# ── Persistence ──────────────────────────────────────────────────────────────

def save_anomalies(anomalies: List[ImpossibleTravelAnomaly], path: str | Path) -> None:
    out = {
        "generated_at": datetime.now().isoformat(),
        "velocity_threshold_kmh": VELOCITY_THRESHOLD_KMH,
        "min_distance_km": MIN_DISTANCE_KM,
        "anomaly_count": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
    }
    Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[IT] Saved {len(anomalies)} anomalies to {path}")


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_impossible_travel(
    entities_path: str | Path,
    bank_path: str | Path,
    cdr_path: str | Path,
    ipdr_path: str | Path,
    out_json: str | Path,
) -> List[ImpossibleTravelAnomaly]:
    anomalies = detect_impossible_travel(entities_path, bank_path, cdr_path, ipdr_path)
    save_anomalies(anomalies, out_json)
    return anomalies


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent

    run_impossible_travel(
        entities_path=ROOT / "data" / "final" / "entities.json",
        bank_path=ROOT / "data" / "final" / "bank_transactions.csv",
        cdr_path=ROOT / "data" / "final" / "cdr_final.csv",
        ipdr_path=ROOT / "data" / "final" / "ipdr_final.csv",
        out_json=ROOT / "data" / "final" / "impossible_travel.json",
    )
