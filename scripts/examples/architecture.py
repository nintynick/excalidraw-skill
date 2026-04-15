"""Architecture diagram — runnable example.

Builds a simple web-app architecture diagram:

    [ Client ]  →  [ API Gateway ]  →  [ Auth ]
                                    →  [ Users ]   →  [ Postgres ]
                                    →  [ Billing ]

Usage:
    python architecture.py

Writes architecture.excalidraw in the current directory.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from excalidraw import Scene, Color  # noqa: E402


def node(scene, label, x, y, w=180, h=70, *, color=Color.BLUE, fill=Color.FILL_BLUE):
    """Draw a rounded-rect node with a centered text label.

    Returns (x, y, w, h) so callers can connect arrows to its edges.
    """
    scene.rect(
        x, y, w, h,
        rounded=True,
        stroke_color=color,
        background_color=fill,
        stroke_width=2,
    )
    # Rough text centering: width ≈ chars * fontSize * 0.55
    font_size = 18
    approx_w = len(label) * font_size * 0.55
    scene.text(
        x + (w - approx_w) / 2,
        y + (h - font_size) / 2,
        label,
        font_size=font_size,
        color=Color.BLACK,
        font="helvetica",
    )
    return (x, y, w, h)


def connect(scene, a, b, *, label=None):
    """Arrow from the right edge of a to the left edge of b."""
    x1 = a[0] + a[2]
    y1 = a[1] + a[3] / 2
    x2 = b[0]
    y2 = b[1] + b[3] / 2
    scene.arrow(x1, y1, x2, y2)
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2 - 20
        scene.text(mid_x - 20, mid_y, label, font_size=12, color=Color.GRAY)


def main():
    scene = Scene()

    # Title
    scene.text(0, 0, "Web App Architecture", font_size=36, color=Color.BLACK, font="helvetica")
    scene.text(0, 50, "Data flow from client through services to storage",
               font_size=16, color=Color.GRAY, font="helvetica")

    # Column 1: client
    client = node(scene, "Client", 0, 150, color=Color.GREEN, fill=Color.FILL_GREEN)

    # Column 2: API gateway
    gateway = node(scene, "API Gateway", 300, 150, color=Color.INDIGO,
                   fill="#d0bfff")

    # Column 3: three services stacked vertically
    auth    = node(scene, "Auth Service",    600, 50)
    users   = node(scene, "Users Service",   600, 150)
    billing = node(scene, "Billing Service", 600, 250)

    # Column 4: shared database
    db = node(scene, "Postgres", 900, 150, color=Color.ORANGE, fill="#ffd8a8")

    # Arrows
    connect(scene, client, gateway, label="HTTPS")
    connect(scene, gateway, auth)
    connect(scene, gateway, users)
    connect(scene, gateway, billing)
    connect(scene, users, db)
    connect(scene, billing, db)

    # Legend
    legend_y = 400
    scene.text(0, legend_y, "Legend", font_size=20, color=Color.BLACK, font="helvetica")
    scene.rect(0, legend_y + 35, 20, 20, stroke_color=Color.GREEN,
               background_color=Color.FILL_GREEN, rounded=True)
    scene.text(30, legend_y + 38, "Client-facing", font_size=14, font="helvetica")
    scene.rect(0, legend_y + 65, 20, 20, stroke_color=Color.INDIGO,
               background_color="#d0bfff", rounded=True)
    scene.text(30, legend_y + 68, "Edge / routing", font_size=14, font="helvetica")
    scene.rect(0, legend_y + 95, 20, 20, rounded=True,
               background_color=Color.FILL_BLUE, stroke_color=Color.BLUE)
    scene.text(30, legend_y + 98, "Application service", font_size=14, font="helvetica")
    scene.rect(0, legend_y + 125, 20, 20, stroke_color=Color.ORANGE,
               background_color="#ffd8a8", rounded=True)
    scene.text(30, legend_y + 128, "Data store", font_size=14, font="helvetica")

    out = os.path.abspath("architecture.excalidraw")
    scene.save(out)
    print(f"Wrote {out} — open in excalidraw.com via File → Open")


if __name__ == "__main__":
    main()
