"""
CGNAT Defeat: links Phone Number <-> IP Address by matching the bank's
recorded login IP + timestamp against IPDR's Public IP + NAT Port + session
window. This is the core trick for de-anonymizing CGNAT-masked traffic
(very common on Indian mobile networks).
"""
from datetime import datetime
from typing import List, Dict, Optional


def match_login_to_session(
    bank_login_ip: str,
    bank_login_time: datetime,
    ipdr_sessions: List[Dict],
) -> Optional[Dict]:
    """
    Finds the IPDR session whose Public IP matches the bank login IP and
    whose session window contains the login timestamp.

    Each ipdr_session dict is expected to have:
      public_ip, nat_port, private_ip, session_start, session_end, phone_number
    """
    for session in ipdr_sessions:
        if session["public_ip"] != bank_login_ip:
            continue
        start = session["session_start"]
        end = session["session_end"]
        if start <= bank_login_time <= end:
            return {
                "phone_number": session.get("phone_number"),
                "private_ip": session["private_ip"],
                "nat_port": session["nat_port"],
                "matched_session_start": start,
                "matched_session_end": end,
                "confidence": "high" if (end - start).total_seconds() < 600 else "medium",
            }
    return None
