"""Record inspected images: python scripts/review.py manifest.json reviews.json"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from renderer.visual_qc import record_visual_review

if __name__=='__main__':
    data=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    result=record_visual_review(sys.argv[1],data['reviewer'],data['reviews'])
    print(result['status'])
    if result['status']!='passed': raise SystemExit(1)
