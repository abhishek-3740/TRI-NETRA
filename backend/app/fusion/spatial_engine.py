"""
Spatio-temporal clustering (ST-DBSCAN) for CDR cell-tower co-location.
Flags two suspects as "physically co-located" if they ping the same tower
within a tight time window.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from typing import List, Dict

COLOCATION_TIME_WINDOW_SEC = 5 * 60
EPS_METERS = 300       # spatial radius for "same tower" clustering
MIN_SAMPLES = 2


def st_dbscan(records: List[Dict], eps_spatial=EPS_METERS, eps_temporal=COLOCATION_TIME_WINDOW_SEC) -> List[int]:
    """
    Simple ST-DBSCAN implementation: builds a combined spatial+temporal
    distance matrix and clusters with scikit-learn's DBSCAN using a
    precomputed metric.
    """
    n = len(records)
    if n == 0:
        return []

    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            spatial_dist = _haversine_m(records[i]["lat"], records[i]["lon"], records[j]["lat"], records[j]["lon"])
            temporal_dist = abs(records[i]["timestamp"] - records[j]["timestamp"])
            # Combine: only "close" if BOTH spatially and temporally close
            dist_matrix[i, j] = max(spatial_dist / eps_spatial, temporal_dist / eps_temporal)

    clustering = DBSCAN(eps=1.0, min_samples=MIN_SAMPLES, metric="precomputed").fit(dist_matrix)
    return clustering.labels_.tolist()


def get_colocation_clusters(case_id: str) -> List[Dict]:
    """TODO: load real CDR records for case_id from Postgres, then cluster."""
    records: List[Dict] = []
    labels = st_dbscan(records)
    clusters = []
    for label in set(labels):
        if label == -1:
            continue  # noise, not a real cluster
        members = [records[i] for i, l in enumerate(labels) if l == label]
        clusters.append({"cluster_id": int(label), "members": members})
    return clusters


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    from math import radians, sin, cos, sqrt, atan2
    R = 6371000  # Earth radius in meters
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))
