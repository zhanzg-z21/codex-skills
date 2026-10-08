"""Public synthetic geometry; contains no user figure data."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from models.figure_spec import FigureSpec
from models.vector_spec import BezierPath, GradientFill, RasterEvidence, classify_reference
from illustrator.jsx_builder import JSXBuilder
from layout.base import compute_layout
from renderer.clean_vector_qc import analyze_semantic, clean_vector_qc
from renderer.visual_qc import CHECKS, record_visual_review


def path_data():
    return dict(id='shape',kind='bezier_path',classification='semantic_vector_illustration',semantic_type='organelle',
                group='icon',layer='ART',closed=True,fill='#CC5533',stroke='#332211',stroke_width=2,
                anchors=[{'anchor':{'x':0.15,'y':0.3},'point_type':'smooth',
                          'in_handle':{'x':0.15,'y':0.4},'out_handle':{'x':0.15,'y':0.2}},
                         {'anchor':{'x':0.45,'y':0.15}},
                         {'anchor':{'x':0.45,'y':0.45}}])


def make_spec(elements=None):
    return FigureSpec(schema_version='0.2',mode='reconstruct',figure_type='reference',
                      canvas={'width':600,'height':400,'margin':0},layout={'kind':'reference'},layers=['ART'],
                      groups=[{'id':'icon','layer':'ART','source_name':'synthetic_organelle','complexity':'simple'}],
                      elements=elements or [path_data()])


def gradient_data():
    return dict(type='linear',axis='horizontal',
                stops=[{'offset':0,'color':'#F7DB73'},{'offset':100,'color':'#BA3D51'}])


class VectorSchemaTests(unittest.TestCase):
    def test_schema_validation_and_roundtrip(self):
        s=make_spec(); self.assertEqual(FigureSpec.parse_raw(s.json()),s)
        invalid=path_data(); invalid['anchors'][0]['anchor']['x']=1.2
        with self.assertRaises(ValueError): BezierPath(**invalid)
        invalid=path_data(); invalid['opacity']=float('nan')
        with self.assertRaises(ValueError): BezierPath(**invalid)

    def test_closed_and_open(self):
        d=path_data(); d['anchors']=d['anchors'][:2]
        with self.assertRaises(ValueError): BezierPath(**d)
        d['closed']=False; self.assertFalse(BezierPath(**d).closed)

    def test_smooth_and_corner(self):
        d=path_data(); d['anchors'][0]['out_handle']['x']=0.2
        with self.assertRaises(ValueError): BezierPath(**d)
        d['anchors'][0]['point_type']='corner'; self.assertEqual(BezierPath(**d).anchors[0].point_type,'corner')

    def test_fill_stroke_preservation(self):
        d=path_data(); d.update(fill=None,opacity=35,stroke_width=2.75)
        e=BezierPath(**d).dict(); self.assertIsNone(e['fill']); self.assertEqual(e['stroke_width'],2.75)
        self.assertEqual(e['stroke'],'#332211'); self.assertEqual(e['opacity'],35)

    def test_gradient_definition(self):
        g=GradientFill(**gradient_data()); self.assertEqual(g.stops[-1].offset,100)
        d=gradient_data(); d['type']='radial'
        with self.assertRaises(ValueError): GradientFill(**d)
        d=gradient_data(); d['stops'].reverse()
        with self.assertRaises(ValueError): GradientFill(**d)

    def test_compound_and_stroke_schema(self):
        d=path_data(); c={k:d.pop(k) for k in ('closed','anchors')}; d.update(kind='compound_path',contours=[c,copy.deepcopy(c)])
        self.assertEqual(make_spec([d]).elements[0].kind,'compound_path')
        d=path_data(); d.update(kind='stroke_path',fill=None,closed=False)
        self.assertEqual(make_spec([d]).elements[0].kind,'stroke_path')
        d['fill']='#FFFFFF'
        with self.assertRaises(ValueError): make_spec([d])

    def test_group_cycles_rejected(self):
        d=json.loads(make_spec().json()); d['groups'][0]['parent']='icon'
        with self.assertRaises(ValueError): FigureSpec(**d)

    def test_raster_evidence_classification(self):
        for kind in ('microscopy','Western blot','histology','medical imaging','photograph'):
            self.assertEqual(classify_reference(kind),'irreducible_raster_evidence')
        r=dict(id='evidence',classification='irreducible_raster_evidence',semantic_type='histology',
               source='local.png',position={'x':0,'y':0},width=0.2,height=0.2,evidence_note='Unmodified measurement')
        self.assertEqual(RasterEvidence(**r).kind,'raster_evidence')
        r.update(classification='semantic_vector_illustration',semantic_type='organ')
        with self.assertRaises(ValueError): RasterEvidence(**r)

    def test_reference_classification_required(self):
        d=path_data(); d.pop('classification')
        with self.assertRaises(ValueError): BezierPath(**d)
        for kind in ('organ','cell','organelle','flame','molecule','biomedical icon','cartoon anatomical structure'):
            self.assertEqual(classify_reference(kind),'semantic_vector_illustration')


class RendererTests(unittest.TestCase):
    def test_bezier_serialization(self):
        d=path_data(); d['fill']=gradient_data(); scene=compute_layout(make_spec([d])); js=JSXBuilder.render_scene(scene)
        self.assertEqual(scene['elements'][0]['anchors'][0]['in_handle'],{'x':0.15,'y':0.4})
        for native in ('leftDirection','rightDirection','PointType.SMOOTH','PointType.CORNER','compoundPathItems.add','GradientType.LINEAR'):
            self.assertIn(native,js)
        self.assertNotIn('trace(',js); self.assertNotIn('rasterize(',js)


class QCTests(unittest.TestCase):
    def test_clean_vector_qc(self):
        qc=clean_vector_qc(make_spec()); self.assertTrue(qc['passed'])
        self.assertEqual(qc['semantic_illustrations']['synthetic_organelle']['anchor_point_count'],3)

    def test_duplicate_and_raster_warning(self):
        d=path_data(); q=analyze_semantic([d,d,{'native_type':'RasterItem'}],600,400)
        self.assertEqual(q['duplicate_object_count'],1); self.assertEqual(q['raster_object_count'],1)
        self.assertTrue(all('CLEAN_VECTOR_QC_WARNING' in w for w in q['warnings']))

    def test_density_relative_to_area_and_complexity(self):
        data=[]
        for i in range(90):
            d=path_data(); x=0.1+(i%10)*0.008; y=0.1+(i//10)*0.008
            d['anchors']=[{'anchor':{'x':x,'y':y}},{'anchor':{'x':x+0.003,'y':y}}, {'anchor':{'x':x,'y':y+0.003}}]
            data.append(d)
        self.assertTrue(analyze_semantic(data,600,400,'simple')['warnings'])
        spread=copy.deepcopy(data)
        for d in spread:
            for a in d['anchors']:
                a['anchor']['x']*=4; a['anchor']['y']*=4
        self.assertFalse(analyze_semantic(spread,600,400,'complex')['warnings'])

    def test_open_paths_are_counted_not_automatically_rejected(self):
        d=path_data(); d['closed']=False; q=analyze_semantic([d],600,400)
        self.assertEqual(q['open_path_count'],1); self.assertFalse(q['warnings'])

    def test_native_raster_contamination_is_counted(self):
        spec=make_spec(); actual=path_data(); actual.update(source_name='SCI_VECTOR_shape',group='native_group')
        snapshot={'objects':[actual,{'source_name':'unexpected','native_type':'RasterItem','kind':'unsupported','group':'native_group'}],
                  'groups':[{'id':'native_group','parent':None,'source_name':'SCI_VECTOR_GROUP_icon'}],
                  'total_raster_objects':1,'total_plugin_objects':0}
        qc=clean_vector_qc(spec,snapshot)
        self.assertFalse(qc['passed'])
        self.assertEqual(qc['semantic_illustrations']['synthetic_organelle']['raster_object_count'],1)

    def test_visual_gate_blocks_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); img=p/'preview.png'; img.write_bytes(b'test')
            manifest=p/'manifest.json'; manifest.write_text(json.dumps({'images':[{'path':str(img)}],'numeric_qc_passed':True}))
            with self.assertRaises(ValueError): record_visual_review(manifest,'reviewer',[])
            checks={k:False for k in CHECKS}; checks['tracing_halo']=True
            result=record_visual_review(manifest,'reviewer',[{'path':str(img),'checks':checks,'observation':'Visible halo'}])
            self.assertEqual(result['status'],'blocked_artifacts')


if __name__=='__main__':
    unittest.main()
