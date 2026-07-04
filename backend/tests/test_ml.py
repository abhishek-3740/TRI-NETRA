from app.ml.risk_aggregator import get_risk_breakdown


def test_risk_breakdown_shape():
    result = get_risk_breakdown("acc_001")
    assert "final_risk_score" in result
    assert 0.0 <= result["final_risk_score"] <= 1.0
    assert isinstance(result["is_mule_account"], bool)
