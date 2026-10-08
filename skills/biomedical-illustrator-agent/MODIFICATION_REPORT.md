# biomedical-illustrator-agent 修改报告

日期：2026-09-20。原项目 scientific-illustrator-agent 保留，本次改动、依赖环境、测试数据和输出均位于独立的 biomedical-illustrator-agent 目录。原项目的 README.md、SKILL.md、models、renderer、illustrator、layout 与 tests 已完整阅读。

## 实现变更

FigureSpec 保留 0.1 节点和边接口，并加入 0.2 矢量元素接口。新增 bezier_path、stroke_path、compound_path、Anchor、Contour、GradientFill、GradientStop、VectorText、RasterEvidence 与 VectorGroup。路径支持 closed、anchor、in_handle、out_handle、smooth/corner、fill、stroke、stroke_width、opacity、z_order、group、layer、端点样式、连接样式、虚线和复合填充规则。几何采用归一化坐标，字体和描边采用点单位。

新增三类 reference classification。新矢量元素必须显式指定分类和语义类型；旧节点和边按其几何定义归入 structured_geometry。semantic_vector_illustration 必须属于可统计的插图组。raster_evidence 仅允许用于显微图、Western blot、组织学、医学影像和照片等实验证据，不能借此放置器官卡通位图。

通用 JSX renderer 直接建立 Illustrator PathItem、PathPoint 和 CompoundPathItem，写入左右控制柄与 PointType。它不包含 heart、liver、gut 或 flame 的坐标，也不导入 SVG 来替代原生路径。图层和分组支持层级及 z_order。所有最终原生锚点、控制柄、路径闭合状态、填充、描边、透明度和文字均经过读回比对。

渐变支持原生水平线性填充、多色 stop、stop opacity 与 midpoint，不产生 raster。稳定接口使用对象范围内的水平渐变。曾测试任意角度的原生渐变变换，但 Illustrator 30.0.0 未可靠保留指定端点，因此没有把该能力加入正式接口。径向渐变同样未开放。

Clean Vector QC 统计 semantic groups 的 path count、anchor point count、tiny fragment count、raster object count、open path count 和 duplicate object count。判断结合 bounding box、轮廓面积、相对碎片尺寸、path density 与有说明的复杂度，不用单一绝对阈值判断所有器官。CLEAN_VECTOR_QC_WARNING 会阻止完成；未分类的原生附加对象和额外 raster 也会被检查。

visual QC 自动导出 100% 整图，以及每个 semantic illustration 的 400% 和 800% 裁剪，并按对象面积从大到小排列。渲染后状态为 pending_visual_review。逐图记录观察并通过检查后，manifest 和 registry 才更新为 passed。检测到明显 tracing artifact 时不能宣布完成。

## 文件范围

修改文件：`.gitignore`；`README.md`；`SKILL.md`；`pyproject.toml`；`src/illustrator/jsx/render_scene.jsx`；`src/illustrator/jsx_builder.py`；`src/layout/base.py`；`src/models/figure_spec.py`；`src/renderer/illustrator_renderer.py`。

新增实现与说明文件：`assets/biomedical_vectors/README.md`；`docs/clean_vector_protocol.md`；`scripts/render.py`；`scripts/review.py`；`src/illustrator/inspection.py`；`src/illustrator/jsx/inspect_document.jsx`；`src/illustrator/jsx/render_vectors.jsx`；`src/models/vector_spec.py`；`src/renderer/clean_vector_qc.py`；`src/renderer/native_verification.py`；`src/renderer/visual_qc.py`；`tests/desktop_integration.py`；`tests/prepare_private_fixture.py`；`tests/private_reconstruction_integration.py`；`tests/test_clean_vectors.py`；`tests/test_private_heart.py`。

`assets/biomedical_vectors/README.md` 定义后续 heart、liver、intestine、mitochondrion、neutrophil、macrophage、nucleus、blood vessel 和 flame 的资源格式、来源记录和 QC 要求，没有批量添加图标。

所有用户衍生坐标、V1 baseline、V1 高倍心脏对照及 clean heart fixture 仅存于 `tests/private_fixtures`，整个目录已加入 `.gitignore`。输出目录同样被忽略。没有复制用户原始参考图到公开资源目录，也没有上传或发布任何仓库。

## 实际测试结果

执行 `python -m unittest discover -s tests`：35 项通过，无失败。包含原有 17 项测试、16 项新增通用测试，以及本地启用的 2 项 private heart regression。缺少私有 fixture 的公开副本会跳过 2 项 private heart 测试。原有 5 个 test 文件逐字节保持不变。

