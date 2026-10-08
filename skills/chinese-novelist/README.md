# 🎭 chinese-novelist skill

### AI辅助中文长篇小说创作系统

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://claude.com/claude-code)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 与同类工具的区别

| | 本skill | 批量生产型skill |
|--|---------|----------------|
| 创作理念 | 深度定制，迭代打磨 | 快速启动，批量产出 |
| 世界观构建 | 采访式深度对话，逐步挖掘 | 5个选择题 |
| 连贯性保证 | 悬念追踪表 + 进度追踪器 + 世界观圣经 | 章节摘要自动追踪 |
| 角色深度 | 四层塑造法（行为→动机→矛盾→弧线） | 性格标签 |
| Anti-AI | 具体禁用词表 + 结构性AI痕迹检查 | "确保文字自然流畅" |
| 适用场景 | 认真创作，想写出好作品 | 快速出稿，走量 |

---

## ✨ 核心特性

- **深度世界构建** - 采访式对话挖掘故事内核，不是5个选择题
- **悬念追踪系统** - 每个伏笔都有记录，不会烂尾
- **四层角色塑造** - 从外在行为到内在矛盾，角色有血有肉
- **18种章末钩子** - S/A/B三档，让读者停不下来
- **Anti-AI检查清单** - 具体到词、句式、结构层面的AI痕迹识别
- **质量自查机制** - 每章写完逐项检查，保证不掉链子

---

## 🚀 快速开始

```
帮我写一部小说
```

或者如果你已经有想法：

```
我想写一部关于[主题]的小说，[简述灵感/设定]，大约[X]章
```

AI会进入**采访模式**，通过对话逐步帮你构建世界观、角色、情节骨架，
然后生成一套完整的创作文件包，之后逐章创作。

---

## 📖 创作流程

```
阶段一：世界构建
  5轮深度采访 → 世界观圣经 + 人物档案 + 悬念追踪表

阶段二：逐章创作
  加载上下文 → 写本章 → 质量自查 → 更新进度 → 循环

阶段三：润色定稿
  Anti-AI检查 → 逐章精修 → 定稿
```

---

## 📁 输出结构

```
novels/
└── 你的小说名/
    ├── world-bible.md          # 世界观圣经
    ├── progress-tracker.md     # 进度追踪器
    ├── writing-prompt.md       # 写作系统提示词
    ├── 第01章-章名.md
    ├── 第02章-章名.md
    └── ...
```

---

## 📚 内置参考资料

| 文件 | 内容 |
|------|------|
| `world-bible-template.md` | 世界观圣经模板（公理层、势力、角色卡、悬念表） |
| `progress-tracker-template.md` | 进度追踪器模板 |
| `writing-prompt-template.md` | 写作系统提示词模板（含调整话术） |
| `quality-checklist.md` | 质量检查清单（必须通过 + 建议优化） |
| `hook-techniques.md` | 18种章末悬念钩子技巧（S/A/B三档） |
| `anti-ai-checklist.md` | Anti-AI写作检查清单 |
| `chapter-structure.md` | 章节结构设计指南（含10种开头技巧） |
| `dialogue-guide.md` | 对话写作指南 |
| `character-building.md` | 人物塑造方法（四层塑造法） |
| `plot-structures.md` | 情节结构模板（含伏笔管理） |

---

## 🛠️ 安装

将此目录放入 Claude Code 的 skills 目录：

```
~/.claude/skills/chinese-novelist/
```

---

## ⚖️ 许可

MIT
