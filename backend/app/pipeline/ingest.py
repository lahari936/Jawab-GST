import mimetypes

import pymupdf

from app.llm.client import transcribe

PROMPT = "Transcribe this notice verbatim. Keep every number, date and reference exactly as printed."
MIN_TEXT = 50  # below this a PDF is treated as a scan


def ingest(data: bytes, filename: str, case_id: str) -> str:
    mime = mimetypes.guess_type(filename)[0] or ""
    if mime == "application/pdf":
        doc = pymupdf.open(stream=data, filetype="pdf")
        text = "\n".join(p.get_text() for p in doc)
        if len(text.strip()) >= MIN_TEXT:
            return text
        images, mime = [p.get_pixmap(dpi=200).tobytes("png") for p in doc], "image/png"
    elif mime.startswith("image/"):
        images = [data]
    else:
        raise ValueError(f"Unsupported notice file: {filename}")
    return "\n\n".join(transcribe(img, mime, PROMPT, case_id) for img in images)
