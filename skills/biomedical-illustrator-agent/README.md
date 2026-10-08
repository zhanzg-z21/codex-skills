# Biomedical Illustrator Agent

A separate local fork of scientific-illustrator-agent for clean semantic biomedical vector reconstruction. The original Skill is unchanged. See SKILL.md for agent routing and docs/clean_vector_protocol.md for the complete reconstruction and QC contract.

## Execution

Create a local virtual environment using Python 3.9 or newer, install requirements.txt, and run commands from this directory with that environment's Python.

```text
python scripts/render.py input.spec.json outputs/result.ai
python -m unittest discover -s tests
python tests/desktop_integration.py
python scripts/review.py outputs/result.visual_qc/manifest.json reviews.json
```

Rendering creates a new Illustrator document and refuses existing output destinations. It returns a pending visual review status, not a completed illustration. Open every generated overview/crop before recording an honest review. Artifact detection or missing reviews blocks completion.

## Implementation map

`src/models/figure_spec.py` preserves the original node and edge API and adds normalized FigureSpec 0.2 elements. `src/models/vector_spec.py` validates classification, arbitrary Bézier anchors and handles, compound contours, strokes, editable text, evidence rasters and native linear gradients.

`src/illustrator/jsx/render_vectors.jsx` is a generic native Illustrator renderer. `src/illustrator/jsx/inspect_document.jsx` reads native geometry and styles back. `src/illustrator/inspection.py` can serialize clean existing authored vector geometry into a fixture, provided explicit semantic classifications are supplied. The exporter is a bounded regression utility and rejects unsupported object types.

`src/renderer/clean_vector_qc.py` computes contextual vector diagnostics. `src/renderer/native_verification.py` checks actual geometry and paint. `src/renderer/visual_qc.py` captures 100%, 400% and 800% images and records the required inspection gate. Typography and stroke widths use points; geometry is normalized to the entire canvas.

`assets/biomedical_vectors` defines the future asset-library contract without bundling user anatomy. Public unit tests use synthetic primitives. `tests/private_fixtures` and all outputs are ignored by Git. The private reconstruction test replays authored clean V2 geometry through this Skill; it does not claim autonomous understanding of a new raster reference.

## Compatibility and limitations

The original 0.1 nodes, edges, layout tests, COM ownership safeguards and SVG subset tests are retained. Native Illustrator operations use ExtendScript through pywin32 COM. This fork has no cloud requirement and is not an MCP server. The renderer never imports an SVG or runs Image Trace for the clean semantic path route.

Only RGB solid paint and horizontal object-bounds linear gradients are supported for the new vector route. Explicit gradient endpoints, arbitrary gradient angles, radial gradients, advanced clipping/masks, mixed-style text runs and arbitrary text transforms require future schema work. Read MODIFICATION_REPORT.md for actual test results, known limitations and local fixture provenance.
