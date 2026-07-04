"""
UPI Bridge: links Bank Account <-> Phone Number by extracting the 10-digit
mobile number embedded in a UPI VPA (Virtual Payment Address), e.g.
'9876543210@okhdfc' -> '9876543210'.
"""
import re

PHONE_IN_UPI_REGEX = re.compile(r"(\d{10})")


def extract_upi_id(vpa: str) -> str | None:
    """Extract the 10-digit phone number from a UPI VPA, if present."""
    match = PHONE_IN_UPI_REGEX.search(vpa)
    return match.group(1) if match else None


def link_account_to_phone(account_id: str, vpa: str) -> dict | None:
    phone = extract_upi_id(vpa)
    if not phone:
        return None
    return {"account_id": account_id, "phone_number": phone, "linked_via": "upi_vpa", "source_vpa": vpa}
