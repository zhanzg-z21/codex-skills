"""Read-back and fixture export using native Illustrator objects."""
import json
from pathlib import Path
from illustrator.com_client import jsx_literal
from models.figure_spec import FigureSpec
from models.vector_spec import classify_reference


def inspect_document(client, owned=True):
    script = (Path(__file__).parent / 'jsx' / 'inspect_document.jsx').read_text(encoding='utf-8')
    return json.loads(client.execute_jsx(script+'\nencodeNativeJSON(inspectDocument(app.activeDocument));', owned_document=owned))


def inspect_file(client, path):
    """Inspect an existing AI without saving it or adopting its document."""
    script = (Path(__file__).parent / 'jsx' / 'inspect_document.jsx').read_text(encoding='utf-8')
    script += '''\n(function(path){
        var file=new File(path),doc=null,opened=false;
        for(var i=0;i<app.documents.length;i++) {
            // Query fullName only for a matching named file, never an untitled test document.
            // A matching open document may have unsaved edits and must never be closed here.
            try {if(app.documents[i].name===decodeURI(file.name) && app.documents[i].fullName.fsName===file.fsName) doc=app.documents[i];} catch(e) {}
        }
        if(!doc) {doc=app.open(file);opened=true;}
        try {return encodeNativeJSON(inspectDocument(doc));}
        finally {if(opened) doc.close(SaveOptions.DONOTSAVECHANGES);}
    })(DATA);'''.replace('DATA',jsx_literal(Path(path).resolve().as_posix()))
    return json.loads(client.execute_jsx(script,owned_document=False))


def snapshot_to_spec(snapshot, classifications):
    """Convert clean authored native geometry to data with explicit group roles.

    classifications maps source group names to a supported semantic_type. Unknown
    artwork must be classified by the author, never inferred from its pixels.
    """
    groups = {g['id']: g for g in snapshot['groups']}
    elements = []
    for obj in snapshot['objects']:
        if obj['kind'] == 'unsupported':
            raise ValueError('Cannot export unsupported object: '+obj['source_name'])
        kind, current = None, obj.get('group')
        while current:
            group = groups[current]
            if group['source_name'] in classifications:
                kind = classifications[group['source_name']]
                break
            current = group['parent']
        if obj['kind'] == 'text':
            kind = 'text'
        if kind is None:
            kind = classifications.get(obj['source_name'])
        if kind is None:
            raise ValueError('Missing reference classification: '+obj['source_name'])
        data = {k:v for k,v in obj.items() if k not in ('native_type', 'bounds', 'area')}
        data.update(classification=classify_reference(kind), semantic_type=kind)
        # Numerical host roundoff is not authored off-canvas geometry.
        for contour in data.get('contours', [data]):
            for a in contour.get('anchors', []):
                for axis in ('x', 'y'):
                    value=a['anchor'][axis]
                    if -1e-8 < value < 1+1e-8:
                        a['anchor'][axis]=min(1,max(0,value))
        elements.append(data)
    clean_groups=[]
    for g in groups.values():
        if g['clipped']:
            raise ValueError('Clipping groups need explicit reconstruction')
        clean_groups.append({k:v for k,v in g.items() if k!='clipped'})
    return FigureSpec(schema_version='0.2', mode='reconstruct', figure_type='reference',
                      canvas={'width':snapshot['width'],'height':snapshot['height'],'margin':0},
                      layout={'kind':'reference'}, layers=snapshot['layers'], groups=clean_groups, elements=elements)
