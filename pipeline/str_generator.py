"""
pipeline/str_generator.py
Automated Suspicious Transaction Report (STR) Generator for TRI-NETRA (ERH26_PS_03).

Generates a FIU-IND-style Markdown STR for a flagged canonical entity,
enriched with findings from all upstream intelligence pipelines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl


# ── Config ───────────────────────────────────────────────────────────────────

REPORTS_DIR = Path("data/reports")
DEFAULT_ENTITY_ID: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_set(items: set | list) -> str:
    if not items:
        return "*Not found in dataset*"
    return ", ".join(sorted(str(x) for x in items))


def _fmt_table(headers: List[str], rows: List[List[str]]) -> str:
    """Generate a Markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# ── Report Builder ───────────────────────────────────────────────────────────

class STRBuilder:
    def __init__(
        self,
        entity_id: str,
        entity: Dict[str, Any],
        fusion_events: Optional[List[Dict]] = None,
        mule_accounts: Optional[List[Dict]] = None,
        device_farms: Optional[List[Dict]] = None,
        travel_anomalies: Optional[List[Dict]] = None,
        hideouts: Optional[List[Dict]] = None,
    ):
        self.entity_id = entity_id
        self.entity = entity
        self.fusion_events = fusion_events or []
        self.mule_accounts = mule_accounts or []
        self.device_farms = device_farms or []
        self.travel_anomalies = travel_anomalies or []
        self.hideouts = hideouts or []

        self.report_id = f"STR-{datetime.now().strftime('%Y%m%d')}-{entity_id[:16]}"
        self.generated_at = datetime.now().isoformat()

    # ── Content assembly ─────────────────────────────────────────────────

    def build(self) -> str:
        sections = [
            self._header(),
            self._part_a_subject(),
            self._part_b_activity_summary(),
            self._part_c_footprint(),
            self._part_d_evidentiary_timeline(),
            self._part_e_recommendations(),
            self._footer(),
        ]
        return "\n\n".join(sections)

    def _header(self) -> str:
        return "\n".join([
            "# FIU-IND SUSPICIOUS TRANSACTION REPORT (STR)",
            "",
            f"> **Report ID:** `{self.report_id}`",
            f"> **Generated:** {self.generated_at}",
            f"> **Classification:** RESTRICTED — Law Enforcement Sensitive",
            f"> **System:** TRI-NETRA Forensic Fusion Engine (ERH26_PS_03)",
            "",
            "---",
        ])

    def _part_a_subject(self) -> str:
        ent = self.entity
        rows = [
            ["Canonical Entity ID", f"`{self.entity_id}`"],
            ["Known Names", _fmt_set(ent.get("names", set()))],
            ["Phone Numbers", _fmt_set(ent.get("phones", set()))],
            ["Bank Accounts", _fmt_set(ent.get("accounts", set()))],
            ["UPI IDs", _fmt_set(ent.get("upis", set()))],
            ["IMEIs", _fmt_set(ent.get("imeis", set()))],
            ["IP Addresses", _fmt_set(ent.get("ips", set()))],
            ["Devices", _fmt_set(ent.get("devices", set()))],
        ]
        return "\n".join([
            "## Part A — Subject Profile",
            "",
            _fmt_table(["Field", "Value"], rows),
            "",
        ])

    def _part_b_activity_summary(self) -> str:
        reasons: List[str] = []
        total_risk = 0

        # Fusion events
        if self.fusion_events:
            inj = [e for e in self.fusion_events if e.get("is_injected")]
            total_risk += sum(e.get("risk_score", 0) for e in self.fusion_events)
            reasons.append(
                f"**Temporal Fusion:** {len(self.fusion_events)} coincidences detected "
                f"({len(inj)} injected/ground-truth sequences)."
            )

        # Mule accounts
        if self.mule_accounts:
            total_risk += sum(m.get("risk_score", 0) for m in self.mule_accounts)
            reasons.append(
                f"**Mule Network:** {len(self.mule_accounts)} linked account(s) flagged "
                f"as high-throughput pass-through nodes."
            )

        # Device farms
        if self.device_farms:
            total_risk += sum(d.get("risk_score", 0) for d in self.device_farms)
            reasons.append(
                f"**Device Farm:** {len(self.device_farms)} IMEI(s) shared by multiple "
                f"SIM cards (SIM-swapping / handset-sharing)."
            )

        # Impossible travel
        if self.travel_anomalies:
            total_risk += len(self.travel_anomalies) * 100
            reasons.append(
                f"**Impossible Travel:** {len(self.travel_anomalies)} geo-velocity anomaly(ies) "
                f"indicating physical presence in two distant cities within an implausible time window."
            )

        # Hideouts
        if self.hideouts:
            total_risk += len(self.hideouts) * 75
            reasons.append(
                f"**Spatial Co-location:** Detected in {len(self.hideouts)} criminal hideout cluster(s) "
                f"where multiple distinct entities converged at the same tower/location."
            )

        if not reasons:
            reasons.append("*No automated flags triggered for this entity. Report generated for manual review.*")

        risk_tier = "CRITICAL" if total_risk >= 300 else "HIGH" if total_risk >= 150 else "MEDIUM" if total_risk >= 50 else "LOW"

        return "\n".join([
            "## Part B — Suspicious Activity Summary",
            "",
            f"**Composite Risk Score:** `{total_risk:.0f}`  ",
            f"**Risk Tier:** `{risk_tier}`",
            "",
            "### Flagged Indicators",
            "",
            "\n".join(f"- {r}" for r in reasons),
            "",
        ])

    def _part_c_footprint(self) -> str:
        lines = ["## Part C — Financial / Telecom Footprint", ""]

        # Accounts table
        if self.mule_accounts:
            acc_rows = [
                [
                    m["account"],
                    m["bank_name"],
                    f"₹{m['money_in']:,.2f}",
                    f"₹{m['money_out']:,.2f}",
                    str(m["in_degree"]),
                    str(m["out_degree"]),
                    f"{m['risk_score']:.1f}",
                ]
                for m in self.mule_accounts
            ]
            lines.append("### Linked Bank Accounts (Mule Analysis)")
            lines.append("")
            lines.append(_fmt_table(
                ["Account", "Bank", "Money In", "Money Out", "In-Deg", "Out-Deg", "Risk"],
                acc_rows
            ))
            lines.append("")

        # IMEI table
        if self.device_farms:
            imei_rows = [
                [
                    d["imei"],
                    str(d["sim_count"]),
                    ", ".join(d["msisdns"][:5]) + ("..." if len(d["msisdns"]) > 5 else ""),
                    d["risk_tier"].upper(),
                    f"{d['risk_score']:.1f}",
                ]
                for d in self.device_farms
            ]
            lines.append("### Linked IMEIs (Device Farm Analysis)")
            lines.append("")
            lines.append(_fmt_table(
                ["IMEI", "SIM Count", "MSISDNs (sample)", "Tier", "Risk"],
                imei_rows
            ))
            lines.append("")

        # IPs
        ips = self.entity.get("ips", set())
        if ips:
            lines.append("### Associated IP Addresses")
            lines.append("")
            lines.append("\n".join(f"- `{ip}`" for ip in sorted(ips)))
            lines.append("")

        return "\n".join(lines)

    def _part_d_evidentiary_timeline(self) -> str:
        if not self.fusion_events:
            return ""

        lines = ["## Part D — Evidentiary Timeline (Fusion Events)", ""]
        for i, ev in enumerate(self.fusion_events[:10], start=1):
            lines.append(
                f"**{i}. Window:** `{ev['window_start']}` → `{ev['window_end']}`  \n"
                f"- Risk Score: `{ev['risk_score']}` | "
                f"Bank: {ev['bank_count']} | CDR: {ev['cdr_count']} | IPDR: {ev['ipdr_count']}"
            )
            if ev.get("is_injected"):
                lines.append("  - ⚠️ **GROUND-TRUTH INJECTED SEQUENCE**")
            lines.append("")
        return "\n".join(lines)

    def _part_e_recommendations(self) -> str:
        return "\n".join([
            "## Part E — Investigator Recommendations",
            "",
            "1. **Freeze / Monitor** all listed bank accounts and UPI IDs immediately.",
            "2. **Requisition expanded CDR/IPDR** for the 30 days preceding the flagged fusion windows.",
            "3. **Trace beneficiary accounts** downstream of the mule pass-through nodes.",
            "4. **Geo-fence alerts** on the criminal hideout coordinates identified in Part C.",
            "5. **Device seizure warrant** for IMEIs flagged under device-farm analysis.",
            "",
        ])

    def _footer(self) -> str:
        hash_src = f"{self.report_id}{self.generated_at}{self.entity_id}"
        digest = hashlib.sha256(hash_src.encode()).hexdigest()[:16]
        return "\n".join([
            "---",
            "",
            f"**Report Integrity Hash:** `{digest}`",
            f"**Generated by:** TRI-NETRA v1.0 | ERH26_PS_03 | E-RAKSHAK 2026",
            f"**Disclaimer:** This is an automated intelligence product. All findings must be validated by a supervising officer before legal action.",
            "",
        ])


