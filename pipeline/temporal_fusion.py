"""
pipeline/temporal_fusion.py
Temporal Correlation Engine for TRI-NETRA (ERH26_PS_03).

Slides a ±N-minute window across Bank + CDR + IPDR per entity
to surface temporal coincidences (the "smoking gun" moments).

Now with Cascade Lookups: Phone → Account → UPI → IMEI → IP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import polars as pl


# ── Config ───────────────────────────────────────────────────────────────────

DEFAULT_WINDOW_MINUTES = 30


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class FusionEvent:
    entity_id: str
    window_start: datetime
    window_end: datetime
    bank_records: List[Dict] = field(default_factory=list)
    cdr_records: List[Dict] = field(default_factory=list)
    ipdr_records: List[Dict] = field(default_factory=list)
    is_injected: bool = False
    risk_score: int = 0

    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "bank_count": len(self.bank_records),
            "cdr_count": len(self.cdr_records),
            "ipdr_count": len(self.ipdr_records),
            "is_injected": self.is_injected,
            "risk_score": self.risk_score,
            "bank_ids": [r.get("Transaction_ID") for r in self.bank_records],
            "cdr_ids": [r.get("CDR_ID") for r in self.cdr_records],
            "ipdr_ids": [r.get("IPDR_ID") for r in self.ipdr_records],
        }


# ── Time helpers ─────────────────────────────────────────────────────────────

def _to_dt(val) -> Optional[datetime]:
    """Robust datetime parser for Polars/pandas mixed output."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    if isinstance(val, str):
        # Try common formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S%.f",
        ):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


# ── Fusion Engine ────────────────────────────────────────────────────────────

