---
name: academic-ppt-image-polisher
description: 批量美化学术PPT中的图片占位符，调用GPT image 2 (gpt-image-1) 生成视觉素材并回写到PPT。触发词：美化PPT、PPT配图、占位图生成、PPT图像优化、批量生图。适用于学术答辩、开题报告、基金申请类PPT。
version: 1.0
author: 张政 (Tsinghua Changgung Hospital)
---

# Academic PPT Image Polisher

## 用途

扫描学术PPT中所有"[图片占位]"标记的形状，调用GPT image 2批量生成与原PPT风格一致的医学/学术配图，按原坐标回写到PPT。保持版式、文字、页码、导航栏完全不变。

## 执行流程（Codex严格按顺序执行）

### Step 0: 环境检查

```bash
# 检查依赖
python -c "import pptx, openai, PIL; print('ok')"
# 若失败:
pip install python-pptx openai Pillow

# 检查API key
echo $env:OPENAI_API_KEY  # PowerShell
# 若空，提示用户设置: $env:OPENAI_API_KEY="sk-..."
```

### Step 1: 扫描占位符

```bash
python scripts/01_scan_placeholders.py <input.pptx>
```

输出 `placeholders.json`，包含每个占位符的slide_idx、shape_id、bbox、description。

### Step 2: 分类

```bash
python scripts/02_classify.py
```

按描述关键词将每个占位符归入5类之一：
- `mechanism_diagram` 机制通路图
- `data_chart_mockup` 数据图示意
- `anatomical_organ` 解剖器官图
- `experiment_concept` 实验示意
- `infographic` 信息图

### Step 3: 生成风格基准图（首次运行）

```bash
python scripts/04_generate_reference.py
```

生成3张reference图保存到 `assets/reference_styles/`。

**关键**：生成后必须停下，把reference图展示给用户确认风格。用户回复"满意"或"重新生成 <category>"。**用户未确认前不进入Step 4**。

如果 `assets/reference_styles/` 已有3张PNG，跳过本步。

### Step 4: 批量生成

```bash
python scripts/05_generate_images.py
```

对每个占位符调用 `client.images.edit()`（不是generate），传入对应category的reference图保证风格统一。失败重试3次。生成的图保存到 `generated/`。

### Step 5: 回写PPT

```bash
python scripts/06_inject_to_pptx.py <input.pptx>
```

按bbox坐标删除原占位符形状，在原位置插入生成的图片。输出 `<input>_polished.pptx`。

### Step 6: 视觉QA

```bash
python scripts/07_qa_visual.py <input>_polished.pptx
```

转PDF→截图，把slide-*.jpg展示给用户检查。

## 关键约束（不可违反）

1. **永远不要修改PPT的版式、文字内容、页码、导航栏、表格、数据callout**
2. **永远不要让GPT image 2生成包含具体数字、文字标签的图**（prompt里强制"no text, no numbers, no labels"）
3. **所有生图调用必须用 `images.edit` 端点 + reference image**，不要用 `images.generate`
4. **Step 3生成reference后必须暂停等用户确认**
5. **单次skill运行总API调用上限50张**，超过则警告用户
6. **失败不中断流程**，记录到 `failed.json` 继续处理其他占位符
7. **回写时如果generated/目录里找不到对应图片，跳过该占位符，原占位框保留不动**

## 成本预估

- gpt-image-1 high quality: ~$0.19/张
- gpt-image-1 medium quality: ~$0.07/张
- 典型18页学术PPT约8-12个占位符 + 3张reference ≈ $3-5/次

## 输入要求

PPT中的占位符文本框需要包含以下任一关键词：
- `[图片占位]`
- `[占位图]`
- `请提供...图`
- `[placeholder]`
- `TODO`

且文本框内应有简短描述，例如：
```
[图片占位]
图3a-b: 肝切除vs其他腹部大手术 MINS发生率柱状图
（标书 Fig 3）
```

## 输出文件

- `placeholders.json` 占位符元数据
- `assets/reference_styles/*.png` 风格基准图（首次生成后复用）
- `generated/slide{N}_shape{ID}.png` 生成的所有配图
- `<input>_polished.pptx` 美化后的PPT
- `failed.json` 失败记录（如果有）

## 故障排查

| 问题 | 排查 |
|------|------|
| API 401 | 检查 `OPENAI_API_KEY` |
| API 429 | 限流，脚本会自动指数退避重试 |
| 占位符扫描为空 | 检查PPT里是否有 `[图片占位]` 字样 |
| 生成图风格不统一 | 删除 `assets/reference_styles/` 重跑Step 3 |
| 回写后图片错位 | 检查 `placeholders.json` 的bbox字段，重跑Step 5 |
| 生成图里有乱码文字 | GPT image 2已知问题，prompt模板已加 "no text"，仍出现需手动遮挡 |

## Codex调用示例

用户在Claude Code里说：

> 读取这个文件夹下的SKILL.md，按流程美化 国自然答辩_HIRI_ATP_心脏焦亡.pptx

Codex应自动：
1. 读取SKILL.md
2. 执行Step 0环境检查
3. 执行Step 1-2扫描分类
4. 执行Step 3生成reference并**暂停等待用户确认**
5. 用户确认后执行Step 4-6
