"""
Tier 2 OCR fallback using PaddleOCR PP-Structure for scanned bank statements.
Requires `paddleocr` + `paddlepaddle` (uncomment in requirements.txt) — kept
optional since it's a heavy CPU install and not needed for digital PDFs.
"""
from typing import List


def extract_tables_via_ocr(file_bytes: bytes) -> List[List[List[str]]]:
    """
    Converts PDF pages to images, runs PP-Structure table detection,
    and returns tables in the same [[row], [row], ...] shape pdfplumber uses.
    """
    from paddleocr import PPStructure  # noqa: local import, heavy dependency
    import fitz  # PyMuPDF, for PDF -> image rendering
    import numpy as np
    from PIL import Image

    engine = PPStructure(table=True, ocr=True, show_log=False)
    tables = []

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        result = engine(np.array(img))
        for region in result:
            if region["type"] == "table" and "res" in region:
                html = region["res"].get("html", "")
                tables.append(_html_table_to_rows(html))

    return tables


def _html_table_to_rows(html: str) -> List[List[str]]:
    from bs4 import BeautifulSoup  # add beautifulsoup4 to requirements if enabling OCR
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        rows.append(cells)
    return rows
