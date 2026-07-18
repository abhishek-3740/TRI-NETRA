"""
pipeline/entity_resolution.py
Entity Resolution for TRI-NETRA (ERH26_PS_03).

Tier 1: Exact-match Union-Find on Phone, IMEI, IP, UPI→Phone, Account, Device, Name.
Tier 2: Fuzzy name matching via rapidfuzz (token_sort_ratio >= 85) with weak-identifier safety check.
Explicitly NEVER uses Subscriber_ID as a join key.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

import polars as pl
from rapidfuzz import fuzz, process


# ── Union-Find ───────────────────────────────────────────────────────────────

class UnionFind:
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}

    def _make(self, x: str) -> None:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x: str) -> str:
        self._make(x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str) -> None:
        self._make(x)
        self._make(y)
        xr, yr = self.find(x), self.find(y)
        if xr == yr:
            return
        if self.rank[xr] < self.rank[yr]:
            xr, yr = yr, xr
        self.parent[yr] = xr
        if self.rank[xr] == self.rank[yr]:
            self.rank[xr] += 1

    def groups(self) -> Dict[str, List[str]]:
        d: Dict[str, List[str]] = defaultdict(list)
        for node in self.parent:
            d[self.find(node)].append(node)
        return dict(d)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_phone_from_upi(upi: str) -> str | None:
    """Extract 10-digit phone from UPI like 9876543210@paytm"""
    if not upi:
        return None
    m = re.search(r"(\d{10})", upi)
    return m.group(1) if m else None


def _norm_phone(v) -> str | None:
    if v is None:
        return None
    s = str(int(v)) if isinstance(v, (int, float)) else str(v)
    s = s.strip()
    return s if len(s) == 10 and s.isdigit() else None


def _norm_imei(v) -> str | None:
    if v is None:
        return None
    s = str(int(v)) if isinstance(v, (float, int)) else str(v)
    s = s.strip().split(".")[0]
    return s if s.isdigit() and len(s) >= 14 else None


def _norm_ip(v) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    return s if "." in s else None


def _norm_name(v) -> str | None:
    if not v:
        return None
    return str(v).strip().lower()


def _norm_city(v) -> str | None:
    if not v:
        return None
    return str(v).strip().lower()


def _norm_network(v) -> str | None:
    if not v:
        return None
    return str(v).strip().lower()


def _key(prefix: str, val: str) -> str:
    return f"{prefix}:{val}"


# ── Core Resolver ────────────────────────────────────────────────────────────

class EntityResolver:
    """
    Resolves Bank + CDR + IPDR records into canonical entities.
    Tier 1: Exact-match Union-Find.
    Tier 2: Fuzzy name merge (rapidfuzz token_sort_ratio >= threshold)
            with weak-identifier safety check (shared city or network provider).
    """

    def __init__(self, fuzzy_threshold: int = 85):
        self.uf = UnionFind()
        # entity_id -> {phones, imeis, ips, upis, names, accounts, devices, cities, network_providers}
        self.entities: Dict[str, Dict[str, Set[str]]] = {}
        self.fuzzy_threshold = fuzzy_threshold

        # Store raw dataframes for Tier-2 weak-identifier collection
        self._bank_df: Optional[pl.DataFrame] = None
        self._cdr_df: Optional[pl.DataFrame] = None
        self._ipdr_df: Optional[pl.DataFrame] = None

    def _key(self, prefix: str, val: str) -> str:
        return f"{prefix}:{val}"

    def _link_all(self, keys: List[str | None]) -> None:
        """Union all non-null keys together."""
        clean = [k for k in keys if k]
        if len(clean) < 2:
            if clean:
                self.uf.find(clean[0])
            return
        first = clean[0]
        for k in clean[1:]:
            self.uf.union(first, k)

    # ── Ingestion (UNCHANGED from original) ─────────────────────────────────

    def ingest_bank(self, df: pl.DataFrame) -> None:
        """
        Bank records contain BOTH sender and receiver on one row.
        We split them so sender-side identifiers only union with each other,
        and receiver-side identifiers only union with each other.
        """
        self._bank_df = df
        rows = df.iter_rows(named=True)
        for r in rows:
            # Sender side
            s_phone = _norm_phone(r.get("Sender_Phone_Number"))
            s_upi = r.get("Sender_UPI_ID")
            s_upi_phone = _extract_phone_from_upi(s_upi)
            s_acc = r.get("Sender_Account_Number")
            s_name = _norm_name(r.get("Sender_Customer_Name"))

            sender_keys = []
            if s_phone:
                sender_keys.append(self._key("phone", s_phone))
            if s_upi_phone:
                sender_keys.append(self._key("phone", s_upi_phone))
            if s_acc:
                sender_keys.append(self._key("account", str(s_acc)))

            self._link_all(sender_keys)

            # Receiver side
            r_phone = _norm_phone(r.get("Receiver_Phone_Number"))
            r_upi = r.get("Receiver_UPI_ID")
            r_upi_phone = _extract_phone_from_upi(r_upi)
            r_acc = r.get("Receiver_Account_Number")
            r_name = _norm_name(r.get("Receiver_Customer_Name"))

            receiver_keys = []
            if r_phone:
                receiver_keys.append(self._key("phone", r_phone))
            if r_upi_phone:
                receiver_keys.append(self._key("phone", r_upi_phone))
            if r_acc:
                receiver_keys.append(self._key("account", str(r_acc)))

            self._link_all(receiver_keys)

    def ingest_cdr(self, df: pl.DataFrame) -> None:
        """
        CDR: Caller and Receiver are on the same row.
        We do NOT link caller to receiver (they are different people),
        but we link caller's own identifiers together, and receiver's own
        identifiers together.
        """
        self._cdr_df = df
        for r in df.iter_rows(named=True):
            # Caller side
            c_phone = _norm_phone(r.get("Caller_MSISDN"))
            c_imei = _norm_imei(r.get("IMEI"))
            c_name = r.get("Caller_Name")

            caller_keys = []
            if c_phone:
                caller_keys.append(self._key("phone", c_phone))
            if c_imei:
                caller_keys.append(self._key("imei", c_imei))

            self._link_all(caller_keys)

            # Receiver side
            rec_phone = _norm_phone(r.get("Receiver_MSISDN"))
            rec_name = r.get("Receiver_Name")

            receiver_keys = []
            if rec_phone:
                receiver_keys.append(self._key("phone", rec_phone))

            self._link_all(receiver_keys)

    def ingest_ipdr(self, df: pl.DataFrame) -> None:
        """
        IPDR: One row = one user session.
        Link phone, IMEI, IP, device_id together for that user.
        """
        self._ipdr_df = df
        for r in df.iter_rows(named=True):
            phone = _norm_phone(r.get("User_MSISDN"))
            imei = _norm_imei(r.get("IMEI"))
            pub_ip = _norm_ip(r.get("Public_IP_Address"))
            priv_ip = _norm_ip(r.get("Private_IP_Address"))
            dev_id = r.get("Device_ID")
            name = r.get("User_Name")

            keys = []
            if phone:
                keys.append(self._key("phone", phone))
            if imei:
                keys.append(self._key("imei", imei))
            if pub_ip:
                keys.append(self._key("ip", pub_ip))
            if dev_id:
                keys.append(self._key("device", str(dev_id)))

            self._link_all(keys)

    # ── Build canonical entities ─────────────────────────────────────────────

    def _build_from_groups(self, groups: Dict[str, List[str]]) -> None:
        """Collapse Union-Find groups into canonical entity objects."""
        self.entities = {}

        for root, members in groups.items():
            ent = {
                "phones": set(),
                "imeis": set(),
                "ips": set(),
                "upis": set(),
                "names": set(),
                "accounts": set(),
                "devices": set(),
                "cities": set(),
                "network_providers": set(),
            }
            for m in members:
                prefix, val = m.split(":", 1)
                if prefix == "phone":
                    ent["phones"].add(val)
                elif prefix == "imei":
                    ent["imeis"].add(val)
                elif prefix == "ip":
                    ent["ips"].add(val)
                elif prefix == "upi":
                    ent["upis"].add(val)
                elif prefix == "name":
                    ent["names"].add(val)
                elif prefix == "account":
                    ent["accounts"].add(val)
                elif prefix == "device":
                    ent["devices"].add(val)

            self.entities[root] = ent

    def _collect_weak_identifiers(self) -> None:
        """
        Post-process: assign cities and network providers to entities
        by looking up phone numbers in the raw data.
        """
        if self._bank_df is not None:
            for r in self._bank_df.iter_rows(named=True):
                s_phone = _norm_phone(r.get("Sender_Phone_Number"))
                s_city = _norm_city(r.get("Sender_City"))
                s_name = _norm_name(r.get("Sender_Customer_Name"))
                s_upi = r.get("Sender_UPI_ID")
                
                r_phone = _norm_phone(r.get("Receiver_Phone_Number"))
                r_city = _norm_city(r.get("Receiver_City"))
                r_name = _norm_name(r.get("Receiver_Customer_Name"))
                r_upi = r.get("Receiver_UPI_ID")

                if s_phone:
                    root = self.find_entity_for_phone(s_phone)
                    if root:
                        if s_city: self.entities[root]["cities"].add(s_city)
                        if s_name: self.entities[root]["names"].add(s_name)
                        if s_upi: self.entities[root]["upis"].add(s_upi)

                if r_phone:
                    root = self.find_entity_for_phone(r_phone)
                    if root:
                        if r_city: self.entities[root]["cities"].add(r_city)
                        if r_name: self.entities[root]["names"].add(r_name)
                        if r_upi: self.entities[root]["upis"].add(r_upi)

        if self._cdr_df is not None:
            for r in self._cdr_df.iter_rows(named=True):
                c_phone = _norm_phone(r.get("Caller_MSISDN"))
                tower_city = _norm_city(r.get("Tower_City"))
                net_provider = _norm_network(r.get("Network_Provider"))
                c_name = r.get("Caller_Name")

                r_phone = _norm_phone(r.get("Receiver_MSISDN"))
                r_name = r.get("Receiver_Name")

                if c_phone:
                    root = self.find_entity_for_phone(c_phone)
                    if root:
                        if tower_city: self.entities[root]["cities"].add(tower_city)
                        if net_provider: self.entities[root]["network_providers"].add(net_provider)
                        if c_name: self.entities[root]["names"].add(str(c_name).strip().lower())
                
                if r_phone:
                    root = self.find_entity_for_phone(r_phone)
                    if root:
                        if r_name: self.entities[root]["names"].add(str(r_name).strip().lower())

        if self._ipdr_df is not None:
            for r in self._ipdr_df.iter_rows(named=True):
                phone = _norm_phone(r.get("User_MSISDN"))
                ip_city = _norm_city(r.get("IP_Location_City"))
                priv_ip = _norm_ip(r.get("Private_IP_Address"))
                name = r.get("User_Name")

                if phone:
                    root = self.find_entity_for_phone(phone)
                    if root:
                        if ip_city: self.entities[root]["cities"].add(ip_city)
                        if priv_ip: self.entities[root]["ips"].add(priv_ip)
                        if name: self.entities[root]["names"].add(str(name).strip().lower())

    def _share_weak_identifier(self, root_a: str, root_b: str) -> bool:
        """
        Safety check for Tier-2 fuzzy merge.
        Only merge if entities share a city OR a network provider.
        (If they shared Phone/IMEI, Tier-1 would have already merged them.)
        """
        ent_a = self.entities.get(root_a, {})
        ent_b = self.entities.get(root_b, {})

        cities_a = ent_a.get("cities", set())
        cities_b = ent_b.get("cities", set())
        if cities_a and cities_b and (cities_a & cities_b):
            return True

        nets_a = ent_a.get("network_providers", set())
        nets_b = ent_b.get("network_providers", set())
        if nets_a and nets_b and (nets_a & nets_b):
            return True

        return False

    def _apply_fuzzy_merging(self) -> None:
        """
        Tier 2: Fuzzy name merge using rapidfuzz token_sort_ratio.
        Only merges entities with names >= threshold similar AND a shared weak identifier.
        """
        # Build name -> current_root mapping
        name_to_root: Dict[str, str] = {}
        for root, ent in self.entities.items():
            for name in ent.get("names", set()):
                name_to_root[name] = root

        if len(name_to_root) < 2:
            return

        names = list(name_to_root.keys())
        merged = 0

        for name in names:
            # Resolve to current root (may have been merged already)
            root_a = self.uf.find(name_to_root[name])

            # Build candidate list: other names whose current root is different
            candidates = [
                other for other in names
                if other != name and self.uf.find(name_to_root[other]) != root_a
            ]
            if not candidates:
                continue

            # Find best fuzzy matches
            matches = process.extract(
                name, candidates,
                scorer=fuzz.token_sort_ratio,
                limit=3,
            )
            for match_name, score, _ in matches:
                if score < self.fuzzy_threshold:
                    continue

                root_b = self.uf.find(name_to_root[match_name])
                if root_b == root_a:
                    continue

                # Safety constraint: shared weak identifier (city or network provider)
                if self._share_weak_identifier(root_a, root_b):
                    self.uf.union(root_a, root_b)
                    merged += 1
                    break  # Only merge best valid match per name

        print(f"[ER] Tier-2 fuzzy merge: {merged} entity merges applied "
              f"(threshold={self.fuzzy_threshold}, token_sort_ratio).")

    def build_entities(self) -> Dict[str, Dict[str, Set[str]]]:
        """
        Build canonical entities.
        Step 1: Tier-1 exact match.
        Step 2: Collect weak identifiers from raw data.
        Step 3: Tier-2 fuzzy name merge with safety check.
        Step 4: Rebuild after fuzzy merges.
        Step 5: Re-collect weak identifiers for merged entities.
        """
        # Step 1: Tier 1
        groups = self.uf.groups()
        self._build_from_groups(groups)

        # Step 2: Collect weak identifiers
        self._collect_weak_identifiers()

        # Step 3: Tier 2 fuzzy merge
        self._apply_fuzzy_merging()

        # Step 4: Rebuild after merges
        groups = self.uf.groups()
        self._build_from_groups(groups)

        # Step 5: Re-collect weak identifiers for merged entities
        self._collect_weak_identifiers()

        return self.entities

    def save_entities(self, path: str | Path) -> None:
        """Serialize to JSON (sets -> lists)."""
        out = {
            eid: {k: list(v) for k, v in ent.items()}
            for eid, ent in self.entities.items()
        }
        Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")

    def load_entities(self, path: str | Path) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.entities = {
            eid: {k: set(v) for k, v in ent.items()}
            for eid, ent in raw.items()
        }

    # ── Lookup helpers ───────────────────────────────────────────────────────

    def find_entity_for_phone(self, phone: str) -> str | None:
        phone = _norm_phone(phone)
        if not phone:
            return None
        key = self._key("phone", phone)
        if key not in self.uf.parent:
            return None
        return self.uf.find(key)

    def find_entity_for_imei(self, imei: str) -> str | None:
        imei = _norm_imei(imei)
        if not imei:
            return None
        key = self._key("imei", imei)
        if key not in self.uf.parent:
            return None
        return self.uf.find(key)


# ── High-level runner ────────────────────────────────────────────────────────

def resolve_all(
    bank_path: str | Path,
    cdr_path: str | Path,
    ipdr_path: str | Path,
    out_json: str | Path | None = None,
    fuzzy_threshold: int = 85,
) -> EntityResolver:
    """
    One-shot resolver. Loads CSVs, runs ingestion, builds entities.
    """
    bank = pl.read_csv(bank_path, try_parse_dates=True, infer_schema_length=1000000)
    cdr = pl.read_csv(cdr_path, try_parse_dates=True, infer_schema_length=1000000)
    ipdr = pl.read_csv(ipdr_path, try_parse_dates=True, infer_schema_length=1000000)

    resolver = EntityResolver(fuzzy_threshold=fuzzy_threshold)
    print(f"[ER] Ingesting Bank ({bank.height} rows)…")
    resolver.ingest_bank(bank)
    print(f"[ER] Ingesting CDR ({cdr.height} rows)…")
    resolver.ingest_cdr(cdr)
    print(f"[ER] Ingesting IPDR ({ipdr.height} rows)…")
    resolver.ingest_ipdr(ipdr)

    print("[ER] Building canonical entities (Tier-1 exact + Tier-2 fuzzy)…")
    resolver.build_entities()
    print(f"[ER] Resolved {len(resolver.entities)} canonical entities.")

    if out_json:
        resolver.save_entities(out_json)
        print(f"[ER] Saved to {out_json}")

    return resolver


if __name__ == "__main__":
    # Example usage relative to project root
    ROOT = Path(__file__).parent.parent
    resolver = resolve_all(
        bank_path=ROOT / "data" / "final" / "bank_transactions.csv",
        cdr_path=ROOT / "data" / "final" / "cdr_final.csv",
        ipdr_path=ROOT / "data" / "final" / "ipdr_final.csv",
        out_json=ROOT / "data" / "final" / "entities.json",
        fuzzy_threshold=85,
    )