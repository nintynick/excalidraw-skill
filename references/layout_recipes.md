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
center_w, center_h = 220, 80
branches = ["Research", "Design", "Build", "Ship", "Learn"]

scene.rect(cx - center_w/2, cy - center_h/2, center_w, center_h,
           rounded=True, background_color=Color.FILL_YELLOW)
scene.text(cx - 40, cy - 10, "Project", font_size=24)

radius = 280
for i, label in enumerate(branches):
    angle = 2 * math.pi * i / len(branches)
    bx = cx + radius * math.cos(angle) - 80
    by = cy + radius * math.sin(angle) - 30
    scene.rect(bx, by, 160, 60, rounded=True, background_color=Color.FILL_BLUE)
    scene.text(bx + 12, by + 18, label, font_size=18)
    # Arrow from edge of center to edge of branch (approximate — use center-to-center)
    scene.arrow(cx, cy, bx + 80, by + 30, end_arrowhead=None)
```

## Process map (BPMN-lite)

Rectangles for tasks, diamonds for decisions, ellipses for start/end, arrows between.

```python
#  ( start ) → [ step 1 ] → [ step 2 ] → < decision > → [ step 3 ] → ( end )
#                                               ↓ no
#                                          [ alt path ]
start = scene.ellipse(0, 100, 80, 40, stroke_color=Color.GREEN, background_color=Color.FILL_GREEN)
step1 = scene.rect(120, 90, 160, 60, rounded=True)
scene.text(160, 110, "Submit form", font_size=16)
decision = scene.diamond(340, 80, 120, 80, stroke_color=Color.ORANGE)
scene.text(365, 110, "Valid?", font_size=16)
# arrows
scene.arrow(80, 120, 120, 120)
scene.arrow(280, 120, 340, 120)
scene.arrow(460, 120, 520, 120)
```

Position your nodes first, then draw arrows between their edges. Computing exact edge points is fiddly — for generated diagrams, shooting from center to center is usually fine because arrows auto-route to the edge visually.

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