class TemporalFusionEngine:
    def __init__(
        self,
        resolver,  # EntityResolver instance
        bank_df: pl.DataFrame,
        cdr_df: pl.DataFrame,
        ipdr_df: pl.DataFrame,
        window_minutes: int = DEFAULT_WINDOW_MINUTES,
    ):
        self.resolver = resolver
        self.window = timedelta(minutes=window_minutes)

        # Build cascade lookup dictionaries from entities
        self._build_lookup_dicts()

        # Normalize timestamps and map to entities via cascade lookups
        self.bank = self._prep_bank(bank_df)
        self.cdr = self._prep_cdr(cdr_df)
        self.ipdr = self._prep_ipdr(ipdr_df)

        self.events: List[FusionEvent] = []

    # ── Cascade Lookup Dictionaries ─────────────────────────────────────────

    def _build_lookup_dicts(self) -> None:
        """
        Build multiple mapping dicts from the canonical entities so we can
        cascade through identifiers: Phone → Account → UPI → IMEI → IP.
        """
        self.phone_dict: Dict[str, str] = {}
        self.account_dict: Dict[str, str] = {}
        self.upi_dict: Dict[str, str] = {}
        self.imei_dict: Dict[str, str] = {}
        self.ip_dict: Dict[str, str] = {}

        for eid, ent in self.resolver.entities.items():
            for phone in ent.get("phones", []):
                self.phone_dict[str(phone)] = eid
            for acc in ent.get("accounts", []):
                self.account_dict[str(acc)] = eid
            for upi in ent.get("upis", []):
                self.upi_dict[str(upi).lower()] = eid
            for imei in ent.get("imeis", []):
                self.imei_dict[str(imei)] = eid
            for ip in ent.get("ips", []):
                self.ip_dict[str(ip)] = eid

        print(
            f"[TF] Lookup dicts built: "
            f"phones={len(self.phone_dict)}, accounts={len(self.account_dict)}, "
            f"upis={len(self.upi_dict)}, imeis={len(self.imei_dict)}, ips={len(self.ip_dict)}"
        )

    # ── Prep with Cascade Lookups ───────────────────────────────────────────

    def _prep_bank(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.with_columns(
            pl.col("Timestamp").map_elements(
                _to_dt, return_dtype=pl.Datetime
            ).alias("_dt")
        )

        # Sender: Phone → Account → UPI
        df = df.with_columns(
            pl.coalesce(
                pl.col("Sender_Phone_Number").cast(pl.Utf8).replace_strict(self.phone_dict, default=None),
                pl.col("Sender_Account_Number").cast(pl.Utf8).replace_strict(self.account_dict, default=None),
                pl.col("Sender_UPI_ID").cast(pl.Utf8).str.to_lowercase().replace_strict(self.upi_dict, default=None),
            ).alias("sender_entity"),
        )

        # Receiver: Phone → Account → UPI
        df = df.with_columns(
            pl.coalesce(
                pl.col("Receiver_Phone_Number").cast(pl.Utf8).replace_strict(self.phone_dict, default=None),
                pl.col("Receiver_Account_Number").cast(pl.Utf8).replace_strict(self.account_dict, default=None),
                pl.col("Receiver_UPI_ID").cast(pl.Utf8).str.to_lowercase().replace_strict(self.upi_dict, default=None),
            ).alias("receiver_entity"),
        )

        return df

    def _prep_cdr(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.with_columns(
            pl.col("Call_Start_Time").map_elements(
                _to_dt, return_dtype=pl.Datetime
            ).alias("_dt")
        )

        # Caller: Phone → IMEI
        df = df.with_columns(
            pl.coalesce(
                pl.col("Caller_MSISDN").cast(pl.Utf8).replace_strict(self.phone_dict, default=None),
                pl.col("IMEI").cast(pl.Utf8).replace_strict(self.imei_dict, default=None),
            ).alias("caller_entity"),
        )

        # Receiver: Phone → IMEI
        df = df.with_columns(
            pl.coalesce(
                pl.col("Receiver_MSISDN").cast(pl.Utf8).replace_strict(self.phone_dict, default=None),
                pl.col("IMEI").cast(pl.Utf8).replace_strict(self.imei_dict, default=None),
            ).alias("receiver_entity"),
        )

        return df

    def _prep_ipdr(self, df: pl.DataFrame) -> pl.DataFrame:
        df = df.with_columns(
            pl.col("Session_Start_Time").map_elements(
                _to_dt, return_dtype=pl.Datetime
            ).alias("_dt")
        )

        # IPDR user: Phone → IMEI → IP
        df = df.with_columns(
            pl.coalesce(
                pl.col("User_MSISDN").cast(pl.Utf8).replace_strict(self.phone_dict, default=None),
                pl.col("IMEI").cast(pl.Utf8).replace_strict(self.imei_dict, default=None),
                pl.col("Public_IP_Address").cast(pl.Utf8).replace_strict(self.ip_dict, default=None),
            ).alias("entity_id"),
        )

        return df

    # ── Core fusion per entity ───────────────────────────────────────────────

    def fuse_entity(self, entity_id: str, b_rows, c_rows, i_rows) -> List[FusionEvent]:
        """
        For a single canonical entity, find all temporal coincidences
        where Bank, CDR, and IPDR events fall within the sliding window.
        """

        # Collect all timestamps
        anchors: List[Tuple[datetime, str, Dict]] = []
        for r in b_rows:
            dt = r.get("_dt")
            if dt:
                anchors.append((dt, "bank", r))
        for r in c_rows:
            dt = r.get("_dt")
            if dt:
                anchors.append((dt, "cdr", r))
        for r in i_rows:
            dt = r.get("_dt")
            if dt:
                anchors.append((dt, "ipdr", r))

        if not anchors:
            return []

        anchors.sort(key=lambda x: x[0])

        events: List[FusionEvent] = []
        used = set()

        for i, (t0, _, _) in enumerate(anchors):
            if i in used:
                continue

            win_start = t0 - self.window
            win_end = t0 + self.window

            batch_bank, batch_cdr, batch_ipdr = [], [], []
            batch_indices = []

            for j, (t, kind, rec) in enumerate(anchors):
                if win_start <= t <= win_end:
                    batch_indices.append(j)
                    if kind == "bank":
                        batch_bank.append(rec)
                    elif kind == "cdr":
                        batch_cdr.append(rec)
                    elif kind == "ipdr":
                        batch_ipdr.append(rec)

            # Only keep windows that have at least 2 dataset types
            types_present = sum([
                bool(batch_bank),
                bool(batch_cdr),
                bool(batch_ipdr),
            ])
            if types_present < 2:
                continue

            # Mark used so we don't duplicate exact same windows
            for j in batch_indices:
                used.add(j)

            # Detect injected sequences
            is_injected = any(
                str(r.get("Transaction_ID", "")).startswith("INJ_") for r in batch_bank
            ) or any(
                str(r.get("CDR_ID", "")).startswith("INJ_") for r in batch_cdr
            ) or any(
                str(r.get("IPDR_ID", "")).startswith("INJ_") for r in batch_ipdr
            )

            # Simple risk score
            risk = 0
            if batch_bank and batch_cdr and batch_ipdr:
                risk += 50  # Three-way coincidence
            elif batch_bank and batch_cdr:
                risk += 30
            elif batch_bank and batch_ipdr:
                risk += 30
            if is_injected:
                risk += 100

            ev = FusionEvent(
                entity_id=entity_id,
                window_start=win_start,
                window_end=win_end,
                bank_records=batch_bank,
                cdr_records=batch_cdr,
                ipdr_records=batch_ipdr,
                is_injected=is_injected,
                risk_score=risk,
            )
            events.append(ev)

        return events

    # ── Run all ──────────────────────────────────────────────────────────────

    def run(self, top_n: Optional[int] = None) -> List[FusionEvent]:
        """
        Run fusion across all entities. Returns sorted by risk_score desc.
        """
        all_events: List[FusionEvent] = []
        entity_ids = list(self.resolver.entities.keys())

        print(f"[TF] Fusing {len(entity_ids)} entities with ±{self.window.seconds//60}min window…")
        
        print("[TF] Pre-grouping dataframes...")
        b_grouped, c_grouped, i_grouped = {}, {}, {}
        for r in self.bank.to_dicts():
            s = r.get("sender_entity")
            re = r.get("receiver_entity")
            if s:
                b_grouped.setdefault(s, []).append(r)
            if re and re != s:
                b_grouped.setdefault(re, []).append(r)
            
        for r in self.cdr.to_dicts():
            ce = r.get("caller_entity")
            re = r.get("receiver_entity")
            if ce:
                c_grouped.setdefault(ce, []).append(r)
            if re and re != ce:
                c_grouped.setdefault(re, []).append(r)
            
        for r in self.ipdr.to_dicts():
            e = r.get("entity_id")
            if e:
                i_grouped.setdefault(e, []).append(r)
            
        print("[TF] Data pre-grouped. Running sliding window...")
        for eid in entity_ids:
            evs = self.fuse_entity(
                eid,
                b_rows=b_grouped.get(eid, []),
                c_rows=c_grouped.get(eid, []),
                i_rows=i_grouped.get(eid, [])
            )
            all_events.extend(evs)

        all_events.sort(key=lambda e: e.risk_score, reverse=True)

        injected = [e for e in all_events if e.is_injected]
        print(f"[TF] Total fusion events: {len(all_events)}")
        print(f"[TF] Injected (ground-truth) sequences caught: {len(injected)}")

        if top_n:
            return all_events[:top_n]
        return all_events

    def to_dataframe(self, events: Optional[List[FusionEvent]] = None) -> pl.DataFrame:
        if events is None:
            events = self.events
        rows = [e.to_dict() for e in events]
        return pl.DataFrame(rows)

    def save(self, events: List[FusionEvent], path: str | Path) -> None:
        rows = [e.to_dict() for e in events]
        Path(path).write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
        print(f"[TF] Saved {len(rows)} events to {path}")


# ── One-shot runner ──────────────────────────────────────────────────────────

def run_fusion(
    resolver,  # EntityResolver
    bank_path: str | Path,
    cdr_path: str | Path,
    ipdr_path: str | Path,
    window_minutes: int = 30,
    out_path: Optional[str | Path] = None,
) -> List[FusionEvent]:
    bank = pl.read_csv(bank_path, try_parse_dates=True, infer_schema_length=1000000)
    cdr = pl.read_csv(cdr_path, try_parse_dates=True, infer_schema_length=1000000)
    ipdr = pl.read_csv(ipdr_path, try_parse_dates=True, infer_schema_length=1000000)

    engine = TemporalFusionEngine(
        resolver=resolver,
        bank_df=bank,
        cdr_df=cdr,
        ipdr_df=ipdr,
        window_minutes=window_minutes,
    )
    events = engine.run()
    if out_path:
        engine.save(events, out_path)
    return events


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from entity_resolution import resolve_all

    ROOT = Path(__file__).parent.parent

    # 1. Resolve entities
    resolver = resolve_all(
        bank_path=ROOT / "data" / "final" / "bank_transactions.csv",
        cdr_path=ROOT / "data" / "final" / "cdr_final.csv",
        ipdr_path=ROOT / "data" / "final" / "ipdr_final.csv",
    )

    # 2. Run temporal fusion
    events = run_fusion(
        resolver=resolver,
        bank_path=ROOT / "data" / "final" / "bank_transactions.csv",
        cdr_path=ROOT / "data" / "final" / "cdr_final.csv",
        ipdr_path=ROOT / "data" / "final" / "ipdr_final.csv",
        window_minutes=30,
        out_path=ROOT / "data" / "final" / "fusion_events.json",
    )