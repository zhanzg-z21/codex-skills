---
name: artifact-template-medical-editorial-scientific-ppt
description: "Create a presentation using the 医学期刊编辑风科研组会 Medical Editorial Scientific PPT template and its retained reference file. Use when the user selects this template, names 医学期刊编辑风科研组会 Medical Editorial Scientific PPT, or explicitly invokes $artifact-template-medical-editorial-scientific-ppt. 基于医学期刊编辑风视觉体系创建可编辑科研组会、研究方案与课题汇报 PowerPoint。参考文件包含 22 页通用版式、可替换文字与图片占位区，不含具体课题内容。"
---

# 医学期刊编辑风科研组会 Medical Editorial Scientific PPT

Create a presentation from this template. Keep the reference file unchanged.

## Workflow

1. Read `artifact-template.json` and resolve its paths relative to this skill directory.
2. Load [@presentations](plugin://presentations@openai-primary-runtime) and invoke its reference/template workflow with the retained file.
3. Treat the user's prompt and available sources as the content input. Do not invent facts merely to fill a template slot.
4. Clone or import the reference instead of replacing its visual system with generic defaults.
5. Render and verify the finished presentation, then return the final artifact.

## Fidelity

Preserve source slides, layouts, masters, typography, geometry, images, charts, tables, and recurring slide chrome.

User instructions control requested content and explicit deviations. The retained reference controls layout and formatting where the user has not requested a change.
