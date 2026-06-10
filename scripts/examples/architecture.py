"""Architecture diagram — runnable example.

Builds a simple web-app architecture diagram:

    [ Client ]  →  [ API Gateway ]  →  [ Auth ]
                                    →  [ Users ]   →  [ Postgres ]
                                    →  [ Billing ]

Uses the library's node() and connect() helpers: labels are bound inside
their shapes (they stay centered when resized) and arrows are anchored
edge-to-edge with real bindings (they follow nodes when dragged).

Usage:
    python architecture.py

Writes architecture.excalidraw in the current directory.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from excalidraw import Scene, Color  # noqa: E402


def main():
    scene = Scene()

    # Title
    scene.text(0, 0, "Web App Architecture", font_size=36, color=Color.BLACK, font="helvetica")
    scene.text(0, 50, "Data flow from client through services to storage",
               font_size=16, color=Color.GRAY, font="helvetica")

    # Column 1: client
    client, _ = scene.node(0, 150, 180, 70, "Client",
                           stroke_color=Color.GREEN, background_color=Color.FILL_GREEN)

    # Column 2: API gateway
    gateway, _ = scene.node(300, 150, 180, 70, "API Gateway",
                            stroke_color=Color.INDIGO, background_color=Color.FILL_INDIGO)

    # Column 3: three services stacked vertically
    auth, _ = scene.node(600, 50, 180, 70, "Auth Service")
    users, _ = scene.node(600, 150, 180, 70, "Users Service")
    billing, _ = scene.node(600, 250, 180, 70, "Billing Service")

    # Column 4: shared database
    db, _ = scene.node(900, 150, 180, 70, "Postgres",
                       stroke_color=Color.ORANGE, background_color=Color.FILL_ORANGE)

    # Arrows — edge-anchored and bound, so they survive manual rearranging
    scene.connect(client, gateway, label="HTTPS")
    scene.connect(gateway, auth)
    scene.connect(gateway, users)
    scene.connect(gateway, billing)
    scene.connect(users, db)
    scene.connect(billing, db)

    # Legend
    legend_y = 400
    scene.text(0, legend_y, "Legend", font_size=20, color=Color.BLACK, font="helvetica")
    swatches = [
        (Color.GREEN, Color.FILL_GREEN, "Client-facing"),
        (Color.INDIGO, Color.FILL_INDIGO, "Edge / routing"),
        (Color.BLUE, Color.FILL_BLUE, "Application service"),
        (Color.ORANGE, Color.FILL_ORANGE, "Data store"),
    ]
    for i, (stroke, fill, label) in enumerate(swatches):
        y = legend_y + 35 + i * 30
        scene.rect(0, y, 20, 20, stroke_color=stroke, background_color=fill, rounded=True)
        scene.text(30, y + 3, label, font_size=14, font="helvetica")

    # Layout QA — catches accidental collisions before the user ever sees them
    for warning in scene.check_overlaps():
        print(f"LAYOUT WARNING: {warning}", file=sys.stderr)

    out = os.path.abspath("architecture.excalidraw")
    scene.save(out)
    print(f"Wrote {out} — open in excalidraw.com via File → Open")


if __name__ == "__main__":
    main()
