"""Native previews and an explicit, evidence-backed visual completion gate."""
import json
from pathlib import Path
from illustrator.com_client import jsx_literal

CHECKS=('rough_edges','tracing_halo','pixel_like_contour','fragmented_colors','excessive_anchors','visible_raster')


def export_visual_qc(client, output, qc, width, height):
    directory=Path(output).with_suffix('.visual_qc'); directory.mkdir(exist_ok=False)
    files=[]
    for index,(name,metric) in enumerate(sorted(qc['semantic_illustrations'].items(),key=lambda pair:pair[1]['bbox_area'],reverse=True)):
        box=metric['bbox']; pad=max(3,0.04*max(box[2]-box[0],box[3]-box[1]))
        box=[max(0,box[0]-pad),max(0,box[1]-pad),min(width,box[2]+pad),min(height,box[3]+pad)]
        for scale in (400,800):
            path=directory/f'{index+1:02d}_{scale}.png'
            data={'path':path.as_posix(),'box':box,'resolution':72*scale/100}
            script='''(function(p){
                var doc=app.activeDocument,b=doc.artboards[0].artboardRect;
                var opt=new ImageCaptureOptions(); opt.resolution=p.resolution;
                opt.antiAliasing=true;opt.transparency=false;
                doc.imageCapture(new File(p.path),[b[0]+p.box[0],b[1]-p.box[1],b[0]+p.box[2],b[1]-p.box[3]],opt);
                return 'OK';
            })(DATA);'''.replace('DATA',jsx_literal(data))
            client.execute_jsx(script)
            if not path.is_file():
                raise RuntimeError('Missing visual QC image '+str(path))
            files.append({'illustration':name,'percent':scale,'path':str(path)})
    overview={'illustration':'full_figure','percent':100,'path':str(Path(output).with_suffix('.png'))}
    manifest={'status':'pending_visual_review','numeric_qc_passed':qc['passed'],
              'registry_path':str(Path(output).with_suffix('.registry.json')),
              'required_checks':CHECKS,'images':[overview]+files,'reviews':[]}
    path=directory/'manifest.json'; path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return str(path)


def record_visual_review(manifest_path, reviewer, reviews):
    """Call only after actually opening every requested preview and crop.

    Every review contains path, checked booleans (True means artifact present),
    and a specific observation. Any artifact keeps the result blocked.
    """
    path=Path(manifest_path); manifest=json.loads(path.read_text(encoding='utf-8'))
    expected={i['path'] for i in manifest['images']}
    if not reviewer.strip() or {r['path'] for r in reviews}!=expected or len(reviews)!=len(expected):
        raise ValueError('Every preview requires one named reviewer observation')
    for r in reviews:
        if set(r['checks'])!=set(CHECKS) or not all(type(v) is bool for v in r['checks'].values()) or not r['observation'].strip():
            raise ValueError('Review must explicitly assess every artifact category')
        if not Path(r['path']).is_file():
            raise ValueError('Reviewed image is missing')
    passed=manifest['numeric_qc_passed'] and not any(any(r['checks'].values()) for r in reviews)
    manifest.update(status='passed' if passed else 'blocked_artifacts',reviewer=reviewer,reviews=reviews)
    path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    registry=Path(manifest['registry_path']) if manifest.get('registry_path') else None
    if registry and registry.is_file():
        data=json.loads(registry.read_text(encoding='utf-8'))
        data['completion_status']=manifest['status']
        registry.write_text(json.dumps(data,indent=2),encoding='utf-8')
    return manifest
