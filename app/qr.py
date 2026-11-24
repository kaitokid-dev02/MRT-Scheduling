"""QR code rendering helpers for printable tickets."""
from __future__ import annotations

import base64

import segno


def qr_data_uri(value: str) -> str:
    """Return a self-contained SVG data URI containing a QR code for ``value``."""
    code = segno.make(value, error="m")
    svg = code.svg_inline(scale=5, border=4, dark="#111111", light="#ffffff")
    payload = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"
