"""
Step 2: 按关键词将占位符分类到5类之一
读取 placeholders.json, 更新 category 字段
"""
import json
from pathlib import Path


def load_config():
    config_path = Path(__file__).parent.parent / "config" / "prompt_templates.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def classify_by_keywords(description: str, keywords_map: dict) -> str:
    """按关键词匹配分类"""
    desc_lower = description.lower()

    # 按优先级匹配（mechanism > data_chart > anatomy > experiment > infographic）
    priority_order = [
        "mechanism_diagram",
        "data_chart_mockup",
        "anatomical_organ",
        "experiment_concept",
        "infographic",
    ]

    matches = {}
    for category in priority_order:
        keywords = keywords_map.get(category, [])
        match_count = sum(1 for kw in keywords if kw.lower() in desc_lower)
        if match_count > 0:
            matches[category] = match_count

    if not matches:
        return "infographic"

    # 取匹配数最多的；并列时按priority_order取靠前的
    max_count = max(matches.values())
    for category in priority_order:
        if matches.get(category) == max_count:
            return category

    return "infographic"


def main():
    placeholders_path = Path("placeholders.json")
    if not placeholders_path.exists():
        print("错误: 未找到 placeholders.json, 请先运行 01_scan_placeholders.py")
        return

    placeholders = json.loads(placeholders_path.read_text(encoding="utf-8"))
    config = load_config()
    keywords_map = config["_classification_keywords"]

    print(f"分类 {len(placeholders)} 个占位符...")

    category_counts = {}
    for ph in placeholders:
        category = classify_by_keywords(ph["description"], keywords_map)
        ph["category"] = category
        category_counts[category] = category_counts.get(category, 0) + 1

        desc_preview = ph["description"][:40].replace("\n", " ")
        print(f"  Slide {ph['slide_idx']}: [{category}] {desc_preview}...")

    placeholders_path.write_text(
        json.dumps(placeholders, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n分类统计:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    print(f"\n更新完成: {placeholders_path.absolute()}")


if __name__ == "__main__":
    main()
