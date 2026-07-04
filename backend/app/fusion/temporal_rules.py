"""
Temporal fusion rules applied over the unified event timeline
(calls + IP sessions + bank transfers, all in IST epoch seconds).
"""
from typing import List, Dict

GROOMING_CALL_WINDOW_SEC = 30 * 60
RAPID_LAYERING_WINDOW_SEC = 10 * 60


def get_unified_timeline(case_id: str) -> List[Dict]:
    """
    TODO: replace with a real Postgres query joining CDR, IPDR, and bank
    events for the given case_id, ordered by timestamp.
    """
    return []  # placeholder — wire up to db_models.py


def apply_rules(events: List[Dict]) -> List[Dict]:
    flags = []
    flags.extend(_detect_grooming_calls(events))
    flags.extend(_detect_digital_alibi(events))
    flags.extend(_detect_rapid_layering(events))
    return flags


def _detect_grooming_calls(events: List[Dict]) -> List[Dict]:
    calls = [e for e in events if e.get("type") == "call"]
    transfers = [e for e in events if e.get("type") == "transfer"]
    flags = []
    for call in calls:
        for transfer in transfers:
            delta = transfer["timestamp"] - call["timestamp"]
            if 0 <= delta <= GROOMING_CALL_WINDOW_SEC:
                flags.append({
                    "rule": "grooming_call",
                    "call_event": call["id"],
                    "transfer_event": transfer["id"],
                    "delta_seconds": delta,
                    "risk_weight": 0.9,
                })
    return flags


def _detect_digital_alibi(events: List[Dict]) -> List[Dict]:
    ip_sessions = [e for e in events if e.get("type") == "ip_session"]
    logins = [e for e in events if e.get("type") == "bank_login"]
    flags = []
    for login in logins:
        for session in ip_sessions:
            if session["session_start"] <= login["timestamp"] <= session["session_end"]:
                flags.append({
                    "rule": "digital_alibi",
                    "login_event": login["id"],
                    "session_event": session["id"],
                    "risk_weight": 0.85,
                })
    return flags


def _detect_rapid_layering(events: List[Dict]) -> List[Dict]:
    transfers = sorted([e for e in events if e.get("type") == "transfer"], key=lambda e: e["timestamp"])
    flags = []
    for i in range(len(transfers) - 1):
        a, b = transfers[i], transfers[i + 1]
        if a.get("to_account") == b.get("from_account"):
            delta = b["timestamp"] - a["timestamp"]
            if 0 <= delta <= RAPID_LAYERING_WINDOW_SEC:
                flags.append({
                    "rule": "rapid_layering",
                    "from_transfer": a["id"],
                    "to_transfer": b["id"],
                    "delta_seconds": delta,
                    "risk_weight": 0.9,
                })
    return flags
