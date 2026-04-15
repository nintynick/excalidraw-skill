"""Side-by-side design review — runnable example.

Usage:
    python side_by_side.py <ref-image> <cur-image> [<ref-image> <cur-image> ...]

Produces a design-review.excalidraw file in the current directory with each
ref/cur pair placed on its own row, red-circle annotations, and a notes column.
This is the same pattern used for design reviews where you compare mockups to
the actual built version.

Open the output in excalidraw.com via File → Open (or Cmd+O).
"""

import os
import sys

# Make the excalidraw library importable when this file is run directly from
# scripts/examples/ or copied elsewhere.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from excalidraw import Scene, Color  # noqa: E402


# Hard-coded notes for the demo; real usage would accept these as inputs
# (CLI flags, a YAML config, or just hand-edited before running).
DEMO_NOTES = [
    {
        "title": "Row 1 — compare",
        "left_annotations": [
            {"x": 100, "y": 100, "w": 160, "h": 50, "note": "Important element"},
        ],
        "diffs": [
            "Left version uses solid background; right uses gradient — align on one style.",
            "Right version adds new CTA that doesn't exist on the left. Confirm scope.",
        ],
    },
]


def build_scene(pairs, notes=None):
    """Build and return a Scene from a list of (ref_path, cur_path) pairs."""
    scene = Scene()
    notes = notes or []

    # Title
    scene.text(0, -80, "Design Review", font_size=48, color=Color.BLACK, font="helvetica")
    scene.text(
        0, -20,
        "Reference (left)  vs.  Current (right)",
        font_size=20, color=Color.GRAY, font="helvetica",
    )

    cursor_y = 60
    COL_GAP = 80
    ROW_GAP = 200

    for row_i, (ref_path, cur_path) in enumerate(pairs):
        row_notes = notes[row_i] if row_i < len(notes) else {}

        # Row title
        scene.text(
            0, cursor_y,
            row_notes.get("title", f"Row {row_i + 1}"),
            font_size=32, color=Color.BLUE, font="helvetica",
        )
        cursor_y += 55

        # Embed images
        fid_l, wl, hl = scene.add_image_file(ref_path)
        fid_r, wr, hr = scene.add_image_file(cur_path)

        # Scale down so multiple rows fit comfortably
        scale = 0.5
        dwl, dhl = wl * scale, hl * scale
        dwr, dhr = wr * scale, hr * scale

        # Sub-labels
        scene.text(0, cursor_y, "Reference", font_size=14, color=Color.GRAY)
        scene.text(dwl + COL_GAP, cursor_y, "Current", font_size=14, color=Color.GRAY)
        cursor_y += 22

        # Images
        img_y = cursor_y
        scene.image(0, img_y, dwl, dhl, fid_l)
        scene.image(dwl + COL_GAP, img_y, dwr, dhr, fid_r)

        # Red annotations on the reference image
        for ann in row_notes.get("left_annotations", []):
            ax = ann["x"] * scale
            ay = img_y + ann["y"] * scale
            aw = ann["w"] * scale
            ah = ann["h"] * scale
            scene.ellipse(ax, ay, aw, ah, stroke_color=Color.RED, stroke_width=4)
            scene.text(
                ax, ay + ah + 6,
                ann["note"],
                font_size=12, color=Color.RED, font="helvetica",
            )

        # Notes column to the right of the images
        notes_x = dwl + COL_GAP + dwr + 80
        scene.text(
            notes_x, img_y,
            "KEY DIFFERENCES",
            font_size=20, color=Color.BLUE, font="helvetica",
        )
        diff_text = "\n\n".join(
            f"{i + 1}. {d}" for i, d in enumerate(row_notes.get("diffs", []))
        )
        scene.text(
            notes_x, img_y + 35,
            diff_text,
            font_size=14, color=Color.BLACK, font="helvetica",
            width=700,
        )

        cursor_y = img_y + max(dhl, dhr) + ROW_GAP

    return scene


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print(__doc__)
        sys.exit(1)
    pairs = list(zip(args[::2], args[1::2]))
    scene = build_scene(pairs, notes=DEMO_NOTES)
    out = os.path.abspath("design-review.excalidraw")
    scene.save(out)
    print(f"Wrote {out} — open in excalidraw.com via File → Open")


if __name__ == "__main__":
    main()
