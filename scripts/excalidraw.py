"""Pure-Python library for authoring .excalidraw scene files.

An .excalidraw file is a single JSON document with this top-level shape:

    {
      "type": "excalidraw",
      "version": 2,
      "source": "...",
      "elements": [ ...scene elements... ],
      "appState": { "viewBackgroundColor": "#ffffff", "gridSize": null },
      "files": { "<fileId>": { "mimeType", "id", "dataURL", "created", "lastRetrieved" } }
    }

Elements are typed: image, rectangle, ellipse, diamond, text, arrow, line.
Each has required fields (id, seed, version, versionNonce, etc.) that this
module fills in automatically so the caller only cares about geometry and
styling.

The library has no third-party dependencies — PNG and JPEG dimensions are
read by parsing the file headers with the standard library. This keeps the
skill portable across any Python 3.8+ environment.

Usage is documented in the project SKILL.md. Quick example:

    from excalidraw import Scene, load_image

    scene = Scene()
    file_id, w, h = scene.add_image_file("screenshot.png")
    scene.image(100, 100, w // 4, h // 4, file_id)
    scene.ellipse(180, 160, 60, 40, stroke_color="#e03131", stroke_width=4)
    scene.text(260, 170, "Click target", color="#e03131")
    scene.save("output.excalidraw")
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Image header parsing (no Pillow dependency)
# ---------------------------------------------------------------------------


def _png_dimensions(data: bytes) -> Tuple[int, int]:
    # PNG: 8-byte signature + IHDR chunk. Width/height are the first 8 bytes of IHDR.
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file")
    # IHDR starts at offset 8: 4 length + 4 "IHDR" + 4 width + 4 height
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _jpeg_dimensions(data: bytes) -> Tuple[int, int]:
    # JPEG: scan for SOF marker (0xFFC0..0xFFCF, excluding a few).
    if data[:2] != b"\xff\xd8":
        raise ValueError("Not a JPEG file")
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            raise ValueError("Invalid JPEG marker")
        # Skip padding FFs
        while data[i] == 0xFF:
            i += 1
        marker = data[i]
        i += 1
        # SOF markers: C0-C3, C5-C7, C9-CB, CD-CF
        if marker in (
            0xC0, 0xC1, 0xC2, 0xC3,
            0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB,
            0xCD, 0xCE, 0xCF,
        ):
            # Skip segment length (2 bytes) + precision (1 byte)
            height, width = struct.unpack(">HH", data[i + 3 : i + 7])
            return width, height
        # Other markers: read segment length and skip
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        i += seg_len
    raise ValueError("Could not find SOF marker in JPEG")


def _gif_dimensions(data: bytes) -> Tuple[int, int]:
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        raise ValueError("Not a GIF file")
    width, height = struct.unpack("<HH", data[6:10])
    return width, height


def _webp_dimensions(data: bytes) -> Tuple[int, int]:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("Not a WebP file")
    chunk = data[12:16]
    if chunk == b"VP8 ":
        width, height = struct.unpack("<HH", data[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L":
        b = data[21:25]
        width = 1 + (((b[1] & 0x3F) << 8) | b[0])
        height = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        return width, height
    if chunk == b"VP8X":
        width = 1 + struct.unpack("<I", data[24:27] + b"\x00")[0]
        height = 1 + struct.unpack("<I", data[27:30] + b"\x00")[0]
        return width, height
    raise ValueError("Unsupported WebP variant")


def image_dimensions(path: str) -> Tuple[int, int, str]:
    """Return (width, height, mime_type) for an image file.

    Supports PNG, JPEG, GIF, WebP via stdlib header parsing — no Pillow.
    """
    with open(path, "rb") as f:
        header = f.read(64)
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = _png_dimensions(header)
        return w, h, "image/png"
    if header[:2] == b"\xff\xd8":
        with open(path, "rb") as f:
            data = f.read()
        w, h = _jpeg_dimensions(data)
        return w, h, "image/jpeg"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        w, h = _gif_dimensions(header)
        return w, h, "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        w, h = _webp_dimensions(header)
        return w, h, "image/webp"
    raise ValueError(f"Unsupported image format: {path}")


# ---------------------------------------------------------------------------
# Scene model
# ---------------------------------------------------------------------------


_FONT_FAMILY = {
    "virgil": 1,      # default hand-drawn
    "helvetica": 2,   # sans
    "cascadia": 3,    # mono
}


def _rand_nonce() -> int:
    # Not cryptographic — Excalidraw just wants a stable-ish nonzero int.
    return int.from_bytes(os.urandom(4), "big") | 1


def _common(**overrides: Any) -> Dict[str, Any]:
    """Fields every element needs. Overrides win."""
    base = {
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,  # 0 = smooth (no hand-drawn wobble)
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": _rand_nonce(),
        "versionNonce": _rand_nonce(),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }
    base.update(overrides)
    return base


@dataclass
class Scene:
    """Mutable collection of elements and embedded files.

    Elements are added in draw order; later elements render on top of earlier
    ones. Use `save(path)` to write the file, or `to_dict()` to inspect.
    """

    elements: List[Dict[str, Any]] = field(default_factory=list)
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    background: str = "#ffffff"
    _id_counter: int = 0

    # ---- ID helper ----
    def _next_id(self, prefix: str = "el") -> str:
        self._id_counter += 1
        return f"{prefix}-{self._id_counter}"

    # ---- File embedding ----
    def add_image_file(self, path: str) -> Tuple[str, int, int]:
        """Embed an image file and return (file_id, width, height).

        The file_id is a content-hash-based string so re-embedding the same
        image produces the same id (de-dupes within a scene).
        """
        with open(path, "rb") as f:
            data = f.read()
        w, h, mime = image_dimensions(path)
        file_id = "img-" + hashlib.sha1(data).hexdigest()[:16]
        data_url = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
        now = int(time.time() * 1000)
        self.files[file_id] = {
            "mimeType": mime,
            "id": file_id,
            "dataURL": data_url,
            "created": now,
            "lastRetrieved": now,
        }
        return file_id, w, h

    # ---- Element primitives ----
    def image(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        file_id: str,
    ) -> Dict[str, Any]:
        el = {
            "id": self._next_id("img"),
            "type": "image",
            "x": x, "y": y, "width": w, "height": h,
            **_common(),
            "status": "saved",
            "fileId": file_id,
            "scale": [1, 1],
        }
        self.elements.append(el)
        return el

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        stroke_color: str = "#1e1e1e",
        background_color: str = "transparent",
        stroke_width: float = 2,
        fill_style: str = "solid",
        rounded: bool = False,
    ) -> Dict[str, Any]:
        el = {
            "id": self._next_id("rect"),
            "type": "rectangle",
            "x": x, "y": y, "width": w, "height": h,
            **_common(
                strokeColor=stroke_color,
                backgroundColor=background_color,
                strokeWidth=stroke_width,
                fillStyle=fill_style,
                roundness={"type": 3} if rounded else None,
            ),
        }
        self.elements.append(el)
        return el

    def ellipse(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        stroke_color: str = "#e03131",
        background_color: str = "transparent",
        stroke_width: float = 4,
    ) -> Dict[str, Any]:
        el = {
            "id": self._next_id("ell"),
            "type": "ellipse",
            "x": x, "y": y, "width": w, "height": h,
            **_common(
                strokeColor=stroke_color,
                backgroundColor=background_color,
                strokeWidth=stroke_width,
            ),
        }
        self.elements.append(el)
        return el

    def diamond(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        stroke_color: str = "#1e1e1e",
        background_color: str = "transparent",
        stroke_width: float = 2,
    ) -> Dict[str, Any]:
        el = {
            "id": self._next_id("dia"),
            "type": "diamond",
            "x": x, "y": y, "width": w, "height": h,
            **_common(
                strokeColor=stroke_color,
                backgroundColor=background_color,
                strokeWidth=stroke_width,
            ),
        }
        self.elements.append(el)
        return el

    def text(
        self,
        x: float,
        y: float,
        content: str,
        *,
        font_size: int = 20,
        font: str = "helvetica",
        color: str = "#1e1e1e",
        align: str = "left",
        width: Optional[float] = None,
    ) -> Dict[str, Any]:
        lines = content.split("\n")
        # Rough heuristic for width if not supplied — Excalidraw re-measures
        # on load, so this just needs to be in the ballpark.
        approx_w = width or max(len(line) for line in lines) * font_size * 0.55
        approx_h = len(lines) * font_size * 1.25
        el = {
            "id": self._next_id("txt"),
            "type": "text",
            "x": x, "y": y,
            "width": approx_w,
            "height": approx_h,
            **_common(strokeColor=color),
            "fontSize": font_size,
            "fontFamily": _FONT_FAMILY.get(font, 2),
            "textAlign": align,
            "verticalAlign": "top",
            "baseline": font_size - 2,
            "containerId": None,
            "originalText": content,
            "text": content,
            "lineHeight": 1.25,
        }
        self.elements.append(el)
        return el

    def arrow(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke_color: str = "#1e1e1e",
        stroke_width: float = 2,
        start_arrowhead: Optional[str] = None,
        end_arrowhead: str = "arrow",
    ) -> Dict[str, Any]:
        el = {
            "id": self._next_id("arr"),
            "type": "arrow",
            "x": x1, "y": y1,
            "width": x2 - x1, "height": y2 - y1,
            **_common(strokeColor=stroke_color, strokeWidth=stroke_width),
            "points": [[0.0, 0.0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": start_arrowhead,
            "endArrowhead": end_arrowhead,
        }
        self.elements.append(el)
        return el

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke_color: str = "#1e1e1e",
        stroke_width: float = 2,
    ) -> Dict[str, Any]:
        el = {
            "id": self._next_id("lin"),
            "type": "line",
            "x": x1, "y": y1,
            "width": x2 - x1, "height": y2 - y1,
            **_common(strokeColor=stroke_color, strokeWidth=stroke_width),
            "points": [[0.0, 0.0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": None,
        }
        self.elements.append(el)
        return el

    # ---- Serialization ----
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "excalidraw-author-skill",
            "elements": self.elements,
            "appState": {
                "viewBackgroundColor": self.background,
                "gridSize": None,
            },
            "files": self.files,
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ---------------------------------------------------------------------------
# Palette — Excalidraw's standard colors
# ---------------------------------------------------------------------------


class Color:
    """Convenience constants matching Excalidraw's default palette."""

    BLACK = "#1e1e1e"
    WHITE = "#ffffff"
    RED = "#e03131"
    ORANGE = "#f08c00"
    YELLOW = "#f1c40f"
    GREEN = "#2f9e44"
    TEAL = "#099268"
    BLUE = "#1971c2"
    LIGHT_BLUE = "#4dabf7"
    INDIGO = "#6741d9"
    PURPLE = "#ae3ec9"
    PINK = "#e64980"
    GRAY = "#868e96"
    LIGHT_GRAY = "#ced4da"

    # Semi-transparent fills
    FILL_RED = "#ffc9c9"
    FILL_YELLOW = "#ffec99"
    FILL_GREEN = "#b2f2bb"
    FILL_BLUE = "#a5d8ff"


if __name__ == "__main__":
    # Smoke test — build a tiny scene and write it to stdout.
    s = Scene()
    s.text(10, 10, "Hello, Excalidraw", font_size=32, color=Color.BLUE)
    s.rect(10, 60, 200, 80, stroke_color=Color.GREEN, rounded=True)
    s.ellipse(50, 80, 120, 40, stroke_color=Color.RED)
    print(s.to_json()[:200] + "...")
