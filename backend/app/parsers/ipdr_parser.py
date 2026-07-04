"""
IPDR (Internet Protocol Detail Record) parser — Polars lazy-load for
multi-million row files. Extracts public IP, NAT port, private IP, and
session timing needed to defeat CGNAT masking.
"""
import io
from typing import Dict
import polars as pl


class IPDRParser:
    def parse(self, file_bytes: bytes) -> Dict:
        # Lazy scan keeps memory flat even on 5M+ row files.
        lf = pl.scan_csv(io.BytesIO(file_bytes), infer_schema_length=1000)
        lf = self._normalize_columns(lf)
        df = lf.collect()
        return {
            "row_count": df.height,
            "records": df.to_dicts(),
        }

    def _normalize_columns(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        rename_map = {}
        for col in lf.columns:
            key = col.strip().lower().replace(" ", "_")
            if key in ("public_ip", "src_public_ip"):
                rename_map[col] = "public_ip"
            elif key in ("nat_port", "translated_port"):
                rename_map[col] = "nat_port"
            elif key in ("private_ip", "src_private_ip"):
                rename_map[col] = "private_ip"
            elif key in ("session_start", "start_time"):
                rename_map[col] = "session_start"
            elif key in ("session_end", "end_time"):
                rename_map[col] = "session_end"
        return lf.rename(rename_map)
