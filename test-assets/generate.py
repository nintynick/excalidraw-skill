"""Generate synthetic test fixtures for the excalidraw-author skill evals.

Creates 6 PNG files: ref-1..3 and cur-1..3, each representing a fake
"UI screen" with simple shapes and captions. No proprietary data — these are
plain colored rectangles rendered with stdlib-only PNG encoding.

Run from this directory:
    python generate.py
"""

import os
import struct
import zlib


def _write_png(path, width, height, pixels):
    """Write an 8-bit RGB PNG using stdlib only.

    pixels: flat bytes of length width * height * 3, row-major.
    """
    def chunk(tag, data):
        chunk_bytes = tag + data
        return (
            struct.pack(">I", len(data))
            + chunk_bytes
            + struct.pack(">I", zlib.crc32(chunk_bytes))
        )

    # Add a filter byte (0 = None) at the start of each row
    row_bytes = width * 3
    scanlines = b"".join(
        b"\x00" + pixels[i * row_bytes : (i + 1) * row_bytes]
        for i in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(scanlines, 9)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", idat)
    png += chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(png)


def _hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _draw_rect(pixels, width, x, y, w, h, color):
    r, g, b = color
    for py in range(max(0, y), min(len(pixels) // (width * 3), y + h)):
        for px in range(max(0, x), min(width, x + w)):
            idx = (py * width + px) * 3
            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b


# Very simple 5x7 bitmap font covering the characters we need for captions.
# Each glyph is 7 rows × 5 columns, rendered as strings of # and spaces.
GLYPHS = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ####", "#    ", "#    ", "#  ##", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    " ": ["     ", "     ", "     ", "     ", "     ", "     ", "     "],
    "1": ["  #  ", " ##  ", "# #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#####", "    #", "   # ", "  ## ", "    #", "#   #", " ### "],
    "-": ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
}


def _draw_text(pixels, width, x, y, text, color, scale=3):
    for ch_i, ch in enumerate(text.upper()):
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        base_x = x + ch_i * (5 + 1) * scale
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "#":
                    _draw_rect(
                        pixels, width,
                        base_x + col * scale,
                        y + row * scale,
                        scale, scale,
                        color,
                    )


def make_image(path, caption, accent_hex, variant):
    """Create a fake UI mockup PNG at `path` with the given caption and color.

    `variant` is either "ref" (reference/mockup) or "cur" (current/built)
    so the two versions of each pair look visually different.
    """
    width, height = 480, 300
    bg = (245, 247, 250) if variant == "ref" else (255, 255, 255)
    pixels = bytearray([0] * (width * height * 3))

    # Fill background
    for i in range(0, len(pixels), 3):
        pixels[i] = bg[0]
        pixels[i + 1] = bg[1]
        pixels[i + 2] = bg[2]

    accent = _hex_to_rgb(accent_hex)
    border = (50, 50, 60)

    # Top bar
    _draw_rect(pixels, width, 0, 0, width, 36, accent)
    _draw_text(pixels, width, 12, 10, caption, (255, 255, 255), scale=2)

    # "Content" box in the middle, style differs by variant
    if variant == "ref":
        _draw_rect(pixels, width, 40, 80, width - 80, 40, (220, 225, 230))
        _draw_rect(pixels, width, 40, 140, width - 80, 40, (220, 225, 230))
        _draw_rect(pixels, width, 40, 200, width - 80, 40, (220, 225, 230))
        _draw_text(pixels, width, 50, 92, "ROW 1", border, scale=2)
        _draw_text(pixels, width, 50, 152, "ROW 2", border, scale=2)
        _draw_text(pixels, width, 50, 212, "ROW 3", border, scale=2)
    else:
        # Current variant uses a grid layout instead of stacked rows
        _draw_rect(pixels, width, 40, 80, (width - 100) // 2, 60, (230, 238, 250))
        _draw_rect(pixels, width, 60 + (width - 100) // 2, 80,
                   (width - 100) // 2, 60, (230, 238, 250))
        _draw_rect(pixels, width, 40, 160, (width - 100) // 2, 60, (230, 238, 250))
        _draw_rect(pixels, width, 60 + (width - 100) // 2, 160,
                   (width - 100) // 2, 60, (230, 238, 250))
        _draw_text(pixels, width, 50, 96, "TILE A", border, scale=2)
        _draw_text(pixels, width, 250, 96, "TILE B", border, scale=2)
        _draw_text(pixels, width, 50, 176, "TILE C", border, scale=2)
        _draw_text(pixels, width, 250, 176, "TILE D", border, scale=2)

    # Footer bar
    _draw_rect(pixels, width, 0, height - 30, width, 30, (235, 235, 240))
    _draw_text(pixels, width, 12, height - 22, variant.upper() + " VARIANT", border, scale=2)

    _write_png(path, width, height, bytes(pixels))


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    pairs = [
        ("1", "HOME SCREEN", "#1971c2"),
        ("2", "SETTINGS",    "#2f9e44"),
        ("3", "PROFILE",     "#e03131"),
    ]
    for num, caption, color in pairs:
        ref_path = os.path.join(out_dir, f"ref-{num}.png")
        cur_path = os.path.join(out_dir, f"cur-{num}.png")
        make_image(ref_path, caption, color, "ref")
        make_image(cur_path, caption, color, "cur")
        print(f"Wrote {ref_path}")
        print(f"Wrote {cur_path}")


if __name__ == "__main__":
    main()
