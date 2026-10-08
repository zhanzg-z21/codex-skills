# Clean Vector Reconstruction Protocol

## Classification before drawing

Every reference element must be assigned a semantic role before Illustrator mutation. Schema 0.2 requires explicit `classification` and `semantic_type` on every element. Legacy nodes and edges are intrinsically structured geometry and retain compatibility.

`structured_geometry`: text, rectangle, rounded_rectangle, ellipse, line, arrow and simple_connector. Rebuild as editable text or native geometric paths.

`semantic_vector_illustration`: organ, cell, organelle, flame, molecule, biomedical_icon and cartoon_anatomical_structure. Rebuild as few meaningful Bézier fill regions and internal strokes. Each illustration needs a group so QC measures the whole object.

`irreducible_raster_evidence`: microscopy, western_blot, histology, medical_imaging and photograph. Preserve the raster evidence and supply an evidence note.

Do not relabel an organ cartoon as a photograph to bypass vector QC. Do not redraw measured histology or a blot as invented vector evidence.

## Semantic reconstruction

Image Trace is prohibited as the final output for semantic illustrations. Identify the silhouette, major internal structure, scientific meaning, color hierarchy and stroke hierarchy first. Reconstruct those structures with a small number of named Bézier regions, using smooth handles for organic contours and corners only where the anatomy or symbol requires one.

Never trace antialiasing halo, pixel noise, compression artifact or minor color variations. A gradient is a native Illustrator gradient fill, never a flattened bitmap. Use compound paths for genuine holes. Reduce path count, anchor count and tiny fragments while preserving meaningful anatomy. Shared boundaries should share curve geometry so adjacent regions do not create accidental white gaps.

Reference interpretation remains an agent task. The renderer deterministically executes validated geometry; it does not infer anatomy from pixels. An existing clean authored vector fixture can be serialized and replayed for regression, but this is not evidence of general automatic image understanding.

## Native schema and units

FigureSpec 0.2 adds `elements`, `groups` and ordered `layers` to the old node/edge schema. Vector elements currently use reconstruct mode and explicit canvas dimensions. Anchors, handles and text positions use normalized canvas coordinates, with top left origin and positive y down. Stroke widths and typography remain points. Handles may extend beyond the artboard, anchors must stay within it. `opacity` is 0 to 100. A smooth anchor's handles must be opposite and collinear.

`bezier_path` contains `closed`, `anchors`, `fill`, `stroke`, `stroke_width`, `opacity`, `z_order`, `group` and `layer`. Each anchor contains `anchor`, `in_handle`, `out_handle` and `point_type` (`smooth` or `corner`). `stroke_path` uses the same geometry and forces no fill. `compound_path` contains multiple contours plus a shared style and `fill_rule` (`nonzero` or `evenodd`). Native `text` remains editable. `raster_evidence` is limited to evidence classification and requires `source`, normalized bounds and `evidence_note`.

A linear gradient fill contains `type: linear`, `axis: horizontal` and 2 to 64 `stops`. Each stop has offset 0 to 100, RGB color, opacity and midpoint. Stops must be sorted and cover both ends. The stable interface uses Illustrator's native object-bounds horizontal gradient. Arbitrary axes, explicit endpoints and radial gradients are not accepted. Native gradient transforms were tested on Illustrator 30.0.0 but did not reliably preserve their requested endpoints, so they are excluded from the supported interface.

Layers are listed from back to front. Within each parent, groups and elements are ordered by ascending `z_order`. A group has an optional parent in the same layer; missing groups and cycles are rejected. Vector text positions describe the top left of native text bounds, not a baseline.

## QC and completion

Run schema and preflight QC before opening a document. After rendering, read back the actual Illustrator PathItems and PathPoints and compare anchors, handles, point type, closed state, fill, stroke, opacity and text. Count paths, anchors, tiny fragments, raster objects, open paths and duplicate painted objects per semantic group.

Contextual warnings consider bounding-box area, filled contour area, relative fragment size, path density and declared semantic complexity. A complex declaration requires an explanation. These are diagnostics, not universal anatomical complexity limits. Open paths can be meaningful vessels and fissures; they are counted without automatically failing. Exact duplicate detection does not detect every reversed or nearly overlapping path.

`CLEAN_VECTOR_QC_WARNING` stops successful rendering when semantic reconstruction is needed. Investigate warnings; do not raise complexity simply to bypass a tracing problem. Pure vector raster/plugin contamination is a failure. Legitimate evidence rasters remain separately classified.

Reference reconstruction automatically exports a 100% overview and 400% and 800% crops for every semantic illustration, largest first. Inspect all files with an image-viewing tool. Check rough edges, tracing halo, pixel-like contour, fragmented colors, excessive anchors and visible raster. Point counts come from native read-back; visual smoothness comes from looking at the exported curves. There is no reliable automatic image-artifact detector in this version.

The renderer returns `pending_visual_review`. Call `renderer.visual_qc.record_visual_review` only after inspecting the images, with a named reviewer, one observation per file and every artifact flag assessed. Missing reviews or detected artifacts prevent a passed manifest. When any visible tracing artifact exists, reconstruct and render a fresh result. Do not declare the figure complete while the manifest is pending or blocked.

## Private fixtures

All user-derived references and clean heart fixture coordinates stay in `tests/private_fixtures`. That entire directory is ignored by Git. Public tests use synthetic geometry. Do not publish user images, generated crops, AI documents or fixture data without explicit authorization.
