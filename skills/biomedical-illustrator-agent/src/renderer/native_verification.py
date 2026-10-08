"""Compare actual native path geometry and paint with the validated input."""
import math


def verify_native_elements(spec, snapshot):
    found={o['source_name']:o for o in snapshot['objects']}
    def equal(a,b,label):
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            okay=math.isclose(a,b,rel_tol=1e-5,abs_tol=1e-5)
        elif isinstance(a,dict) and isinstance(b,dict):
            for key in a:
                equal(a[key],b.get(key),label+'.'+key)
            return
        elif isinstance(a,list) and isinstance(b,list):
            okay=len(a)==len(b)
            if okay:
                for x,y in zip(a,b): equal(x,y,label)
                return
        elif isinstance(a,str) and isinstance(b,str) and a.startswith('#'):
            okay=a.lower()==b.lower()
        else: okay=a==b
        if not okay:
            raise RuntimeError('Native preservation failed: '+label+' '+str(a)+' != '+str(b))
    for element in spec.elements:
        expected=element.dict(); actual=found.get('SCI_VECTOR_'+element.id)
        if actual is None:
            raise RuntimeError('Missing native object '+element.id)
        expected_type={'bezier_path':'PathItem','stroke_path':'PathItem','compound_path':'CompoundPathItem','text':'TextFrame','raster_evidence':'PlacedItem'}[element.kind]
        equal(expected_type,actual['native_type'],element.id+'.native_type')
        if element.kind in ('bezier_path','stroke_path','compound_path'):
            cs=expected.get('contours',[expected]); acs=actual.get('contours',[actual])
            equal(len(cs),len(acs),element.id+'.contours')
            for c,ac in zip(cs,acs):
                equal(c['closed'],ac['closed'],element.id+'.closed')
                for a in c['anchors']:
                    for key in ('in_handle','out_handle'):
                        if a[key] is None: a[key]=a['anchor']
                equal(c['anchors'],ac['anchors'],element.id+'.anchors')
            for key in ('fill','stroke','stroke_width','opacity','fill_rule','stroke_cap','stroke_join','stroke_dashes'):
                # A disabled stroke's width/cap/join is not painted and may be host-defaulted.
                if not expected['stroke'] and key.startswith('stroke_'): continue
                equal(expected[key],actual[key],element.id+'.'+key)
        elif element.kind=='text':
            for key in ('text','font','size','color','horizontal_scale','vertical_scale','leading','tracking','justification','position'):
                equal(expected[key],actual[key],element.id+'.'+key)
