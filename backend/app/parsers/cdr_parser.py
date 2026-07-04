"""CDR (Call Detail Record) parser — Polars-based, handles large CSVs efficiently."""
import io
from typing import Dict
import polars as pl


class CDRParser:
    EXPECTED_COLUMNS = ["calling_party", "called_party", "timestamp", "cell_id", "lat", "lon"]

    def parse(self, file_bytes: bytes) -> Dict:
        df = pl.read_csv(io.BytesIO(file_bytes), infer_schema_length=1000)
        df = self._normalize_columns(df)
        return {
            "row_count": df.height,
            "records": df.to_dicts(),
        }

    def _normalize_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        rename_map = {}
        for col in df.columns:
            key = col.strip().lower().replace(" ", "_")
            if key in ("caller", "a_party", "calling_number"):
                rename_map[col] = "calling_party"
            elif key in ("callee", "b_party", "called_number"):
                rename_map[col] = "called_party"
            elif key in ("date_time", "call_time", "time"):
                rename_map[col] = "timestamp"
            elif key in ("cellid", "tower_id", "cell_id"):
                rename_map[col] = "cell_id"
            elif key in ("latitude",):
                rename_map[col] = "lat"
            elif key in ("longitude",):
                rename_map[col] = "lon"
        return df.rename(rename_map)
