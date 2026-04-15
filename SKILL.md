---
name: excalidraw-author
description: Generate .excalidraw files programmatically for any layout — architecture diagrams, flowcharts, annotated screenshots, design reviews, side-by-side visual comparisons, timelines, mind maps, process maps, UI wireframes, and freeform canvases. Use this skill whenever the user asks for an Excalidraw file, a .excalidraw output, a "drawing" / "diagram" / "canvas" / "whiteboard" in Excalidraw, or wants to compare screenshots visually, annotate an image with callouts, sketch an architecture, or produce any visual layout that would normally be drawn by hand. Also trigger when the user mentions Excalidraw at all in an output context, even if they haven't explicitly said "generate a file" — assume that's what they want unless they say otherwise. The skill writes files to disk; it does not open or render Excalidraw, so always hand the path back to the user and tell them to open it via File → Open on excalidraw.com.
---

# Excalidraw Author

Write `.excalidraw` files from Python. Any layout: architecture, flowcharts, annotated screenshots, visual diffs, timelines, mind maps, wireframes. The user opens the file in excalidraw.com and sees the whole scene — images, shapes, arrows, text, annotations — fully editable.

## Why this skill exists

Excalidraw stores entire scenes as a single JSON document. That means you can *write* a scene directly to disk. No browser automation. No Excalidraw plugin API. No clipboard hacks. Just a file.

The hard part is getting the JSON shape exactly right: every element has required fields (`seed`, `version`, `versionNonce`, `groupIds`, `boundElements`, `roundness`, `updated`, …) and missing any of them makes Excalidraw refuse to open the file or crash silently. The bundled `scripts/excalidraw.py` library handles those fields for you so you can focus on geometry and content.

## When to use this

Use this skill when the user asks for an Excalidraw file or any visual layout where Excalidraw is the natural output format. Common triggers:

- **Diagrams and flowcharts** — architecture, sequence flows, state machines, process maps, decision trees, org charts
- **Annotated screenshots** — red circles on UI elements, callouts with arrows, highlight-and-explain
- **Design reviews / visual diffs** — side-by-side comparisons of mockups vs. built pages, before/after, version A vs. version B
- **Whiteboards and freeform layouts** — brainstorms, mind maps, storyboards, timelines, Venn diagrams
- **Wireframes and sketches** — rough UI layouts, interaction flows

Do **not** use this skill for:
- Rendering a `.excalidraw` file to PNG/SVG (the real Excalidraw app handles that via its export API)
- Heavy image editing or pixel-level graphics (use image tools)
- Plain text documents (use Markdown)

## How to work with the library

