"""Render samples/jawab/case_*/notice.txt to notice.pdf (cases A, B) and a tilted photo-like notice.png (case C).

Run from repo root: python scripts/make_samples.py
"""
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent / "samples" / "jawab"


def render(case: str) -> pymupdf.Document:
    doc = pymupdf.open()
    page = doc.new_page()  # A4-ish default
    page.insert_textbox(pymupdf.Rect(40, 40, 560, 800), (ROOT / case / "notice.txt").read_text(),
                        fontname="cour", fontsize=8.5)
    return doc


for case in ("case_a", "case_b"):
    render(case).save(ROOT / case / "notice.pdf")

# Case C: rasterise with a slight tilt, like a phone photo.
pix = render("case_c")[0].get_pixmap(matrix=pymupdf.Matrix(3, 3).prerotate(2), colorspace=pymupdf.csGRAY)
pix.save(ROOT / "case_c" / "notice.png")
print("ok")
