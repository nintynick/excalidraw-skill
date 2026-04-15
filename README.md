# excalidraw-skill

A [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) / [Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview) skill for programmatically generating **`.excalidraw`** files — architecture diagrams, flowcharts, annotated screenshots, side-by-side design reviews, timelines, mind maps, wireframes, and any other canvas layout you'd otherwise draw by hand.

The skill bundles a small pure-Python library for composing scenes, instructions that teach Claude how to use it well, and a set of runnable examples. When invoked, Claude writes a `.excalidraw` file to disk; you open it in [excalidraw.com](https://excalidraw.com) via **File → Open** (or `Cmd+O`) and see the full scene — images, shapes, arrows, text, annotations — all editable.

## Why

Excalidraw stores entire scenes as a single JSON document. That means Claude can write one directly with no browser automation, no plugin API, and no clipboard hacks. The hard part is getting the element schema exactly right (every element needs `seed`, `version`, `versionNonce`, `boundElements`, `groupIds`, `roundness`, `updated`… and missing any of them causes Excalidraw to refuse the file). The library in `scripts/excalidraw.py` handles all of that so the caller only thinks about geometry and content.

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/nintynick/excalidraw-skill.git ~/.claude/skills/excalidraw-author
```

Or any other path Claude Code scans for skills. The directory name becomes the skill name — this repo ships as `excalidraw-author` because that's the identifier declared in `SKILL.md`'s frontmatter.

Restart Claude Code. The skill will appear in the registry and trigger automatically the next time you ask for an Excalidraw file.

## What it does

Trigger phrases that reliably activate the skill:

- *"Build me an Excalidraw file showing our authentication flow"*
- *"Generate a `.excalidraw` diagram for this architecture: client → gateway → 3 services → postgres"*
- *"Compare these mockups to the built pages side by side in Excalidraw"*
- *"Annotate this screenshot with red circles pointing at the broken parts and export to Excalidraw"*
- *"Make a flowchart in Excalidraw for the order lifecycle"*
- *"Draw a mind map of possible product directions for Q3"*

Output is always a `.excalidraw` file at a path Claude will tell you. Open it in excalidraw.com via File → Open.

## What's in the repo

```
.
├── SKILL.md                     # Instructions Claude reads to use the skill
├── scripts/
│   ├── excalidraw.py            # Pure-Python library (no dependencies)
│   └── examples/
│       ├── side_by_side.py      # Design review: ref vs cur pairs with annotations
│       ├── architecture.py      # Flowchart: rects, arrows, labeled nodes
│       └── annotated.py         # Screenshot with red ellipse callouts
├── references/
│   ├── element_schema.md        # Full .excalidraw element field reference
│   └── layout_recipes.md        # Grid, timeline, mind map, swimlane, process map patterns
├── test-assets/                 # Synthetic placeholder images (6 PNGs) + generator
└── evals/evals.json             # Test prompts and assertions
```

Nothing depends on anything outside Python 3.8+ stdlib. The library parses PNG, JPEG, GIF, and WebP headers directly rather than pulling in Pillow.

## Using the library directly

You don't have to go through Claude — the library is usable as a plain Python module. Here's a minimal architecture diagram:

```python
import sys
sys.path.insert(0, "path/to/excalidraw-skill/scripts")
from excalidraw import Scene, Color

scene = Scene()

# Title
scene.text(0, 0, "System Architecture", font_size=36, color=Color.BLACK)

# Nodes
client  = scene.rect(  0, 150, 180, 70, rounded=True,
                       stroke_color=Color.GREEN, background_color=Color.FILL_GREEN)
scene.text(50, 175, "Client", font_size=20)

gateway = scene.rect(300, 150, 180, 70, rounded=True,
                     stroke_color=Color.INDIGO, background_color="#d0bfff")
scene.text(335, 175, "API Gateway", font_size=20)

# Arrow
scene.arrow(180, 185, 300, 185)

scene.save("architecture.excalidraw")
```

Run the bundled examples against the synthetic test fixtures:

```bash
cd scripts/examples
python architecture.py
python side_by_side.py ../../test-assets/ref-1.png ../../test-assets/cur-1.png
python annotated.py ../../test-assets/ref-1.png
```

Each writes a `.excalidraw` file to the current directory that you can open in excalidraw.com.

## What this skill does not do

- **Render `.excalidraw` to PNG/SVG.** Use Excalidraw's own export feature or its `@excalidraw/excalidraw` library for that.
- **Edit existing files in place.** The library can load and mutate scenes if you extend it, but the skill's focus is authoring from scratch.
- **Inject live into a running excalidraw.com tab.** That path exists (via `localStorage` + IndexedDB) but it's outside this skill's scope. Always produce a file; let the user open it.

## Development

The skill was built and iterated on using the [skill-creator](https://github.com/anthropic-experimental/claude-plugins-official) eval loop. Test prompts and assertions live in `evals/evals.json`. Test fixtures in `test-assets/` are synthetic placeholder images rendered from a pure-Python PNG encoder — no proprietary data.

To regenerate the test fixtures:

```bash
cd test-assets
python generate.py
```

## License

[MIT](LICENSE). Use it, fork it, ship it.

## Credits

Built with [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). The skill authoring loop is powered by the [skill-creator](https://github.com/anthropic-experimental/claude-plugins-official) skill.
