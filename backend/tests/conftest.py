import pytest


@pytest.fixture
def sample_bank_rows():
    return [
        {"date": "01/01/2026", "narration": "UPI/9876543210@okhdfc/payment", "amount_debit": "5000"},
    ]
