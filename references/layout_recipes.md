# Layout recipes

Reach for these when you need a layout beyond the three core patterns in SKILL.md. Each recipe is a formula — a handful of coordinate rules plus the primitives to call. Tune the numbers to the task.

## Grid of cards

A regular grid of rectangular items (UI mockup tiles, feature cards, screenshot thumbnails).

```
┌───────┐  ┌───────┐  ┌───────┐
│       │  │       │  │       │
└───────┘  └───────┘  └───────┘
┌───────┐  ┌───────┐  ┌───────┐
│       │  │       │  │       │
└───────┘  └───────┘  └───────┘
```

```python
cols = 3
card_w, card_h = 280, 180
gutter_x, gutter_y = 40, 40
for i, item in enumerate(items):
    col = i % cols
    row = i // cols
    x = col * (card_w + gutter_x)
    y = row * (card_h + gutter_y)
    scene.rect(x, y, card_w, card_h, rounded=True, background_color=Color.FILL_BLUE)
    scene.text(x + 16, y + 16, item["title"], font_size=20)
    scene.text(x + 16, y + 50, item["description"], font_size=14, width=card_w - 32)
```

## Horizontal timeline

```
──●──────●──────●──────●──
  │      │      │      │
 Jan    Feb    Mar    Apr
```

```python
events = [("Jan", "Kickoff"), ("Feb", "Alpha"), ("Mar", "Beta"), ("Apr", "Launch")]
y = 100
spacing = 220
radius = 12
scene.line(0, y, (len(events) - 1) * spacing + spacing, y)
for i, (label, event) in enumerate(events):
    cx = i * spacing + 50
    scene.ellipse(cx - radius, y - radius, radius * 2, radius * 2,
                  stroke_color=Color.BLUE, background_color=Color.FILL_BLUE)
    scene.text(cx - 15, y + 25, label, font_size=16, color=Color.BLUE)
    scene.text(cx - 30, y + 50, event, font_size=14)
```

## Mind map

Center node + radial branches. Use simple math to place branches at regular angles.

```python
import math

cx, cy = 500, 400
branches = ["Research", "Design", "Build", "Ship", "Learn"]

hub, _ = scene.node(cx - 110, cy - 40, 220, 80, "Project",
                    background_color=Color.FILL_YELLOW, stroke_color=Color.ORANGE,
                    font_size=24)

radius = 280
for i, label in enumerate(branches):
    angle = 2 * math.pi * i / len(branches)
    bx = cx + radius * math.cos(angle) - 80
    by = cy + radius * math.sin(angle) - 30
    branch, _ = scene.node(bx, by, 160, 60, label, font_size=18)
    scene.connect(hub, branch, end_arrowhead=None)  # edge-anchored spoke
```

## Process map (BPMN-lite)

Rectangles for tasks, diamonds for decisions, ellipses for start/end, arrows between.

```python
#  ( start ) → [ step 1 ] → < decision > → [ step 2 ] → ( end )
#                                ↓ no
#                           [ alt path ]
start, _ = scene.node(0, 100, 80, 40, "Start", shape="ellipse",
                      stroke_color=Color.GREEN, background_color=Color.FILL_GREEN,
                      font_size=14)
step1, _ = scene.node(160, 90, 160, 60, "Submit form", font_size=16)
decision, _ = scene.node(400, 80, 130, 80, "Valid?", shape="diamond",
                         stroke_color=Color.ORANGE, background_color=Color.FILL_ORANGE,
                         font_size=16)
alt, _ = scene.node(400, 240, 160, 60, "Show errors", font_size=16,
                    stroke_color=Color.RED, background_color=Color.FILL_RED)

scene.connect(start, step1)
scene.connect(step1, decision)
scene.connect(decision, alt, label="no")   # vertical drop, edge-anchored
```

Position your nodes first, then `connect()` them — it anchors on the facing edges and binds the arrows so the diagram survives manual rearranging. Use `elbow=True` (or `arrow_path` with explicit waypoints) when a straight line would cut through another node.

## Swimlane diagram

Rows of activity grouped by actor. Useful for cross-team flows.

```python
lanes = ["User", "Frontend", "API", "Database"]
lane_h = 140
lane_w = 1200
for i, label in enumerate(lanes):
    y = i * lane_h
    scene.line(0, y, lane_w, y, stroke_color=Color.GRAY)
    scene.text(10, y + lane_h/2 - 10, label, font_size=18, color=Color.GRAY)
scene.line(0, len(lanes) * lane_h, lane_w, len(lanes) * lane_h, stroke_color=Color.GRAY)
# Now place nodes into lanes by setting y = lane_index * lane_h + padding
```

## Before/after banner

A narrower variant of side-by-side for single-screen comparisons. One row, two images, central divider.

```python
fid_a, wa, ha = scene.add_image_file("before.png")
fid_b, wb, hb = scene.add_image_file("after.png")
scale = 0.5
scene.text(0, 0, "Before", font_size=28, color=Color.GRAY)
scene.image(0, 50, wa * scale, ha * scale, fid_a)
gap = 100
after_x = wa * scale + gap
scene.text(after_x, 0, "After", font_size=28, color=Color.GREEN)
scene.image(after_x, 50, wb * scale, hb * scale, fid_b)
# Divider
divider_x = wa * scale + gap / 2
scene.line(divider_x, 0, divider_x, max(ha, hb) * scale + 50, stroke_color=Color.LIGHT_GRAY)
```

## Two-column notes

Headline + bulleted notes on one side, supporting illustration on the other.

```python
# Image on left, notes on right
fid, w, h = scene.add_image_file("diagram.png")
scale = 0.7
scene.image(0, 0, w * scale, h * scale, fid)
notes_x = w * scale + 80
scene.text(notes_x, 0, "Key takeaways", font_size=28, color=Color.BLUE)
bullets = "\n\n".join(f"• {line}" for line in lines)
scene.text(notes_x, 50, bullets, font_size=16, width=600)
```

## Tips that apply to any layout

- **Leave breathing room.** Cramped layouts read as amateurish. 40-100px of padding around every major element is a safe default.
- **Keep a consistent baseline grid.** If text rows are 20px tall, space titles at multiples of 20. It reads more intentional than it is.
- **Use color sparingly for meaning.** Black for structure, red for warnings/differences, blue for section headers, green for positive states. Don't rainbow-vomit.
- **Title every section.** A 32px blue heading before each row or region dramatically improves scannability for ~10 characters of text per heading.
- **Scale images before placing.** Full-resolution screenshots dwarf everything else. Downscale to 40-60% of native size unless the image is small.
- **Draw your annotations AFTER placing the thing you're annotating.** Element draw order matters — annotations need to render on top of their targets.
- **Wrap paragraph text.** Any text longer than a short label gets `width=` so it wraps into a column instead of one huge line.
- **Lint before saving.** `scene.check_overlaps()` catches text/shape collisions that look fine in coordinates but broken on canvas.
