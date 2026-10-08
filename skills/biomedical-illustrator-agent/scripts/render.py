"""Render one validated FigureSpec: python scripts/render.py spec.json result.ai"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from models.figure_spec import FigureSpec
from renderer.illustrator_renderer import render_figure_spec

if __name__=='__main__':
    if len(sys.argv)!=3:
        raise SystemExit(__doc__)
    spec=FigureSpec.parse_raw(Path(sys.argv[1]).read_text(encoding='utf-8'))
    print(json.dumps(render_figure_spec(spec,Path(sys.argv[2])),indent=2))
