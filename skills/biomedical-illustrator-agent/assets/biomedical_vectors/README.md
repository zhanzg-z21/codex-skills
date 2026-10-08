# Biomedical vector primitives

This directory is an extensible library contract, not a stock icon collection. No user reference images or private heart coordinates belong here.

Future assets may represent heart, liver, intestine, mitochondrion, neutrophil, macrophage, nucleus, blood vessel and flame. Each asset is FigureSpec 0.2 JSON with named semantic groups, editable native paths, low anchor counts, scientific intent, author/license provenance and a QC record. Keep dimensions normalized. Use fill regions for major structures and stroke paths for meaningful internal anatomy.

An asset directory contains `asset.spec.json`, `metadata.json` and `QC.md`. Metadata identifies the organism/context, intended scientific meaning, source/license, major anatomical components, complexity justification and any limitations. QC records native path/anchor/fragment counts and inspected 100%, 400% and 800% views.

Do not store Image Trace exports, embedded bitmap surrogates, outlines made from compression noise, or hundreds of unlabelled fragments. Reuse an asset only when its scientific meaning matches the new figure. Otherwise author new meaningful curves using the generic renderer.

The first private heart regression is under `tests/private_fixtures`, which is ignored by Git. It is not a distributable library asset.