# ── Data Loader ──────────────────────────────────────────────────────────────

def _gather_entity_findings(entity_id: str, root: Path) -> Dict[str, Any]:
    """
    Cross-reference the entity against all pipeline outputs to collect
    real anomalies instead of hardcoded placeholders.
    """
    findings: Dict[str, Any] = {
        "fusion_events": [],
        "mule_accounts": [],
        "device_farms": [],
        "travel_anomalies": [],
        "hideouts": [],
    }

    # Helper: check if any identifier of the entity matches a finding
    ent = _load_json(root / "data" / "final" / "entities.json")
    if not ent or entity_id not in ent:
        return findings
    profile = ent[entity_id]

    phones = set(str(p) for p in profile.get("phones", []))
    accounts = set(str(a) for a in profile.get("accounts", []))
    imeis = set(str(i) for i in profile.get("imeis", []))

    # ── Fusion Events ──────────────────────────────────────────────────
    fusion = _load_json(root / "data" / "final" / "fusion_events.json")
    if fusion:
        for ev in fusion:
            if ev.get("entity_id") == entity_id:
                findings["fusion_events"].append(ev)

    # ── Mule Accounts ─────────────────────────────────────────────────
    mules = _load_json(root / "data" / "final" / "mule_accounts.json")
    if mules:
        for m in mules.get("mule_accounts", []):
            if m["account"] in accounts:
                findings["mule_accounts"].append(m)

    # ── Device Farms ──────────────────────────────────────────────────
    farms = _load_json(root / "data" / "final" / "device_farms.json")
    if farms:
        for d in farms.get("top_50_device_farms", []):
            if d["imei"] in imeis:
                findings["device_farms"].append(d)

    # ── Impossible Travel ─────────────────────────────────────────────
    travel = _load_json(root / "data" / "final" / "impossible_travel.json")
    if travel:
        for a in travel.get("anomalies", []):
            if a.get("entity_id") == entity_id:
                findings["travel_anomalies"].append(a)

    # ── Criminal Hideouts ─────────────────────────────────────────────
    hideouts = _load_json(root / "data" / "final" / "criminal_hideouts.json")
    if hideouts:
        for h in hideouts.get("criminal_hideouts", []):
            if entity_id in h.get("entity_ids", []):
                findings["hideouts"].append(h)

    return findings


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an FIU-IND STR for a canonical entity."
    )
    parser.add_argument(
        "--entity_id",
        type=str,
        default=None,
        help="Canonical entity_id from entities.json. Defaults to first entity.",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Project root directory (default: current working dir).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    entities_path = root / "data" / "final" / "entities.json"

    if not entities_path.exists():
        print(f"[STR] ERROR: entities.json not found at {entities_path}")
        return

    with open(entities_path, "r", encoding="utf-8") as f:
        entities = json.load(f)

    # Pick entity
    if args.entity_id:
        entity_id = args.entity_id
    else:
        entity_id = next(iter(entities.keys()))
        print(f"[STR] No --entity_id provided. Defaulting to first entity: {entity_id}")

    if entity_id not in entities:
        print(f"[STR] ERROR: Entity '{entity_id}' not found in entities.json")
        return

    entity = entities[entity_id]
    print(f"[STR] Building STR for entity: {entity_id}")

    # Gather real findings
    findings = _gather_entity_findings(entity_id, root)

    # Build report
    builder = STRBuilder(
        entity_id=entity_id,
        entity=entity,
        fusion_events=findings["fusion_events"],
        mule_accounts=findings["mule_accounts"],
        device_farms=findings["device_farms"],
        travel_anomalies=findings["travel_anomalies"],
        hideouts=findings["hideouts"],
    )
    md = builder.build()

    # Save
    out_dir = root / "data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"STR_{entity_id}.md"
    out_path.write_text(md, encoding="utf-8")

    print(f"[STR] Report saved to: {out_path}")


if __name__ == "__main__":
    main()