Import `excalidraw.py` from `scripts/` (or copy the file next to your generated script — it's self-contained, stdlib only, no Pillow needed).

```python
import sys
sys.path.insert(0, "<path-to-skill>/scripts")
from excalidraw import Scene, Color

scene = Scene()
# ... add elements ...
scene.save("output.excalidraw")
```

### The core mental model

A **Scene** is a list of elements drawn in order (later elements draw on top of earlier ones) plus a dict of embedded image files. Coordinates are in pixels, origin top-left, y grows downward (standard screen coords). There's no enforced canvas size — the canvas is infinite; just use whatever coordinates make sense.

### Primitives you have

| Method | Produces | Key args |
|---|---|---|
| `scene.image(x, y, w, h, file_id)` | embedded image | file_id from `add_image_file` |
| `scene.rect(x, y, w, h, ...)` | rectangle | `stroke_color`, `background_color`, `rounded` |
| `scene.ellipse(x, y, w, h, ...)` | ellipse / circle | `stroke_color`, `stroke_width` (default red for annotations) |
| `scene.diamond(x, y, w, h, ...)` | diamond (decision nodes) | `stroke_color` |
| `scene.text(x, y, content, ...)` | text label or block | `font_size`, `font` (`"helvetica"` / `"virgil"` / `"cascadia"`), `color`, `width` for wrapping |
| `scene.arrow(x1, y1, x2, y2, ...)` | arrow | `stroke_color`, `end_arrowhead="arrow"` |
| `scene.line(x1, y1, x2, y2, ...)` | line | `stroke_color` |

To embed an image:

```python
file_id, w, h = scene.add_image_file("screenshot.png")
scene.image(100, 100, w, h, file_id)  # place at native size
# or scale it:
scale = 0.5
scene.image(100, 100, w * scale, h * scale, file_id)
```

`add_image_file` returns the image's native pixel dimensions so you can lay things out without guessing. PNG, JPEG, GIF, and WebP are supported. Images are base64-embedded directly in the file — the `.excalidraw` is self-contained and can be shared or checked in.

### Colors

Use `Color.RED`, `Color.BLUE`, `Color.GREEN`, etc. from the library, or any hex string. The default palette matches Excalidraw's built-in colors so your scene looks native. For annotations specifically, red (`Color.RED`) is conventional.

### Font families

Pass `font="helvetica"` (clean sans, good default for diagrams and notes), `"virgil"` (hand-drawn style, Excalidraw's sketchy default), or `"cascadia"` (monospace, good for code and titles). For design reviews and diagrams I recommend `"helvetica"` for body text and headings — it reads much better than Virgil at small sizes.

### Roughness

The library defaults all shapes to `roughness=0` (smooth lines, not Excalidraw's hand-drawn wobble). This reads as more professional for diagrams and reviews. If the user wants the sketchy look, shapes support manual override — but default smooth.

## Layout patterns

Composing a scene is 90% math: decide where things go, then call primitives. Three patterns cover most needs. Full worked examples are in `scripts/examples/`.

### Pattern 1: Side-by-side comparison

Use for design reviews, before/after, version A vs B, reference vs. actual. Each row has a title, two images side by side, and optional annotations and diff notes.

```python
# Pseudo-code — see scripts/examples/side_by_side.py for the real thing
ROW_GAP = 200
COL_GAP = 80
notes_w = 900

cursor_y = 0
for row in rows:
    scene.text(0, cursor_y, row["title"], font_size=32, color=Color.BLUE)
    cursor_y += 50
    fid_l, w_l, h_l = scene.add_image_file(row["left"])
    fid_r, w_r, h_r = scene.add_image_file(row["right"])
    scene.image(0, cursor_y, w_l, h_l, fid_l)
    scene.image(w_l + COL_GAP, cursor_y, w_r, h_r, fid_r)
    # Annotate left image (circles + notes)
    for circle in row["left_circles"]:
        x = circle["x"]; y = circle["y"] + cursor_y
        scene.ellipse(x, y, circle["w"], circle["h"])
        scene.text(x, y + circle["h"] + 6, circle["note"], font_size=12, color=Color.RED)
    # Notes block to the right
    notes_x = w_l + COL_GAP + w_r + 100
    scene.text(notes_x, cursor_y, "KEY DIFFERENCES", font_size=20, color=Color.BLUE)
    scene.text(notes_x, cursor_y + 35, "\n\n".join(row["diffs"]),
               font_size=14, width=notes_w)
    cursor_y += max(h_l, h_r) + ROW_GAP
```

Tips for side-by-side:
- Scale large images down (divide w/h by 2-4) so multiple rows fit on screen; 800-1200px wide is a good target.
- Leave **enough vertical gap between rows** (150-250px) that annotation notes below one row don't bleed into the title of the next.
- Put the notes/differences text block to the *right* of the images rather than above or below, so the visual comparison stays at eye level and the reader can glance sideways to read the prose.

### Pattern 2: Flowchart / architecture diagram

Use for anything where nodes connect with arrows. Conventions:

- **Rectangles** = processes, services, components
- **Diamonds** = decisions, branch points
- **Ellipses** = start/end markers
- **Arrows** = flow, data, dependencies
- Label nodes with `scene.text` centered *inside* the shape (compute x as `node_x + node_w/2 - text_w/2`; text width is roughly `len(label) * font_size * 0.55`)

```python
def node(scene, label, x, y, w=180, h=70):
    scene.rect(x, y, w, h, stroke_color=Color.BLUE, background_color=Color.FILL_BLUE, rounded=True)
    # Center the label inside the rect
    approx_w = len(label) * 20 * 0.55
    scene.text(x + (w - approx_w) / 2, y + h/2 - 12, label, font_size=20)

def connect(scene, a, b):
    # Connect right-edge of a to left-edge of b (simple case)
    scene.arrow(a[0] + a[2], a[1] + a[3]/2, b[0], b[1] + b[3]/2)
```

For arrows that route through multiple points, just draw several connected arrows or use `line` segments — Excalidraw arrows are straight, not splines.

### Pattern 3: Annotated screenshot

One image at the center of the canvas with red ellipse annotations and callouts.

```python
fid, w, h = scene.add_image_file("screenshot.png")
# Optional downscale so we have room for callouts
scale = 0.6
dw, dh = w * scale, h * scale
scene.image(0, 0, dw, dh, fid)

callouts = [
    {"cx": 120, "cy": 80, "label": "This button is where users get stuck"},
    {"cx": 400, "cy": 250, "label": "Loading spinner hangs here on slow network"},
]
for c in callouts:
    scene.ellipse(c["cx"] - 30, c["cy"] - 20, 60, 40,
                  stroke_color=Color.RED, stroke_width=4)
    # Callout text off to the right of the image
    text_x = dw + 80
    scene.text(text_x, c["cy"], c["label"], font_size=16, color=Color.RED)
    scene.arrow(text_x - 10, c["cy"] + 8, c["cx"] + 30, c["cy"], stroke_color=Color.RED)
```

## What to hand back to the user

After writing the file:

1. Print the absolute path so it's obvious
2. Tell the user to open it via **File → Open** (or Cmd+O) on excalidraw.com
3. Mention any scale/size decisions you made so they can adjust if needed

Example closing message:

> Wrote `/abs/path/output.excalidraw` (N elements, M embedded images).
> Open it in excalidraw.com via File → Open (or Cmd+O).
> Images were scaled to 50% of native size to fit the layout — let me know if you want them larger.

## Common mistakes to avoid

- **Don't forget required fields.** Every element needs `seed`, `version`, `versionNonce`, `groupIds`, `updated`, `boundElements`, etc. The library handles this — don't try to build element dicts manually unless you really know the schema.
- **Don't overload localStorage.** This skill writes *files* for the user to open via File → Open. It does not try to inject scenes into a live excalidraw.com tab via localStorage or IndexedDB. That path exists but isn't our job — always produce a file.
- **Don't skip dimension lookups.** Always use `scene.add_image_file()` to get real pixel dimensions rather than guessing. Layouts that assume all images are the same size break when they aren't.
- **Don't use `roughness=1` by default.** The hand-drawn look is cute but hurts legibility at small sizes. Default smooth (which the library provides) and only opt into sketchy when explicitly asked.
- **Don't use Virgil (default hand-drawn font) for body text.** Fine for a title, hard to read for 14px diff notes. Use `font="helvetica"` for anything non-display.

## Additional references

- `references/element_schema.md` — full list of element fields, types, and what Excalidraw expects
- `references/layout_recipes.md` — more layout patterns (grid, timeline, mind map, process map)
- `scripts/examples/side_by_side.py` — runnable design-review example
- `scripts/examples/architecture.py` — runnable flowchart example
- `scripts/examples/annotated.py` — runnable annotated-screenshot example

Read a reference file when your task goes beyond the three core patterns above, or when you need a field that isn't covered by the library's primitives.
