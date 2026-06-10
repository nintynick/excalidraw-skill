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
Each has required fields (id, seed, version, versionNonce, index, etc.) that
this module fills in automatically so the caller only cares about geometry
and styling.

The library has no third-party dependencies — PNG and JPEG dimensions are
read by parsing the file headers with the standard library. This keeps the
skill portable across any Python 3.8+ environment.

Usage is documented in the project SKILL.md. Quick example:

    from excalidraw import Scene, Color

    scene = Scene()
    file_id, w, h = scene.add_image_file("screenshot.png")
    scene.image(100, 100, w // 4, h // 4, file_id)
    scene.ellipse(180, 160, 60, 40, stroke_color="#e03131", stroke_width=4)
    scene.text(260, 170, "Click target", color="#e03131")
    a, _ = scene.node(500, 100, 180, 70, "API Gateway")
    b, _ = scene.node(800, 100, 180, 70, "Auth Service")
    scene.connect(a, b)
    for warning in scene.check_overlaps():
        print("LAYOUT WARNING:", warning)
    scene.save("output.excalidraw")
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import textwrap
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
    "assistant": 4,   # newer sans
}

# Average glyph width as a fraction of font size, per family. Rough but
# consistent with how Excalidraw measures these faces.
_CHAR_W = {1: 0.6, 2: 0.55, 3: 0.6, 4: 0.55}

_B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _frac_index(n: int) -> str:
    """n-th key of Excalidraw's fractional-index integer sequence.

    Produces 'a0'..'az', then 'b00'..'bzz', 'c000'.., which sort
    lexicographically in insertion order — the same scheme the
    fractional-indexing library uses for generateKeyBetween(prev, null).
    """
    length = 1
    prefix = 0
    capacity = 62
    while n >= capacity:
        n -= capacity
        prefix += 1
        length += 1
        capacity = 62 ** length
    digits = []
    for _ in range(length):
        digits.append(_B62[n % 62])
        n //= 62
    return chr(ord("a") + prefix) + "".join(reversed(digits))


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


def _bbox(el: Dict[str, Any]) -> Tuple[float, float, float, float]:
    x, y = el.get("x", 0), el.get("y", 0)
    w, h = el.get("width", 0), el.get("height", 0)
    if w < 0:
        x, w = x + w, -w
    if h < 0:
        y, h = y + h, -h
    return x, y, w, h


