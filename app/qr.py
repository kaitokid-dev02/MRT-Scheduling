"""QR code rendering helpers for printable tickets."""
from __future__ import annotations

import base64
from io import BytesIO

import segno


def qr_data_uri(value: str) -> str:
    """Return a self-contained PNG data URI containing a QR code for ``value``."""
    code = segno.make(value, error="m")
    image = BytesIO()
    code.save(image, kind="png", scale=7, border=4, dark="#111111", light="#ffffff")
    payload = base64.b64encode(image.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"
