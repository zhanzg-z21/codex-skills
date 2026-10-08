# Codex Skills

这是一个个人 Codex skill 集合，保存可复用的科研写作、科研制图、PPT 和文献追踪工作流。

## 当前收录

`skills/` 下目前收录九个经过清理的技能：

* `academic-ppt-image-polisher`，张政署名的学术 PPT 配图技能。
* `artifact-template-medical-editorial-scientific-ppt`，医学期刊编辑风科研组会 PPT 模板技能。
* `biomedical-illustrator-agent`，Scientific Illustrator Agent 的本地生物医学改编版。
* `chinese-novelist`，中文长篇小说创作技能。
* `clinical-epi-biostat-expert-v02`，带知识库、来源索引和执行边界的临床流行病学与医学统计技能。
* `codex-ppt`，Codex PPT 的本地改编版。
* `comment-letter-scout`，医学期刊 comment letter 选题追踪技能。
* `lvdan-research-reasoning`，生物医学机制研究推理技能。
* `scientific-illustrator-agent`，Scientific Illustrator Agent 的本地技能副本。

原始目录中的虚拟环境、运行日志、生成结果、私有 fixtures、缓存文件和大型示例输出没有放入公开仓库。项目专属的 `scrna-hiri-targets` 和统计知识库也没有放入首个公开版本，避免把具体课题验收标准和来源材料直接公开。

## 使用方式

把本仓库克隆到本地后，将需要的技能目录复制到 Codex 的用户技能目录，或者放入项目的 `.agents/skills` 目录：

```powershell
git clone https://github.com/zhanzg-z21/codex-skills.git
Copy-Item .\codex-skills\skills\comment-letter-scout $HOME\.codex\skills\comment-letter-scout -Recurse
```

每个技能目录都以 `SKILL.md` 为入口。需要额外运行环境的技能会在自己的 README 或 `requirements.txt` 中说明。

## 归属说明

仓库中包含本地改编或保留原作者内容的技能。具体来源、署名和许可证见 [ATTRIBUTIONS.md](ATTRIBUTIONS.md)。