def _edge_point(box: Tuple[float, float, float, float],
                tx: float, ty: float) -> Tuple[float, float]:
    """Point where the segment from the box's center toward (tx, ty) exits the box."""
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    # Scale factor to reach the boundary along each axis
    candidates = []
    if dx != 0:
        candidates.append((w / 2) / abs(dx))
    if dy != 0:
        candidates.append((h / 2) / abs(dy))
    t = min(candidates)
    return cx + dx * t, cy + dy * t


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

    # ---- internal helpers ----
    def _next_id(self, prefix: str = "el") -> str:
        self._id_counter += 1
        return f"{prefix}-{self._id_counter}"

    def _add(self, el: Dict[str, Any]) -> Dict[str, Any]:
        # Fractional ordering index — current Excalidraw exports carry one
        # per element; assigning it here keeps z-order stable on load.
        el["index"] = _frac_index(len(self.elements))
        self.elements.append(el)
        return el

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
        return self._add(el)

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
        return self._add(el)

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
        return self._add(el)

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
        return self._add(el)

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
        """Free-floating text.

        With `width`, the text is word-wrapped to that width and the element
        is marked autoResize=false so Excalidraw keeps the column instead of
        re-measuring it back into one long line. Without `width`, the text
        renders at its natural size (manual newlines are respected either way).
        """
        family = _FONT_FAMILY.get(font, 2)
        char_w = _CHAR_W.get(family, 0.55) * font_size
        if width is not None:
            max_chars = max(1, int(width / char_w))
            wrapped_lines: List[str] = []
            for para in content.split("\n"):
                wrapped_lines.extend(textwrap.wrap(para, max_chars) or [""])
            rendered = "\n".join(wrapped_lines)
        else:
            rendered = content
        lines = rendered.split("\n")
        approx_w = width or max(len(line) for line in lines) * char_w
        approx_h = len(lines) * font_size * 1.25
        el = {
            "id": self._next_id("txt"),
            "type": "text",
            "x": x, "y": y,
            "width": approx_w,
            "height": approx_h,
            **_common(strokeColor=color),
            "fontSize": font_size,
            "fontFamily": family,
            "textAlign": align,
            "verticalAlign": "top",
            "baseline": font_size - 2,
            "containerId": None,
            "originalText": content,
            "autoResize": width is None,
            "text": rendered,
            "lineHeight": 1.25,
        }
        return self._add(el)

    def node(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        *,
        shape: str = "rectangle",
        stroke_color: str = "#1971c2",
        background_color: str = "#a5d8ff",
        text_color: str = "#1e1e1e",
        font_size: int = 20,
        font: str = "helvetica",
        stroke_width: float = 2,
        rounded: bool = True,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """A shape with a label *bound inside it* — returns (container, text).

        The label is centered by Excalidraw itself (containerId/boundElements
        binding), so it stays centered even if the user resizes or renames the
        node. Use this instead of eyeballing text coordinates over a rect.
        Connect nodes with `scene.connect(container_a, container_b)`.
        """
        maker = {"rectangle": self.rect, "ellipse": self.ellipse,
                 "diamond": self.diamond}[shape]
        if shape == "rectangle":
            container = self.rect(x, y, w, h, stroke_color=stroke_color,
                                  background_color=background_color,
                                  stroke_width=stroke_width, rounded=rounded)
        else:
            container = maker(x, y, w, h, stroke_color=stroke_color,
                              background_color=background_color,
                              stroke_width=stroke_width)
        family = _FONT_FAMILY.get(font, 2)
        char_w = _CHAR_W.get(family, 0.55) * font_size
        lines = label.split("\n")
        tw = min(w - 10, max(len(l) for l in lines) * char_w)
        th = len(lines) * font_size * 1.25
        text_el = {
            "id": self._next_id("txt"),
            "type": "text",
            "x": x + (w - tw) / 2,
            "y": y + (h - th) / 2,
            "width": tw,
            "height": th,
            **_common(strokeColor=text_color),
            "fontSize": font_size,
            "fontFamily": family,
            "textAlign": "center",
            "verticalAlign": "middle",
            "baseline": font_size - 2,
            "containerId": container["id"],
            "originalText": label,
            "autoResize": True,
            "text": label,
            "lineHeight": 1.25,
        }
        self._add(text_el)
        container["boundElements"] = (container["boundElements"] or []) + [
            {"type": "text", "id": text_el["id"]}
        ]
        return container, text_el

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
        return self.arrow_path([(x1, y1), (x2, y2)],
                               stroke_color=stroke_color,
                               stroke_width=stroke_width,
                               start_arrowhead=start_arrowhead,
                               end_arrowhead=end_arrowhead)

    def arrow_path(
        self,
        points: List[Tuple[float, float]],
        *,
        stroke_color: str = "#1e1e1e",
        stroke_width: float = 2,
        start_arrowhead: Optional[str] = None,
        end_arrowhead: str = "arrow",
    ) -> Dict[str, Any]:
        """Multi-point arrow through absolute canvas coordinates.

        Use for elbow/L-shaped routing around obstacles:
        `scene.arrow_path([(0, 0), (120, 0), (120, 80)])`.
        """
        if len(points) < 2:
            raise ValueError("arrow_path needs at least 2 points")
        x0, y0 = points[0]
        rel = [[px - x0, py - y0] for px, py in points]
        xs = [p[0] for p in rel]
        ys = [p[1] for p in rel]
        el = {
            "id": self._next_id("arr"),
            "type": "arrow",
            "x": x0, "y": y0,
            "width": max(xs) - min(xs), "height": max(ys) - min(ys),
            **_common(strokeColor=stroke_color, strokeWidth=stroke_width),
            "points": rel,
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": start_arrowhead,
            "endArrowhead": end_arrowhead,
        }
        return self._add(el)

    def connect(
        self,
        a: Dict[str, Any],
        b: Dict[str, Any],
        *,
        stroke_color: str = "#1e1e1e",
        stroke_width: float = 2,
        start_arrowhead: Optional[str] = None,
        end_arrowhead: str = "arrow",
        elbow: bool = False,
        bind: bool = True,
        gap: float = 6,
        label: Optional[str] = None,
        label_size: int = 14,
        label_color: str = "#868e96",
    ) -> Dict[str, Any]:
        """Arrow from element `a` to element `b`, anchored edge-to-edge.

        Pass the element dicts returned by rect()/ellipse()/node()[0]. The
        anchor points are computed on the facing edges (never the centers),
        and with bind=True the arrow is bound to both shapes so it follows
        them when the user drags nodes around. elbow=True routes an L-shaped
        path (horizontal then vertical) instead of a straight line — useful
        when a straight shot would cross other nodes.
        """
        ba, bb = _bbox(a), _bbox(b)
        ca = (ba[0] + ba[2] / 2, ba[1] + ba[3] / 2)
        cb = (bb[0] + bb[2] / 2, bb[1] + bb[3] / 2)
        if elbow:
            # Leave a horizontally, arrive at b vertically (or the reverse,
            # whichever matches the dominant direction).
            if abs(cb[0] - ca[0]) >= abs(cb[1] - ca[1]):
                corner = (cb[0], ca[1])
                start = _edge_point(ba, corner[0], corner[1])
                end = _edge_point(bb, corner[0], corner[1])
            else:
                start = _edge_point(ba, ca[0], cb[1])
                corner = (ca[0], cb[1])
                end = _edge_point(bb, corner[0], corner[1])
            pts = [start, corner, end]
        else:
            start = _edge_point(ba, *cb)
            end = _edge_point(bb, *ca)
            pts = [start, end]
        arrow = self.arrow_path(pts, stroke_color=stroke_color,
                                stroke_width=stroke_width,
                                start_arrowhead=start_arrowhead,
                                end_arrowhead=end_arrowhead)
        if bind:
            arrow["startBinding"] = {"elementId": a["id"], "focus": 0, "gap": gap}
            arrow["endBinding"] = {"elementId": b["id"], "focus": 0, "gap": gap}
            for shape in (a, b):
                bound = shape["boundElements"] or []
                bound.append({"type": "arrow", "id": arrow["id"]})
                shape["boundElements"] = bound
        if label:
            mx = (pts[0][0] + pts[-1][0]) / 2
            my = (pts[0][1] + pts[-1][1]) / 2
            char_w = _CHAR_W[2] * label_size
            self.text(mx - len(label) * char_w / 2, my - label_size * 1.6,
                      label, font_size=label_size, color=label_color)
        return arrow

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
        return self._add(el)

    # ---- Layout QA ----
    def check_overlaps(self) -> List[str]:
        """Lint the scene for accidental collisions. Returns warning strings.

        Checks free text vs free text, and partial shape-on-shape overlap
        (containment is fine — that's how grouping boxes work). Bound labels
        and annotation ellipses are skipped: those overlap their containers
        by design. Run this before save() and fix anything it reports.
        """

        def overlap(b1, b2):
            ix = max(0.0, min(b1[0] + b1[2], b2[0] + b2[2]) - max(b1[0], b2[0]))
            iy = max(0.0, min(b1[1] + b1[3], b2[1] + b2[3]) - max(b1[1], b2[1]))
            return ix * iy

        def contains(outer, inner, tol=2):
            return (inner[0] >= outer[0] - tol and inner[1] >= outer[1] - tol
                    and inner[0] + inner[2] <= outer[0] + outer[2] + tol
                    and inner[1] + inner[3] <= outer[1] + outer[3] + tol)

        warnings = []
        free_texts = [e for e in self.elements
                      if e["type"] == "text" and not e.get("containerId")]
        for i in range(len(free_texts)):
            for j in range(i + 1, len(free_texts)):
                b1, b2 = _bbox(free_texts[i]), _bbox(free_texts[j])
                ia = overlap(b1, b2)
                m = min(b1[2] * b1[3], b2[2] * b2[3])
                if m > 0 and ia > 0.15 * m:
                    warnings.append(
                        f"text overlap: {free_texts[i]['text'][:30]!r} and "
                        f"{free_texts[j]['text'][:30]!r}"
                    )
        shapes = [e for e in self.elements
                  if e["type"] in ("rectangle", "diamond")]
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                b1, b2 = _bbox(shapes[i]), _bbox(shapes[j])
                if (overlap(b1, b2) > 4
                        and not contains(b1, b2) and not contains(b2, b1)):
                    warnings.append(
                        f"shape overlap: {shapes[i]['id']} and {shapes[j]['id']}"
                    )
        return warnings

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

    # Light fill variants (Excalidraw's default background swatches)
    FILL_RED = "#ffc9c9"
    FILL_ORANGE = "#ffd8a8"
    FILL_YELLOW = "#ffec99"
    FILL_GREEN = "#b2f2bb"
    FILL_TEAL = "#96f2d7"
    FILL_BLUE = "#a5d8ff"
    FILL_INDIGO = "#d0bfff"
    FILL_PURPLE = "#eebefa"
    FILL_PINK = "#fcc2d7"
    FILL_GRAY = "#ced4da"


if __name__ == "__main__":
    # Smoke test — build a tiny scene exercising the helpers.
    s = Scene()
    s.text(10, 10, "Hello, Excalidraw", font_size=32, color=Color.BLUE)
    a, _ = s.node(10, 80, 200, 80, "Service A")
    b, _ = s.node(400, 80, 200, 80, "Service B", background_color=Color.FILL_GREEN,
                  stroke_color=Color.GREEN)
    s.connect(a, b, label="gRPC")
    s.text(10, 220, "A long paragraph that should wrap into a neat column "
                    "instead of rendering as one enormous line.", width=260,
           font_size=14)
    warnings = s.check_overlaps()
    print("overlap warnings:", warnings or "none")
    print(s.to_json()[:200] + "...")
