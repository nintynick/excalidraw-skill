"""Annotated screenshot — runnable example.

Places one image in the center of the canvas with red ellipse callouts
and text labels pointing at different regions, connected by arrows.

Usage:
    python annotated.py <image-path>

Writes annotated.excalidraw in the current directory.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from excalidraw import Scene, Color  # noqa: E402


# Hard-coded callouts for the demo. Real usage would accept these as input
# or compute them from image analysis.
DEMO_CALLOUTS = [
    {"cx_frac": 0.25, "cy_frac": 0.25, "w": 80, "h": 40, "label": "Upper-left region"},
    {"cx_frac": 0.75, "cy_frac": 0.25, "w": 80, "h": 40, "label": "Upper-right region"},
    {"cx_frac": 0.25, "cy_frac": 0.75, "w": 80, "h": 40, "label": "Lower-left region"},
    {"cx_frac": 0.75, "cy_frac": 0.75, "w": 80, "h": 40, "label": "Lower-right region"},
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    image_path = sys.argv[1]
    scene = Scene()

    # Title at the top
    scene.text(0, 0, "Annotated Screenshot", font_size=32, color=Color.BLACK, font="helvetica")

    # Embed image and downscale to 60% so there's room for callouts around it
    file_id, native_w, native_h = scene.add_image_file(image_path)
    scale = 0.6
    dw, dh = native_w * scale, native_h * scale

    image_x = 0
    image_y = 60
    scene.image(image_x, image_y, dw, dh, file_id)

    # For each callout, draw an ellipse on the image and a label to the right
    label_x = image_x + dw + 80
    for i, c in enumerate(DEMO_CALLOUTS):
        # Callout center on the image
        cx = image_x + c["cx_frac"] * dw
        cy = image_y + c["cy_frac"] * dh
        w = c["w"]
        h = c["h"]
        scene.ellipse(
            cx - w / 2, cy - h / 2, w, h,
            stroke_color=Color.RED,
            stroke_width=4,
        )
        # Numbered label on the ellipse
        scene.text(
            cx - 6, cy - 12,
            str(i + 1),
            font_size=20, color=Color.RED, font="helvetica",
        )

        # Matching text label off to the right
        label_y = image_y + 60 + i * 80
        scene.text(
            label_x, label_y,
            f"{i + 1}. {c['label']}",
            font_size=18, color=Color.BLACK, font="helvetica",
        )
        # Arrow from label back to the ellipse
        scene.arrow(
            label_x - 10, label_y + 10,
            cx + w / 2, cy,
            stroke_color=Color.RED,
            stroke_width=2,
        )

    out = os.path.abspath("annotated.excalidraw")
    scene.save(out)
    print(f"Wrote {out} — open in excalidraw.com via File → Open")


if __name__ == "__main__":
    main()
