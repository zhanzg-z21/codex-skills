---
name: biomedical-illustrator-agent
description: Create and reconstruct biomedical mechanism figures, organ icons, cell icons, organelles and scientific illustrations as editable native Adobe Illustrator paths. Use for clean semantic vector reconstruction from reference images or natural language, with explicit evidence classification, Bezier geometry, native gradients and high magnification QC. Avoid final Image Trace artwork for semantic illustrations.
---

# Biomedical Illustrator Agent

This is a local fork of scientific-illustrator-agent. Resolve paths against this directory. Use the bundled renderer for the final artifact. Do not bypass it with temporary project JSX or hardcoded anatomical coordinates in renderer code.

## Prepare and classify

Use Windows Python with the dependencies in `requirements.txt` and a local Illustrator installation. Keep dependencies in this Skill's virtual environment. Review `docs/clean_vector_protocol.md` before reference reconstruction. Inspect the reference and classify every element before drawing: structured_geometry, semantic_vector_illustration or irreducible_raster_evidence. The exact role vocabulary and normalized coordinate contract are in that protocol and `src/models/vector_spec.py`.

Preserve uncertain labels as uncertainty. Preserve measured microscopy, Western blot, histology, medical imaging and photographic evidence as evidence. Never invent experimental features or redraw them as cartoons.

## Clean Vector Reconstruction Protocol

For organs, cells, organelles, flames, molecules, biomedical icons and cartoon anatomy, Image Trace is prohibited as final artwork. Rebuild a small number of meaningful Bézier regions and internal strokes. Ignore antialiasing halo, pixel noise, compression artifact and minor color variations. Preserve silhouette, major internal structure, scientific meaning, color hierarchy and stroke hierarchy. Reduce path count, anchor count and tiny fragments. Use shared curve boundaries where anatomical regions meet.

Write a FigureSpec 0.2 JSON with named semantic groups. Use bezier_path, compound_path and stroke_path for anatomy; keep text editable. Linear gradients are native Illustrator paint. No SVG rasterization or flattened substitute is permitted. Store reusable clean primitives in `assets/biomedical_vectors` only after provenance and QC review. User-derived geometry and images stay in ignored private fixtures.

For ordinary workflow nodes and arrows, the original FigureSpec 0.1 interface remains supported. See `src/models/figure_spec.py`, `src/layout/base.py` and the examples. Existing SVG progressive construction is a legacy vector-only import path; it is not the default semantic reconstruction route and does not replace clean vector QC.

## Render and verify

Run `python scripts/render.py spec.json result.ai` from this directory, or use absolute paths. This validates classification and geometry, performs contextual clean vector preflight, creates a fresh document, writes actual native PathItem and PathPoint objects, and reads the result back. Output files are never intentionally overwritten. Preserve other open documents and do not blindly retry failed mutations.

Review the actual native QC report. It counts paths, anchors, fragments, rasters, open paths and duplicates, using bounding box, area, density and declared complexity to flag likely tracing noise. Any CLEAN_VECTOR_QC_WARNING requires investigation and semantic reconstruction when appropriate. Do not inflate the complexity setting to pass a noisy trace.

For reference reconstruction, inspect the automatically exported 100% preview and 400% and 800% crops, largest semantic illustrations first. Check rough edges, tracing halo, pixel-like contour, fragmented colors, excessive anchors and visible raster. The code does not substitute numeric counts for visual review.

Rendering returns pending_visual_review until all required images have been opened and reviewed. Record specific observations through `renderer.visual_qc.record_visual_review`, or `python scripts/review.py manifest.json reviews.json`. Each review must contain its image path, an observation and a boolean for every artifact check, where true means an artifact is present. Any artifact blocks completion. Reconstruct into a fresh output and inspect again; never announce completion with visible tracing artifacts.

Deliver the AI file, preview, QC manifest and concise limitations. Cite actual read-back counts. Do not claim anatomical fidelity or visual review that was not performed.

## Maintainer validation

Run `python -m unittest discover -s tests` and `python tests/desktop_integration.py`. Public tests use synthetic geometry. Private regression data lives only in `tests/private_fixtures`; the private heart test skips if that data is absent. Desktop tests exercise actual paths, compound holes, gradients and editable text. See MODIFICATION_REPORT.md for tested application versions and regression outcomes.

The agent interprets references. The Python model, layout and QC are local. Illustrator document creation, PathPoints, native gradients, inspection, saving and image capture still use trusted bundled ExtendScript through Windows COM. Linear gradients currently use native horizontal object-bounds fill. Arbitrary gradient axes, radial gradients, arbitrary clipping groups and fully automatic visual artifact detection are not implemented.
