# Academic PPT Image Polisher

学术PPT图像批量美化skill，调用GPT image 2 (gpt-image-1) 生成医学/学术配图。

## 快速开始

### 1. 把整个文件夹放到PPT同目录

```
D:\你的PPT文件夹\
├── 国自然答辩.pptx
├── academic-ppt-image-polisher\   ← 这个文件夹
│   ├── SKILL.md
│   ├── scripts\
│   ├── config\
│   └── assets\
```

### 2. 安装依赖

```powershell
pip install python-pptx openai Pillow
```

### 3. 设置API key

```powershell
$env:OPENAI_API_KEY="sk-..."
```

### 4. 启动Claude Code

```powershell
cd "D:\你的PPT文件夹"
claude --dangerously-skip-permissions
```

### 5. 让Codex执行

在Claude Code里说：

> 读取 academic-ppt-image-polisher/SKILL.md，按流程美化 国自然答辩.pptx

## 执行流程

Codex会按 SKILL.md 里的7步依次执行：

| Step | 脚本 | 说明 | 是否需要确认 |
|------|------|------|------|
| 0 | - | 环境检查 | 否 |
| 1 | `01_scan_placeholders.py` | 扫描占位符 | 否 |
| 2 | `02_classify.py` | 自动分类 | 否 |
| 3 | `04_generate_reference.py` | **生成3张风格基准图** | **是，必须确认风格** |
| 4 | `05_generate_images.py` | 批量生图 | 否 |
| 5 | `06_inject_to_pptx.py` | 回写PPT | 否 |
| 6 | `07_qa_visual.py` | 视觉检查 | 否 |

**最关键的是Step 3**：生成的3张reference图会决定后续所有图的画风。如果不满意，删除 `assets/reference_styles/` 下对应的PNG，重跑Step 3，调整prompt再生成。

## 5类占位符的处理策略

skill把占位符分5类，每类用不同的prompt策略：

| Category | 触发关键词 | 用途 |
|----------|-----------|------|
| `mechanism_diagram` | 通路、机制、信号、级联 | 信号通路图 |
| `data_chart_mockup` | 柱状图、曲线、ROC、热图 | 数据图示意 |
| `anatomical_organ` | 肝脏、心脏、器官、解剖 | 解剖示意 |
| `experiment_concept` | H&E、IF、WB、染色、流式 | 实验流程 |
| `infographic` | 地图、分布、流程图、时间线 | 信息图 |

## 自定义配色

修改 `config/style_tokens.json` 的 `colors` 字段，然后**删除reference图重跑Step 3**让新配色生效。

```json
{
  "colors": {
    "primary": "#你的主色",
    "primary_light": "#辅色",
    "accent": "#强调色"
  }
}
```

## 成本估算

| PPT规模 | 占位符数 | 总成本 |
|---------|---------|--------|
| 小（10页） | 5-8 | $2-3 |
| 中（20页） | 10-15 | $4-6 |
| 大（40页） | 20-30 | $8-12 |

价格基于 gpt-image-1 high quality $0.19/张 + 3张reference图。

## 已知限制

1. **GPT image 2不擅长生成精确数据图**。data_chart_mockup类只生成"示意性"图表，具体数字需要在生成后手动覆盖文本框。
2. **解剖位置可能出错**。即使prompt强约束"heart on left, liver on right"，仍有~10%概率画错。Step 6的QA环节必须人工把关。
3. **生成图里偶尔会出现乱码英文字符**。GPT image 2已知问题，无法完全避免。
4. **风格延续不是100%稳定**。即使用了reference image，约15-20%的图风格仍会偏离。可以单独重跑某个失败的占位符。

## 故障排查

### Step 1扫描结果为0
检查PPT里占位符文本框是否包含以下任一关键词：
- `[图片占位]`
- `[占位图]`
- `请提供...图`
- `TODO`

### Step 4 API调用全失败
- 检查 `OPENAI_API_KEY` 是否正确
- 检查网络代理（中国大陆需要VPN）
- 检查账户余额

### Step 5回写后图片错位
检查 `placeholders.json` 里bbox坐标是否正确。可能是原PPT的shape被Codex误判。

### 想单独重生成某张图
直接编辑 `placeholders.json` 只保留要重生的项，重跑 `05_generate_images.py`，然后跑 `06_inject_to_pptx.py`。

## 文件夹结构

```
academic-ppt-image-polisher/
├── SKILL.md                              # Codex入口文档
├── README.md                             # 本文件
├── scripts/
│   ├── 01_scan_placeholders.py           # 扫描
│   ├── 02_classify.py                    # 分类
│   ├── 04_generate_reference.py          # 生成基准图
│   ├── 05_generate_images.py             # 批量生图
│   ├── 06_inject_to_pptx.py              # 回写PPT
│   └── 07_qa_visual.py                   # 视觉QA
├── config/
│   ├── prompt_templates.json             # 5类prompt模板
│   └── style_tokens.json                 # 全局风格令牌
├── assets/
│   └── reference_styles/                 # 风格基准图（首次运行后生成）
└── generated/                            # 生成的图（运行后产生）
```

## 运行后产生的文件

- `placeholders.json` - 占位符元数据
- `assets/reference_styles/*.png` - 风格基准图
- `generated/slide{N}_shape{ID}.png` - 所有生成的图
- `<input>_polished.pptx` - 美化后的PPT
- `qa_output/slide-*.jpg` - QA截图
- `failed.json` - 失败记录（如果有）

## 关于这个skill的设计原则

1. **保留版式骨架**：永远不动文字、页码、导航栏、表格、callout数字
2. **只替换占位框**：所有"美化"操作只针对显式标记的占位符
3. **风格统一靠reference**：用 `images.edit` 端点而非 `images.generate`，所有图基于同一张基准图延续
4. **失败不中断**：单张失败记录到failed.json，其他正常处理
5. **可重入**：每一步都独立可重跑，generated/里已有的图不重复生成（手动删除后才重生）

## 联系

设计者: 张政（清华大学附属北京清华长庚医院 麻醉科）
用途: HIRI研究方向的学术PPT批量美化
