# Excalidraw element schema reference

The `.excalidraw` file format is a JSON document. The library in `scripts/excalidraw.py` abstracts most of this, but when you need to reach past what the library offers — custom fill patterns, grouped elements, bound text inside shapes — this reference is the source of truth.

## Top-level scene shape

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "your-tool-name",
  "elements": [ ... element objects ... ],
  "appState": {
    "viewBackgroundColor": "#ffffff",
    "gridSize": null
  },
  "files": {
    "<fileId>": {
      "mimeType": "image/png",
      "id": "<fileId>",
      "dataURL": "data:image/png;base64,...",
      "created": 1700000000000,
      "lastRetrieved": 1700000000000
    }
  }
}
```

- `type` must be `"excalidraw"`. A value of `"excalidraw/clipboard"` is a different (partial) format for pasted selections.
- `version` is the schema version — `2` is current.
- `elements` is an array drawn in order. Later = on top.
- `files` is a dict keyed by `fileId`, each holding one embedded image as a base64 data URL.

## Fields every element has

```jsonc
{
  "id": "string",              // unique within the scene
  "type": "...",               // "image" | "rectangle" | "ellipse" | "diamond" | "text" | "arrow" | "line" | "freedraw"
  "x": 0, "y": 0,              // top-left in canvas pixels
  "width": 100, "height": 100,
  "angle": 0,                  // radians, rotation around center
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",        // "solid" | "hachure" | "cross-hatch" | "zigzag" | "dots" | "dashed"
  "strokeWidth": 2,
  "strokeStyle": "solid",      // "solid" | "dashed" | "dotted"
  "roughness": 0,              // 0 = smooth, 1 = normal, 2 = cartoonist
  "opacity": 100,              // 0-100
  "groupIds": [],              // array of group IDs this element belongs to
  "frameId": null,             // ID of the frame containing this element, or null
  "roundness": null,           // null or {type: 2 or 3} for rounded corners
  "seed": 12345,               // random int, used for deterministic roughness
  "versionNonce": 67890,       // random int, versioning nonce
  "version": 1,                // mutation version counter
  "isDeleted": false,
  "boundElements": null,       // or array of {type, id} for text bound to a container
  "updated": 1700000000000,    // ms timestamp
  "link": null,                // optional hyperlink URL
  "locked": false
}
```

Excalidraw will reject elements missing any of these. The library fills them in automatically.

## Type-specific fields

### image

```json
{
  "type": "image",
  "status": "saved",
  "fileId": "<matches a key in top-level files>",
  "scale": [1, 1]
}
```

The `fileId` must correspond to an entry in the top-level `files` dict. `status: "saved"` tells Excalidraw the image is embedded (as opposed to pending or error).

### rectangle / ellipse / diamond

No extra required fields beyond the common ones. For rounded rectangles set `roundness: {"type": 3}`; set it to `null` for sharp corners.

### text

```json
{
  "type": "text",
  "fontSize": 20,
  "fontFamily": 2,              // 1=Virgil, 2=Helvetica, 3=Cascadia, 4=Assistant
  "textAlign": "left",          // "left" | "center" | "right"
  "verticalAlign": "top",       // "top" | "middle" | "bottom"
  "baseline": 18,               // usually fontSize - 2
  "containerId": null,          // ID of container element if text is bound inside a shape
  "originalText": "...",        // text as-entered (before wrapping)
  "text": "...",                // text as-rendered (may have wrapping inserted)
  "lineHeight": 1.25
}
```

Excalidraw re-measures text dimensions on load, so `width` and `height` don't need to be perfectly accurate — reasonable estimates are fine. The library uses `len(line) * fontSize * 0.55` as a rough width estimate.

**Text bound inside a shape:** to put text "inside" a rectangle so it moves with the rectangle, set the text's `containerId` to the rectangle's `id` and add `{type: "text", id: <textId>}` to the rectangle's `boundElements` array. This is optional — free-floating text works fine for most diagrams.

### arrow

```json
{
  "type": "arrow",
  "points": [[0, 0], [100, 50]],
  "lastCommittedPoint": null,
  "startBinding": null,
  "endBinding": null,
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

- `x`, `y` is the arrow's origin. `points` are offsets from that origin, so the first point is always `[0, 0]`.
- For multi-segment arrows, add more points: `[[0,0], [50,0], [50,50], [100,50]]` creates an L-shaped path.
- `startArrowhead` / `endArrowhead` can be `null`, `"arrow"`, `"bar"`, `"dot"`, `"triangle"`, or `"triangle_outline"`.

**Binding arrows to shapes:** for an arrow that auto-updates when you move the connected shapes, set:
```json
"startBinding": {"elementId": "<shape-id>", "focus": 0, "gap": 5},
"endBinding": {"elementId": "<other-id>", "focus": 0, "gap": 5}
```
The library doesn't bind by default — arrows are positioned statically, which is fine for generated diagrams that you don't expect the user to manually rearrange much.

### line

Same as arrow but with both arrowheads `null`.

## Colors

Excalidraw has a standard palette but accepts any hex color. Standard values:

| Name | Stroke | Fill (light variant) |
|---|---|---|
| Black | `#1e1e1e` | — |
| Red | `#e03131` | `#ffc9c9` |
| Orange | `#f08c00` | `#ffd8a8` |
| Yellow | `#f1c40f` | `#ffec99` |
| Green | `#2f9e44` | `#b2f2bb` |
| Teal | `#099268` | `#96f2d7` |
| Blue | `#1971c2` | `#a5d8ff` |
| Indigo | `#6741d9` | `#d0bfff` |
| Purple | `#ae3ec9` | `#eebefa` |
| Pink | `#e64980` | `#fcc2d7` |
| Gray | `#868e96` | `#ced4da` |

`"transparent"` is also valid and is the default `backgroundColor` for shapes.

## AppState flags worth knowing

- `viewBackgroundColor` — canvas background, defaults to white
- `gridSize` — `null` or a number (e.g., `20`) to show a grid
- `currentItemFontFamily` — default font for newly-drawn text
- `theme` — `"light"` or `"dark"`
- `zoom` — `{value: 0.5}` etc. Not usually needed; Excalidraw auto-fits on load.

Most of these can be omitted and Excalidraw uses sensible defaults.

## Gotchas

- **Every element needs `seed` and `versionNonce`**, even if you're not animating or collaborating. Missing them causes Excalidraw to throw on load.
- **`points` in arrows/lines start at `[0, 0]`** relative to the element's `x, y`, not in absolute canvas coordinates. If your arrow isn't showing up where you expect, that's usually why.
- **Image `fileId` must match a key in `files`** exactly. Off-by-one on hashes or name mismatches = broken image.
- **`boundElements: null`** is valid. An empty array `[]` is also valid. Don't leave it undefined.
- **`frameId: null`** is required — Excalidraw groups elements into "frames" and checks this field unconditionally.
- **Unicode in text works**, but watch for narrow-no-break spaces (`U+202F`) sneaking into labels from screenshots or copy-paste.
