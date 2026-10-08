"""
Step 6: 视觉QA - 转PDF + 截图，检查美化后的PPT是否有溢出/错位

Windows 环境需要安装 LibreOffice 和 poppler:
- LibreOffice: https://www.libreoffice.org/
- poppler for Windows: https://github.com/oschwartz10612/poppler-windows
将 soffice.exe 和 pdftoppm.exe 加入PATH
"""
import sys
import subprocess
import shutil
from pathlib import Path


def check_dependencies():
    """检查 soffice 和 pdftoppm 是否可用"""
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    pdftoppm = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")

    if not soffice:
        print("警告: 未找到 soffice (LibreOffice)")
        print("Windows下载: https://www.libreoffice.org/download/")
        return False, None, None

    if not pdftoppm:
        print("警告: 未找到 pdftoppm (poppler)")
        print("Windows下载: https://github.com/oschwartz10612/poppler-windows")
        return False, soffice, None

    return True, soffice, pdftoppm


def convert_to_images(pptx_path: str, output_dir: Path):
    """PPT → PDF → JPG"""
    ok, soffice, pdftoppm = check_dependencies()
    if not ok:
        print("\n替代方案: 手动用 PowerPoint 打开 polished.pptx 检查效果")
        return False

    output_dir.mkdir(exist_ok=True)

    print(f"PPT → PDF ...")
    pdf_path = output_dir / Path(pptx_path).with_suffix(".pdf").name
    subprocess.run([
        soffice, "--headless",
        "--convert-to", "pdf",
        "--outdir", str(output_dir),
        pptx_path
    ], check=True)

    if not pdf_path.exists():
        print(f"PDF转换失败: {pdf_path}")
        return False

    print(f"PDF → JPG ...")
    # 清理旧截图
    for old in output_dir.glob("slide-*.jpg"):
        old.unlink()

    subprocess.run([
        pdftoppm, "-jpeg", "-r", "150",
        str(pdf_path), str(output_dir / "slide")
    ], check=True)

    images = sorted(output_dir.glob("slide-*.jpg"))
    print(f"\n生成 {len(images)} 张截图:")
    for img in images:
        print(f"  {img.absolute()}")

    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python 07_qa_visual.py <polished.pptx>")
        sys.exit(1)

    pptx_path = sys.argv[1]
    if not Path(pptx_path).exists():
        print(f"错误: 文件不存在 {pptx_path}")
        sys.exit(1)

    output_dir = Path("qa_output")
    success = convert_to_images(pptx_path, output_dir)

    if success:
        print("\n" + "=" * 50)
        print("QA准备完毕")
        print("=" * 50)
        print(f"截图位置: {output_dir.absolute()}")
        print("\n下一步: 在Claude Code里说 '检查 qa_output/ 下所有slide-*.jpg 的视觉效果'")
        print("Claude会读取截图，检查以下问题:")
        print("  - 图片溢出占位框")
        print("  - 图片与其他元素重叠")
        print("  - 生成图里出现乱码文字")
        print("  - 配色与PPT主色不一致")
        print("  - 解剖位置错误")


if __name__ == "__main__":
    main()
