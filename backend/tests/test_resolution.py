from app.resolution.upi_bridge import extract_upi_id, link_account_to_phone


def test_extract_upi_id():
    assert extract_upi_id("9876543210@okhdfc") == "9876543210"
    assert extract_upi_id("no-phone-here@bank") is None


def test_link_account_to_phone():
    link = link_account_to_phone("acc_001", "9876543210@okhdfc")
    assert link["phone_number"] == "9876543210"
