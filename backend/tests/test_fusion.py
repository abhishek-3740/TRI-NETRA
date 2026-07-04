from app.fusion.temporal_rules import apply_rules


def test_grooming_call_rule_fires_within_window():
    events = [
        {"id": "call_1", "type": "call", "timestamp": 1000},
        {"id": "transfer_1", "type": "transfer", "timestamp": 1000 + 60},
    ]
    flags = apply_rules(events)
    assert any(f["rule"] == "grooming_call" for f in flags)


def test_grooming_call_rule_does_not_fire_outside_window():
    events = [
        {"id": "call_1", "type": "call", "timestamp": 1000},
        {"id": "transfer_1", "type": "transfer", "timestamp": 1000 + 3600},
    ]
    flags = apply_rules(events)
    assert not any(f["rule"] == "grooming_call" for f in flags)
