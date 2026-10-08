"""Explicit desktop test, separate from portable unit-test discovery."""
import json
import sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tests'))
from test_clean_vectors import make_spec, path_data, gradient_data
from renderer.illustrator_renderer import render_figure_spec


def main():
    p=path_data(); p.update(fill=gradient_data(),opacity=75)
    line=path_data(); line.update(id='vessel',kind='stroke_path',closed=False,fill=None,stroke='#336699',opacity=90)
    for a in line['anchors']:
        for key in ('anchor','in_handle','out_handle'):
            if a.get(key): a[key]['x']+=0.4
    compound=path_data(); contour={k:compound.pop(k) for k in ('closed','anchors')}
    outer={'closed':True,'anchors':[{'anchor':{'x':x,'y':y}} for x,y in [(0.1,0.6),(0.4,0.6),(0.4,0.9),(0.1,0.9)]]}
    inner={'closed':True,'anchors':[{'anchor':{'x':x,'y':y}} for x,y in [(0.2,0.7),(0.3,0.7),(0.3,0.8),(0.2,0.8)]]}
    compound.update(id='membrane',kind='compound_path',contours=[outer,inner],fill_rule='evenodd',fill='#66AA88',opacity=100)
    text=dict(id='caption',kind='text',classification='structured_geometry',semantic_type='text',layer='ART',
              text='Native Bezier / compound / gradient',position={'x':0.48,'y':0.65},size=11)
    output=ROOT/'outputs'/('desktop_'+datetime.now().strftime('%Y%m%d_%H%M%S'))/'integration.ai'
    result=render_figure_spec(make_spec([p,line,compound,text]),output)
    (output.parent/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
