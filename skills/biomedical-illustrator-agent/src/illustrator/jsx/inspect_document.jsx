// Read actual native objects. Serialization does not depend on a JSON host global.
function inspectDocument(doc) {
    var previousSystem=app.coordinateSystem;
    try {
    app.coordinateSystem=CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
    var b=doc.artboards[0].artboardRect, w=b[2]-b[0], h=b[1]-b[3], serial=0;
    var result={width:w,height:h,layers:[],groups:[],objects:[],hidden_objects:0};
    function xy(p) {return {x:(p[0]-b[0])/w,y:(b[1]-p[1])/h};}
    function hex(c) {
        if (c.typename==='NoColor') return null;
        if (c.typename!=='RGBColor') throw new Error('Only explicit RGB supported: '+c.typename);
        function channel(v){return ('0'+Math.round(v).toString(16)).slice(-2);}
        return '#'+channel(c.red)+channel(c.green)+channel(c.blue);
    }
    function fill(c) {
        if (c.typename!=='GradientColor') return hex(c);
        if (c.gradient.type!==GradientType.LINEAR) throw new Error('Only linear gradients can be exported');
        var stops=[], m=c.matrix;
        if(Math.abs(m.mValueA-1)>0.00001 || Math.abs(m.mValueB)>0.00001 || Math.abs(m.mValueC)>0.00001 || Math.abs(m.mValueD-1)>0.00001 || Math.abs(m.mValueTX)>0.00001 || Math.abs(m.mValueTY)>0.00001 || Math.abs(c.angle)>0.00001)
            throw new Error('Transformed gradient is outside the stable horizontal gradient interface');
        for(var i=0;i<c.gradient.gradientStops.length;i++) {
            var s=c.gradient.gradientStops[i];
            stops.push({offset:s.rampPoint,color:hex(s.color),opacity:s.opacity,midpoint:s.midPoint});
        }
        return {type:'linear',axis:'horizontal',stops:stops};
    }
    function bounds(o) {var r=o.geometricBounds;return [(r[0]-b[0])/w,(b[1]-r[1])/h,(r[2]-b[0])/w,(b[1]-r[3])/h];}
    function path(o) {
        var anchors=[];
        for(var j=0;j<o.pathPoints.length;j++) {
            var p=o.pathPoints[j];
            anchors.push({anchor:xy(p.anchor),in_handle:xy(p.leftDirection),out_handle:xy(p.rightDirection),point_type:p.pointType===PointType.SMOOTH?'smooth':'corner'});
        }
        return {closed:o.closed,anchors:anchors};
    }
    function pathStyle(o,r) {
        r.fill=o.filled?fill(o.fillColor):null; r.stroke=o.stroked?hex(o.strokeColor):null;
        r.stroke_width=o.strokeWidth;
        r.stroke_cap=o.strokeCap===StrokeCap.BUTTENDCAP?'butt':(o.strokeCap===StrokeCap.PROJECTINGENDCAP?'projecting':'round');
        r.stroke_join=o.strokeJoin===StrokeJoin.MITERENDJOIN?'miter':(o.strokeJoin===StrokeJoin.BEVELENDJOIN?'bevel':'round');
        r.stroke_dashes=[];
        for(var i=0;i<o.strokeDashes.length;i++) r.stroke_dashes.push(o.strokeDashes[i]);
        r.fill_rule=o.evenodd?'evenodd':'nonzero';
    }
    function visit(container, group, layer) {
        var direct=[], items=container.pageItems, i;
        for(i=0;i<items.length;i++) if(items[i].parent===container) direct.push(items[i]);
        // Host collections are front to back. Spec z_order is back to front.
        for(i=direct.length-1;i>=0;i-=1) {
            var o=direct[i];
            if(o.hidden) {result.hidden_objects++;continue;}
            var id='e'+(++serial), z=direct.length-1-i;
            if(o.typename==='GroupItem') {
                result.groups.push({id:id,parent:group,layer:layer,z_order:z,source_name:o.name,clipped:o.clipped});
                visit(o,id,layer); continue;
            }
            var r={id:id,source_name:o.name,group:group,layer:layer,z_order:z,opacity:o.opacity,
                   native_type:o.typename,bounds:bounds(o)};
            if(o.typename==='PathItem') {
                r.kind=o.filled?'bezier_path':'stroke_path'; var p=path(o);
                r.closed=p.closed; r.anchors=p.anchors; pathStyle(o,r); r.area=Math.abs(o.area);
            } else if(o.typename==='CompoundPathItem') {
                r.kind='compound_path'; r.contours=[]; r.area=0;
                for(var k=o.pathItems.length-1;k>=0;k-=1) {r.contours.push(path(o.pathItems[k]));r.area+=Math.abs(o.pathItems[k].area);}
                pathStyle(o.pathItems[0],r);
            } else if(o.typename==='TextFrame') {
                var a=o.textRange.characterAttributes;
                r.kind='text'; r.text=o.contents.replace(/\r/g,'\n'); r.position=xy([o.left,o.top]);
                r.font=a.textFont.name; r.size=a.size; r.color=hex(a.fillColor);
                r.horizontal_scale=a.horizontalScale; r.vertical_scale=a.verticalScale;
                r.leading=a.autoLeading?null:a.leading; r.tracking=a.tracking;
                var ju=o.textRange.paragraphAttributes.justification;
                r.justification=ju===Justification.CENTER?'center':(ju===Justification.RIGHT?'right':'left');
            } else r.kind='unsupported';
            result.objects.push(r);
        }
    }
    for(var l=doc.layers.length-1;l>=0;l-=1) {
        var layer=doc.layers[l];
        if(!layer.visible) {result.hidden_objects+=layer.pageItems.length;continue;}
        result.layers.push(layer.name); visit(layer,null,layer.name);
    }
    result.total_raster_objects=doc.rasterItems.length+doc.placedItems.length;
    result.total_plugin_objects=doc.pluginItems.length;
    return result;
    } finally {app.coordinateSystem=previousSystem;}
}
function encodeNativeJSON(v) {
    if(v===null) return 'null';
    if(typeof v==='string') return '"'+v.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n').replace(/\t/g,'\\t').replace(/[\x00-\x1f]/g,function(c){return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4);})+'"';
    if(typeof v==='number' || typeof v==='boolean') return String(v);
    var a=[], k;
    if(v instanceof Array) {for(k=0;k<v.length;k++) a.push(encodeNativeJSON(v[k]));return '['+a.join(',')+']';}
    for(k in v) if(v.hasOwnProperty(k)) a.push(encodeNativeJSON(k)+':'+encodeNativeJSON(v[k]));
    return '{'+a.join(',')+'}';
}
