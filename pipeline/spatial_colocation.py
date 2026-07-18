"""
pipeline/spatial_colocation.py
Spatial-Temporal Co-location / Criminal Hideout Detection for TRI-NETRA (ERH26_PS_03).

Uses DBSCAN as a proxy for ST-DBSCAN on CDR cell-tower pings.
Clusters in 3D Space-Time (Latitude, Longitude, Timestamp) to find
locations where multiple distinct entities gather simultaneously.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import polars as pl
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler


# ── Config ───────────────────────────────────────────────────────────────────

EPS = 0.5               # DBSCAN epsilon in standardized units (~0.5 std)
MIN_SAMPLES = 3       # Min points to form a cluster
KM_PER_DEGREE_LAT = 111.32


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class HideoutCluster:
    cluster_id: int
    point_count: int
    unique_entity_count: int
    entity_ids: List[str]
    center_lat: float
    center_lon: float
    time_span_hours: float
    events: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "point_count": self.point_count,
            "unique_entity_count": self.unique_entity_count,
            "entity_ids": self.entity_ids,
            "center_lat": round(self.center_lat, 6),
            "center_lon": round(self.center_lon, 6),
            "time_span_hours": round(self.time_span_hours, 2),
            "events": self.events,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _build_phone_dict(entities: Dict) -> Dict[str, str]:
    """Map phone number → canonical entity_id from entities.json."""
    phone_dict: Dict[str, str] = {}
    for eid, ent in entities.items():
        for phone in ent.get("phones", []):
            phone_dict[str(phone)] = eid
    return phone_dict


# ── Feature Engineering ──────────────────────────────────────────────────────

def _project_to_local_km(
    lats: np.ndarray,
    lons: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """
    Convert lat/lon degrees to local Cartesian kilometers.
    Uses dataset centroid as origin.
    """
    lat_mean = float(np.mean(lats))
    lon_mean = float(np.mean(lons))

    # 1° latitude ≈ 111.32 km everywhere
    y_km = (lats - lat_mean) * KM_PER_DEGREE_LAT
    # 1° longitude ≈ 111.32 km * cos(latitude)
    x_km = (lons - lon_mean) * KM_PER_DEGREE_LAT * math.cos(math.radians(lat_mean))

    return x_km, y_km, lat_mean, lon_mean


def _build_space_time_matrix(df: pl.DataFrame) -> Tuple[np.ndarray, StandardScaler]:
    """
    Build a 3D feature matrix [x_km, y_km, time_hours] and scale it.

    ST-DBSCAN Proxy Logic:
      1. Project lat/lon to local Cartesian coordinates (kilometers).
      2. Convert timestamps to hours relative to the first event.
      3. Stack into [x_km, y_km, time_hours].
      4. Apply StandardScaler so each dimension has mean=0, std=1.
         Because spatial and temporal units are already in comparable
         scales (km vs hours), StandardScaler approximately preserves
         the "1 km ≈ 1 hour" relationship. eps=0.5 then means roughly
         half a standard-deviation radius in the combined space-time.
    """
    lats = df["Latitude"].to_numpy()
    lons = df["Longitude"].to_numpy()
    timestamps = df["timestamp"].to_numpy()

    # Spatial projection (km)
    x_km, y_km, _, _ = _project_to_local_km(lats, lons)

    # Temporal projection (hours from first event)
    t_min = timestamps.min()
    time_hours = (timestamps - t_min).astype('timedelta64[s]').astype(float) / 3600.0

    # 3D matrix
    X = np.column_stack([x_km, y_km, time_hours])

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"[SC] Space-time matrix: {X_scaled.shape} "
          f"(spatial std={scaler.scale_[0]:.2f}km, {scaler.scale_[1]:.2f}km, "
          f"temporal std={scaler.scale_[2]:.2f}h)")
    return X_scaled, scaler


# ── Core Detection ─────────────────────────────────────────────────────────

def detect_criminal_hideouts(
    cdr_path: str | Path,
    entities_path: str | Path,
    eps: float = EPS,
    min_samples: int = MIN_SAMPLES,
) -> List[HideoutCluster]:
    """
    1. Load CDR + entities
    2. Map caller/receiver to canonical entity_id
    3. Build 3D space-time matrix
    4. Run DBSCAN
    5. Return clusters with >= 2 distinct entities
    """
    # ── Load entities ──────────────────────────────────────────────────
    with open(entities_path, "r", encoding="utf-8") as f:
        entities = json.load(f)
    phone_dict = _build_phone_dict(entities)

    # ── Load & filter CDR ──────────────────────────────────────────────
    cdr = pl.read_csv(cdr_path, try_parse_dates=True, infer_schema_length=1000000)

    # Keep only rows with valid lat/lon/timestamp
    cdr = cdr.filter(
        pl.col("Latitude").is_not_null()
        & pl.col("Longitude").is_not_null()
        & pl.col("Call_Start_Time").is_not_null()
    ).with_columns(
        pl.col("Call_Start_Time")
        .map_elements(_to_dt, return_dtype=pl.Datetime)
        .alias("timestamp")
    ).filter(pl.col("timestamp").is_not_null())

    print(f"[SC] CDR rows with valid geo+time: {cdr.height}")

    # ── Map both caller and receiver to entity_id ──────────────────────
    # Each CDR row produces 2 geo-events: caller at tower, receiver at tower.
    # This lets us detect when multiple entities are near the same tower
    # at the same time (meeting / shared hideout).

    caller_df = cdr.with_columns(
        pl.col("Caller_MSISDN")
        .cast(pl.Utf8)
        .replace_strict(phone_dict, default=None)
        .alias("entity_id"),
        pl.col("Caller_MSISDN").cast(pl.Utf8).alias("msisdn"),
        pl.lit("caller").alias("role"),
    ).filter(pl.col("entity_id").is_not_null())

    receiver_df = cdr.with_columns(
        pl.col("Receiver_MSISDN")
        .cast(pl.Utf8)
        .replace_strict(phone_dict, default=None)
        .alias("entity_id"),
        pl.col("Receiver_MSISDN").cast(pl.Utf8).alias("msisdn"),
        pl.lit("receiver").alias("role"),
    ).filter(pl.col("entity_id").is_not_null())

    # Combine into unified event stream
    events = pl.concat([caller_df, receiver_df])
    print(f"[SC] Total geo-events (caller+receiver): {events.height}")

    if events.height == 0:
        print("[SC] No geo-tagged events found. Returning empty.")
        return []

    # ── Daily-windowed DBSCAN ──────────────────────────────────────────
    # Running DBSCAN on a full year of country-wide data in one shot
    # makes eps=0.5 in StandardScaler space cover thousands of km and
    # months of time. Instead, we process each day separately so that
    # DBSCAN clusters compare only events within the same 24-hour window,
    # making spatial proximity the dominant clustering dimension.

    events = events.with_columns(
        pl.col("timestamp").cast(pl.Date).alias("_date")
    )

    hideouts: List[HideoutCluster] = []
    cluster_id_offset = 0
    unique_dates = sorted(events["_date"].unique().to_list())
    print(f"[SC] Processing {len(unique_dates)} daily windows...")

    for date_val in unique_dates:
        day_events = events.filter(pl.col("_date") == date_val)
        if day_events.height < min_samples:
            continue

        # Build space-time matrix for this day only
        try:
            X_scaled, scaler = _build_space_time_matrix(day_events)
        except Exception:
            continue

        # Run DBSCAN on this day's events
        db = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean", n_jobs=-1)
        labels = db.fit_predict(X_scaled)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        if n_clusters == 0:
            continue

        # Analyze clusters for this day
        day_events = day_events.with_columns(pl.Series("cluster_id", labels))

        unique_labels = set(labels)
        unique_labels.discard(-1)

        for cid in sorted(unique_labels):
            cluster_df = day_events.filter(pl.col("cluster_id") == cid)
            entity_ids = sorted(set(cluster_df["entity_id"].to_list()))

            # Only flag clusters with >= 2 distinct canonical entities
            if len(entity_ids) < 2:
                continue

            lats = cluster_df["Latitude"].to_numpy()
            lons = cluster_df["Longitude"].to_numpy()
            times = cluster_df["timestamp"].to_numpy()

            # Event details (limit to first 20 to keep JSON small)
            event_rows = cluster_df.head(20).to_dicts()
            event_list = [
                {
                    "entity_id": r["entity_id"],
                    "msisdn": r["msisdn"],
                    "role": r["role"],
                    "timestamp": r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else str(r["timestamp"]),
                    "lat": r["Latitude"],
                    "lon": r["Longitude"],
                    "tower_city": r.get("Tower_City"),
                    "cdr_id": r.get("CDR_ID"),
                }
                for r in event_rows
            ]

            time_span = float(
                (times.max() - times.min()).astype('timedelta64[s]').astype(float) / 3600.0
            ) if len(times) > 1 else 0.0

            hideouts.append(
                HideoutCluster(
                    cluster_id=cluster_id_offset + int(cid),
                    point_count=len(cluster_df),
                    unique_entity_count=len(entity_ids),
                    entity_ids=entity_ids,
                    center_lat=float(np.mean(lats)),
                    center_lon=float(np.mean(lons)),
                    time_span_hours=time_span,
                    events=event_list,
                )
            )

        cluster_id_offset += n_clusters

    # Sort by number of distinct entities (most suspicious first)
    hideouts.sort(key=lambda h: h.unique_entity_count, reverse=True)

    print(f"[SC] Flagged {len(hideouts)} criminal hideouts "
          f"(clusters with >= 2 distinct entities across {len(unique_dates)} daily windows).")
    return hideouts


# ── Persistence ────────────────────────────────────────────────────────────

def save_hideouts(hideouts: List[HideoutCluster], path: str | Path) -> None:
    out = {
        "generated_at": datetime.now().isoformat(),
        "eps": EPS,
        "min_samples": MIN_SAMPLES,
        "hideout_count": len(hideouts),
        "criminal_hideouts": [h.to_dict() for h in hideouts],
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[SC] Saved {len(hideouts)} hideouts to {path}")


# ── Main Runner ─────────────────────────────────────────────────────────────

def run_spatial_colocation(
    cdr_path: str | Path,
    entities_path: str | Path,
    out_json: str | Path,
    eps: float = EPS,
    min_samples: int = MIN_SAMPLES,
) -> List[HideoutCluster]:
    hideouts = detect_criminal_hideouts(cdr_path, entities_path, eps, min_samples)
    save_hideouts(hideouts, out_json)
    return hideouts


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent

    run_spatial_colocation(
        cdr_path=ROOT / "data" / "final" / "cdr_final.csv",
        entities_path=ROOT / "data" / "final" / "entities.json",
        out_json=ROOT / "data" / "final" / "criminal_hideouts.json",
        eps=0.5,
        min_samples=3,
    )
