"""
Step 4: 批量调用 GPT image 2 生成所有占位符对应的图片
关键: 使用 images.edit 端点 + reference image 保证风格统一
"""
import os
import sys
import base64
import json
import time
from pathlib import Path
from openai import OpenAI


# category → reference图文件名映射
REFERENCE_MAP = {
    "mechanism_diagram": "mechanism_reference.png",
    "data_chart_mockup": "infographic_reference.png",
    "anatomical_organ": "anatomy_reference.png",
    "experiment_concept": "anatomy_reference.png",
    "infographic": "infographic_reference.png",
}


def load_templates():
    config_path = Path(__file__).parent.parent / "config" / "prompt_templates.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_settings():
    config_path = Path(__file__).parent.parent / "config" / "style_tokens.json"
    return json.loads(config_path.read_text(encoding="utf-8"))["api_settings"]


def determine_size(bbox: dict) -> str:
    """根据bbox长宽比决定输出尺寸"""
    w = bbox["width"]
    h = bbox["height"]
    if h == 0:
        return "1024x1024"
    ratio = w / h
    if ratio > 1.3:
        return "1536x1024"
    elif ratio < 0.77:
        return "1024x1536"
    else:
        return "1024x1024"


def generate_one(client, placeholder, templates, ref_dir, output_dir, settings):
    """生成单张图，带重试"""
    category = placeholder["category"]
    template = templates[category]
    ref_filename = REFERENCE_MAP[category]
    ref_path = ref_dir / ref_filename

    if not ref_path.exists():
        raise FileNotFoundError(f"reference图不存在: {ref_path}")

    description = placeholder["description"]
    prompt = template["prompt"].format(description=description)

    # 在原prompt前加上风格延续指令
    full_prompt = (
        "Maintain the EXACT same visual style as the reference image: "
        "same color palette, same line weight, same level of detail, "
        "same illustration aesthetic. "
        f"Generate the following content in that same style: {prompt}"
    )

    size = determine_size(placeholder["bbox"])
    quality = template.get("quality", settings["default_quality"])

    out_filename = f"slide{placeholder['slide_idx']}_shape{placeholder['shape_id']}.png"
    out_path = output_dir / out_filename

    print(f"  -> {out_filename}")
    print(f"     category: {category}, size: {size}, quality: {quality}")

    retry = settings["retry_attempts"]
    backoff = settings["retry_backoff_base"]
    last_error = None

    for attempt in range(retry):
        try:
            with open(ref_path, "rb") as ref_file:
                result = client.images.edit(
                    model="gpt-image-1",
                    image=ref_file,
                    prompt=full_prompt,
                    size=size,
                    quality=quality,
                )
            image_b64 = result.data[0].b64_json
            out_path.write_bytes(base64.b64decode(image_b64))
            print(f"     ✓ 成功")
            return True
        except Exception as e:
            last_error = str(e)
            wait = backoff ** attempt
            print(f"     第{attempt+1}次失败: {last_error[:80]}, 等待{wait}s重试")
            time.sleep(wait)

    print(f"     ✗ 最终失败")
    return False, last_error


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("错误: 未设置 OPENAI_API_KEY")
        sys.exit(1)

    placeholders_path = Path("placeholders.json")
    if not placeholders_path.exists():
        print("错误: 未找到 placeholders.json, 请先运行 01 和 02")
        sys.exit(1)

    placeholders = json.loads(placeholders_path.read_text(encoding="utf-8"))
    templates = load_templates()
    settings = load_settings()

    ref_dir = Path(__file__).parent.parent / "assets" / "reference_styles"
    if not list(ref_dir.glob("*.png")):
        print("错误: 未找到reference图, 请先运行 04_generate_reference.py")
        sys.exit(1)

    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)

    total = len(placeholders)
    max_total = settings["max_total_generations"]
    if total > max_total:
        print(f"警告: 占位符数量 {total} 超过上限 {max_total}")
        confirm = input("是否继续? (y/n): ")
        if confirm.lower() != "y":
            return

    print(f"开始批量生成 {total} 张图...")
    print(f"预估成本: 约 ${total * 0.19:.2f}\n")

    client = OpenAI()
    succeeded = 0
    failed = []

    for idx, ph in enumerate(placeholders, 1):
        print(f"[{idx}/{total}] Slide {ph['slide_idx']}: {ph['description'][:50]}...")

        if ph.get("category") is None:
            print(f"  跳过: category未分类")
            failed.append({"placeholder": ph, "error": "category is None"})
            continue

        try:
            result = generate_one(client, ph, templates, ref_dir, output_dir, settings)
            if result is True:
                succeeded += 1
            else:
                failed.append({"placeholder": ph, "error": result[1] if isinstance(result, tuple) else "unknown"})
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            failed.append({"placeholder": ph, "error": str(e)})

        print()

    print("=" * 50)
    print(f"完成: {succeeded}/{total} 成功")
    if failed:
        failed_path = Path("failed.json")
        failed_path.write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"失败 {len(failed)} 个, 详情见 {failed_path}")

    print("\n下一步: python scripts/06_inject_to_pptx.py <input.pptx>")


if __name__ == "__main__":
    main()
