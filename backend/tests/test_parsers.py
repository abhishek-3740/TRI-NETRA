from app.parsers.cdr_parser import CDRParser
from app.parsers.ipdr_parser import IPDRParser


def test_cdr_parser_normalizes_columns():
    csv_bytes = b"Caller,Callee,Call Time,Cell ID,Latitude,Longitude\n9876543210,9123456780,2026-01-01T10:00:00,TWR001,21.17,72.83\n"
    result = CDRParser().parse(csv_bytes)
    assert result["row_count"] == 1
    assert "calling_party" in result["records"][0]


def test_ipdr_parser_normalizes_columns():
    csv_bytes = b"public_ip,nat_port,private_ip,session_start,session_end\n10.0.0.1,4001,192.168.1.5,2026-01-01T10:00:00,2026-01-01T10:10:00\n"
    result = IPDRParser().parse(csv_bytes)
    assert result["row_count"] == 1
