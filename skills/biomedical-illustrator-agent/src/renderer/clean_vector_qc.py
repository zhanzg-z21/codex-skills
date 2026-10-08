"""Contextual vector diagnostics; visual inspection remains a separate gate."""
import json
import math
from collections import defaultdict

WARNING = 'CLEAN_VECTOR_QC_WARNING'


def contours(obj):
    return obj.get('contours', [obj]) if obj.get('kind') in ('bezier_path','stroke_path','compound_path') else []


def sampled_points(contour, width, height):
    anchors=contour['anchors']; points=[]
    pairs=list(zip(anchors, anchors[1:]))
    if contour['closed']:
        pairs.append((anchors[-1],anchors[0]))
    for a,b in pairs:
        p=[a['anchor'],a.get('out_handle') or a['anchor'],b.get('in_handle') or b['anchor'],b['anchor']]
        for step in range(17):
            t=step/16; u=1-t
            points.append((width*(u**3*p[0]['x']+3*u*u*t*p[1]['x']+3*u*t*t*p[2]['x']+t**3*p[3]['x']),
                           height*(u**3*p[0]['y']+3*u*u*t*p[1]['y']+3*u*t*t*p[2]['y']+t**3*p[3]['y'])))
    return points


def canonical_signature(obj):
    parts=[]
    for c in contours(obj):
        anchors=[tuple(round(a.get(k, a['anchor'])[axis] if a.get(k) else a['anchor'][axis],7)
                       for k in ('anchor','in_handle','out_handle') for axis in ('x','y')) for a in c['anchors']]
        if c['closed']:
            start=min(range(len(anchors)),key=lambda i:anchors[i])
            anchors=anchors[start:]+anchors[:start]
        parts.append((c['closed'],anchors))
    return json.dumps([parts,obj.get('fill'),obj.get('stroke'),obj.get('stroke_width'),obj.get('opacity',100)],sort_keys=True)


def analyze_semantic(objects, width, height, complexity='moderate'):
    paths=[]; all_points=[]; signatures=set(); duplicates=0
    for obj in objects:
        cs=contours(obj)
        if cs:
            sig=canonical_signature(obj)
            duplicates+=int(sig in signatures); signatures.add(sig)
        for c in cs:
            points=sampled_points(c,width,height); all_points.extend(points)
            xs,ys=zip(*points)
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2) if c['closed'] else 0
            paths.append({'anchors':len(c['anchors']), 'closed':c['closed'], 'area':area,
                          'bbox_area':(max(xs)-min(xs))*(max(ys)-min(ys)),
                          'diagonal':math.hypot(max(xs)-min(xs),max(ys)-min(ys))})
    if all_points:
        xs,ys=zip(*all_points); bbox=[min(xs),min(ys),max(xs),max(ys)]
    else:
        bbox=[0,0,0,0]
    bbox_area=max((bbox[2]-bbox[0])*(bbox[3]-bbox[1]),1)
    diagonal=math.hypot(bbox[2]-bbox[0],bbox[3]-bbox[1])
    # Relative silhouette scale and filled area distinguish fragments from long thin vessels.
    tiny=sum(p['closed'] and p['area'] < bbox_area*0.00015 and p['diagonal'] < diagonal*0.025 for p in paths)
    count=len(paths); anchors=sum(p['anchors'] for p in paths)
    size_factor=max(0.7,min(2.5,(bbox_area/10000)**0.25))
    complexity_factor={'simple':1,'moderate':2,'complex':5}[complexity]
    path_budget=32*complexity_factor*size_factor
    anchor_budget=240*complexity_factor*size_factor
    density=count/max(bbox_area/10000,0.25)
    raster=sum(o.get('native_type') in ('RasterItem','PlacedItem') or o.get('kind')=='raster_evidence' for o in objects)
    plugin=sum(o.get('native_type')=='PluginItem' for o in objects)
    warnings=[]
    if count > path_budget and (density>35*complexity_factor or tiny/max(count,1)>0.08):
        warnings.append('Path density exceeds the contextual budget; perform semantic reconstruction again')
    if anchors > anchor_budget and (anchors/max(count,1)>20 or count>path_budget):
        warnings.append('Excessive anchors relative to silhouette area and semantic complexity')
    if tiny>=4 and tiny/max(count,1)>0.08:
        warnings.append('Tiny fragment concentration suggests tracing noise')
    if duplicates:
        warnings.append('Duplicate painted geometry detected')
    if raster or plugin:
        warnings.append('Semantic illustration contains raster or live trace/plugin objects')
    return {'path_count':count,'anchor_point_count':anchors,'tiny_fragment_count':tiny,
            'raster_object_count':raster,'open_path_count':sum(not p['closed'] for p in paths),
            'duplicate_object_count':duplicates,'plugin_object_count':plugin,'bbox':bbox,
            'bbox_area':bbox_area,'summed_filled_area':sum(p['area'] for p in paths),
            'path_density_per_10000_pt2':density,'contextual_path_budget':path_budget,
            'contextual_anchor_budget':anchor_budget,'complexity':complexity,
            'warnings':[WARNING+': '+w for w in warnings]}


def clean_vector_qc(spec, snapshot=None):
    observed={o['source_name']:o for o in snapshot['objects']} if snapshot else {}
    groups={g.id:g for g in spec.groups}; buckets=defaultdict(list); warnings=[]
    for element in spec.elements:
        if element.classification!='semantic_vector_illustration':
            continue
        data=element.dict()
        if snapshot:
            actual=observed.get('SCI_VECTOR_'+element.id)
            if actual is None:
                warnings.append(WARNING+': missing native semantic object '+element.id)
                continue
            data=actual
        buckets[element.group or element.id].append(data)
    if snapshot:
        declared={'SCI_VECTOR_'+e.id for e in spec.elements}
        native_groups={g['id']:g for g in snapshot['groups']}
        for actual in snapshot['objects']:
            if actual['source_name'] in declared: continue
            parent=actual.get('group')
            while parent:
                group=native_groups[parent]
                prefix='SCI_VECTOR_GROUP_'
                semantic_group=group['source_name'][len(prefix):] if group['source_name'].startswith(prefix) else None
                if semantic_group in buckets:
                    buckets[semantic_group].append(actual)
                    warnings.append(WARNING+': undeclared native object in semantic group '+semantic_group)
                    break
                parent=group['parent']
        expected_rasters=sum(e.kind=='raster_evidence' for e in spec.elements)
        if snapshot['total_raster_objects']!=expected_rasters:
            warnings.append(WARNING+': native raster count differs from classified evidence count')
    metrics={}
    for key,items in buckets.items():
        group=groups.get(key); label=group.source_name or key if group else key
        metrics[label]=analyze_semantic(items,spec.canvas.width,spec.canvas.height,group.complexity if group else 'moderate')
        warnings.extend(label+': '+w for w in metrics[label]['warnings'])
    if snapshot and snapshot['total_plugin_objects']:
        warnings.append(WARNING+': document contains live plugin objects')
    return {'measurement':'Illustrator native read-back' if snapshot else 'schema preflight',
            'semantic_illustrations':metrics,'warnings':warnings,'passed':not warnings}