Skill creator 的 quick_validate 校验通过。测试环境为 Windows、Python 3.12.10、Pydantic 2.13.5、pywin32 312、Pillow 11.3.0，Illustrator 30.0.0。PyYAML 仅安装在新 Skill 的本地环境，用于 Skill metadata 校验。

桌面 synthetic integration 通过：闭合 Bézier、开放 stroke_path、smooth/corner、复合路径孔洞、RGB、描边和透明度、原生水平线性渐变、可编辑文字均经实际对象读回。其 100%、400%、800% 图片均已查看，manifest 为 passed。旧版 pm25_workflow 桌面渲染也通过，产生 27 个可编辑对象和 8 个文字框。

Acute Storm versus Chronic Siege 经新 Skill 的 scripts/render.py 完整重建，并由 tests/private_reconstruction_integration.py 再次从零生成。输入是从已完成 V2 原生对象提取的 FigureSpec 私有 fixture；执行阶段仅依赖新 Skill 的通用 renderer，没有调用旧项目临时 JSX。该测试证明通用 schema 和 renderer 可重建已有 clean geometry，不声称自动从陌生位图推断解剖结构。

最终读回：175 条 native paths，849 个锚点，26 个可编辑文字框，0 个 raster/placed objects，0 个 live plugin/Image Trace 对象。10 个 semantic groups 的数值 QC 均通过，无 tiny fragment、duplicate 或 raster 警告。

heart_acute：V1 1447 条路径、8770 个锚点；本轮 clean V2 replay 15 条路径、71 个锚点。

heart_chronic：V1 1896 条路径、11145 个锚点；本轮 clean V2 replay 21 条路径、82 个锚点。

heart_axis：V1 1137 条路径、6547 个锚点；本轮 clean V2 replay 14 条路径、66 个锚点。

三颗心脏合计：V1 为 4480 条路径、26462 个锚点；clean 版本为 50 条路径、219 个锚点。路径减少 98.88%，锚点减少 99.17%。V1 数值来自上一轮保存的 Illustrator 原生计数 baseline，clean 数值由本轮新文档重新读回。

liver_acute：10 条路径、55 个锚点，全部由新 Bézier renderer 直接生成。

liver_chronic：9 条路径、49 个锚点，全部由新 Bézier renderer 直接生成。

gut：20 条路径、120 个锚点，全部由新 Bézier renderer 直接生成。

flames：4 条路径、20 个锚点，全部由新 Bézier renderer 直接生成。

## 高倍检查与回归数据

已查看 1 张 100% 整图和 20 张 400%/800% 裁剪。三颗心脏轮廓和内部分区平滑，无可见 raster、tracing halo、像素状轮廓或被追踪成碎片的细小色差。肝脏、肠道和火焰同样未出现 tracing artifacts。原有肠道分段接缝与 axis heart 的左下房区缺口仍保留，属于已授权 V2 示意结构，并非新增描摹噪声。

第二次完整渲染的全部 21 张 QC 图片与第一轮已查看结果逐字节相同，因此记录了相同图像回归确认，没有把未查看的变化图像自动判为通过。具体观察保存在 visual QC manifest。

交付 AI：`outputs/private_regression_20260920_222812/reconstruction.ai`。预览：同目录 `reconstruction.png`。原生计数：`reconstruction.native.json`。数值 QC：`reconstruction.qc.json`。高倍检查：`reconstruction.visual_qc/manifest.json`。单元测试日志：`outputs/unit_tests_final.txt`。汇总：`outputs/validation_summary.json`。

## ExtendScript 依赖与限制

仍依赖 ExtendScript 的操作包括新建 Illustrator 文档、添加 PathItem/PathPoint/CompoundPathItem、字体与原生渐变赋值、按图层分组、原生对象读回、AI 保存、PNG export 和 imageCapture。Python 负责 schema、布局、分类、数值 QC、文件组织和测试。没有用 SVG rasterization 代替 Illustrator 原生路径。

当前渐变只保证对象范围内的水平线性填充，不支持任意角度、显式端点或径向渐变。复杂 clipping/mask、混合文字 runs、任意文字变换和通用图像语义识别仍未实现。新矢量元素接口使用 reconstruct mode；旧 create mode 继续处理自动布局的结构化节点。

数值 QC 使用 Bézier 采样近似面积，并且重复检测针对相同几何和样式，不涵盖所有反向或近似重叠路径。阈值是结合尺寸与复杂度的启发式判断。高倍视觉质量仍需 agent 或人工真实查看，代码不会把图像理解能力伪装成自动检测器。

本轮遇到一次读取未命名文档 fullName 导致的 Illustrator 无响应，已恢复测试会话。读取既有文件的接口现先按文件名匹配，再读取 fullName，且不关闭调用前已打开的匹配文档。原始 Skill、V1/V2 文件均未保存覆盖。
