# excalidraw-author

A Claude skill for programmatically generating `.excalidraw` files — architecture diagrams, annotated screenshots, design reviews, flowcharts, timelines, mind maps, and any other layout you'd otherwise draw by hand.

The user opens the generated file in [excalidraw.com](https://excalidraw.com) (**File → Open**, or Cmd+O) and sees the full scene: images, shapes, arrows, text, annotations — all editable.

## Why

Excalidraw stores entire scenes as a single JSON file. That means Claude can *write* one directly — no browser automation, no drag-drop, no plugin API. This skill bundles:

- **A pure-Python library** (`scripts/excalidraw.py`) with primitives for every element type Excalidraw supports (image, rectangle, ellipse, diamond, text, arrow, line). No third-party dependencies — it parses PNG and JPEG headers with stdlib.
- **Instructions and layout recipes** (`SKILL.md`, `references/`) that teach Claude how to think about canvas coordinates, compose common layouts (side-by-side, grid, annotated image, flowchart), and avoid the sharp edges of the `.excalidraw` format.
- **Runnable examples** (`scripts/examples/`) covering the most common use cases.

## Installation

Copy this directory into `~/.claude/skills/` (or wherever your Claude Code skill directory lives), and restart Claude Code. The skill will appear in the skill registry and trigger automatically when you ask for Excalidraw output.

```bash
cp -r claude-excalidraw-skill ~/.claude/skills/excalidraw-author
```

## Triggering

The skill activates when you ask Claude things like:

- "Build me an Excalidraw file showing [X]"
- "Generate a `.excalidraw` diagram of our architecture"
- "Compare these two sets of screenshots side by side in Excalidraw"
- "Annotate this image with callouts and export to Excalidraw"
- "Make a flowchart in Excalidraw"

You'll get a `.excalidraw` file back. Open it in excalidraw.com via File → Open.

## What the skill does NOT do

- **Render** `.excalidraw` files to PNG/SVG. Use the real Excalidraw app or its export API for that.
- **Edit** existing `.excalidraw` files in place. (You can read and round-trip them with the library, but the skill's focus is authoring.)
- **Inject** into a running excalidraw.com tab. The skill writes files; you open them in the app.

## Development

Running the tests:

```bash
cd evals
# Test cases in evals.json
```

Test fixtures in `test-assets/` are synthetic placeholder images generated from simple shapes and captions. No proprietary data.

## License

MIT
