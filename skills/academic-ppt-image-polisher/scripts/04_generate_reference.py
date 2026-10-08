"""
Step 3: 生成3张风格基准图，保存到 assets/reference_styles/
后续所有图都基于这些reference生成以保证风格统一

关键: 这一步用 images.generate (从0生成); 后续步骤用 images.edit (基于reference延续)
"""
import os
import base64
import json
from pathlib import Path
from openai import OpenAI


REFERENCE_SPECS = {
    "mechanism_reference.png": {
        "category": "mechanism_diagram",
        "prompt": (
            "Flat medical schematic illustration showing a signaling pathway: "
            "damaged liver releases ATP molecules into bloodstream, ATP travels "
            "through blood vessels to heart, binds to receptor on macrophage surface, "
            "triggers inflammasome assembly inside the cell. "
            "Style: scientific vector aesthetic, clean line work, "
            "labeled arrows showing causal flow between elements, "
            "isometric 3/4 perspective for organs and cells, "
            "color palette dominated by deep purple #6B2C8C with secondary lavender #A55EA0, "
            "white background, no shadows, no 3D rendering effects, "
            "BioRender-inspired educational style. "
            "CRITICAL: do not render any text, letters, numbers, or labels in the image. "
            "Anatomical positions correct: heart on left, liver on right under diaphragm."
        ),
        "size": "1536x1024",
    },
    "anatomy_reference.png": {
        "category": "anatomical_organ",
        "prompt": (
            "Stylized anatomical illustration of a human heart and liver shown together, "
            "isometric 3/4 view, cross-section visible showing internal architecture, "
            "color palette #6B2C8C primary with anatomically appropriate secondary tones "
            "(deep red for blood vessels, pink for muscle tissue), "
            "white background, educational textbook quality, clean vector line work. "
            "No text labels, no annotations, no leader lines. "
            "Anatomical accuracy is essential."
        ),
        "size": "1024x1024",
    },
    "infographic_reference.png": {
        "category": "infographic",
        "prompt": (
            "Flat modern infographic illustration showing a 4-step timeline with "
            "isometric icon elements, clean editorial design, "
            "color palette #6B2C8C primary, #A55EA0 secondary, #FFA94D accent on white background, "
            "suitable for academic presentation. "
            "No text in image, no numbers, no labels, just visual structure."
        ),
        "size": "1536x1024",
    },
}


def generate_reference(client: OpenAI, filename: str, spec: dict, output_dir: Path):
    """生成一张reference图"""
    print(f"生成 {filename} ...")
    print(f"  尺寸: {spec['size']}")
    print(f"  category: {spec['category']}")

    result = client.images.generate(
        model="gpt-image-1",
        prompt=spec["prompt"],
        size=spec["size"],
        quality="high",
        n=1,
    )

    image_b64 = result.data[0].b64_json
    out_path = output_dir / filename
    out_path.write_bytes(base64.b64decode(image_b64))
    print(f"  已保存: {out_path}")


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("错误: 未设置 OPENAI_API_KEY 环境变量")
        print("PowerShell: $env:OPENAI_API_KEY=\"sk-...\"")
        return

    output_dir = Path(__file__).parent.parent / "assets" / "reference_styles"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否已有reference, 询问是否覆盖
    existing = list(output_dir.glob("*.png"))
    if existing:
        print(f"已存在 {len(existing)} 张reference图:")
        for f in existing:
            print(f"  - {f.name}")
        print("\n如要重新生成, 请先删除 assets/reference_styles/ 下的PNG文件")
        print("跳过Step 3")
        return

    client = OpenAI()

    for filename, spec in REFERENCE_SPECS.items():
        try:
            generate_reference(client, filename, spec, output_dir)
        except Exception as e:
            print(f"  失败: {e}")
            continue

    print("\n" + "=" * 50)
    print("Reference图生成完毕")
    print("=" * 50)
    print(f"位置: {output_dir.absolute()}")
    print("\n下一步: 请打开这3张图查看风格")
    print("如满意, 继续 Step 4: python scripts/05_generate_images.py")
    print("如不满意, 删除对应PNG后重跑本脚本")


if __name__ == "__main__":
    main()
