// Generic native paths. No organ coordinates, tracing, SVG import or rasterization.
function renderVectors(scene, warnings) {
    var doc = app.activeDocument, board = doc.artboards[0].artboardRect;
    var groups = scene.groups || [], elements = scene.elements || [], layers = scene.layers.slice(0);
    var count = 0;
    function xy(p) { return [board[0]+p.x*scene.width, board[1]-p.y*scene.height]; }
    function rgb(hex) {
        var c = new RGBColor();
        c.red=parseInt(hex.substr(1,2),16); c.green=parseInt(hex.substr(3,2),16); c.blue=parseInt(hex.substr(5,2),16);
        return c;
    }
    function paint(fill, id) {
        if (typeof fill === 'string') return rgb(fill);
        var g=doc.gradients.add(); g.name='SCI_GRADIENT_'+id; g.type=GradientType.LINEAR;
        while (g.gradientStops.length<fill.stops.length) g.gradientStops.add();
        for (var i=0;i<fill.stops.length;i++) {
            var s=g.gradientStops[i], d=fill.stops[i];
            s.rampPoint=d.offset; s.color=rgb(d.color); s.opacity=d.opacity; s.midPoint=d.midpoint;
        }
        var c=new GradientColor(); c.gradient=g;
        return c;
    }
    function style(path, o) {
        path.filled=o.fill!==null;
        if (path.filled) path.fillColor=paint(o.fill,o.id);
        path.stroked=o.stroke!==null && o.stroke_width>0;
        if (path.stroked) {
            path.strokeColor=rgb(o.stroke); path.strokeWidth=o.stroke_width;
            path.strokeCap=o.stroke_cap==='butt'?StrokeCap.BUTTENDCAP:(o.stroke_cap==='projecting'?StrokeCap.PROJECTINGENDCAP:StrokeCap.ROUNDENDCAP);
            path.strokeJoin=o.stroke_join==='miter'?StrokeJoin.MITERENDJOIN:(o.stroke_join==='bevel'?StrokeJoin.BEVELENDJOIN:StrokeJoin.ROUNDENDJOIN);
            path.strokeDashes=o.stroke_dashes;
        }
        path.evenodd=o.fill_rule==='evenodd'; path.opacity=o.opacity;
    }
    function contour(parent, c, name) {
        var p=parent.pathItems.add(), points=[];
        for (var i=0;i<c.anchors.length;i++) points.push(xy(c.anchors[i].anchor));
        p.setEntirePath(points); p.name=name; p.closed=c.closed;
        for (var j=0;j<c.anchors.length;j++) {
            var a=c.anchors[j], pp=p.pathPoints[j];
            pp.anchor=xy(a.anchor);
            pp.leftDirection=xy(a.in_handle || a.anchor);
            pp.rightDirection=xy(a.out_handle || a.anchor);
            pp.pointType=a.point_type==='smooth'?PointType.SMOOTH:PointType.CORNER;
        }
        count++; return p;
    }
    function add(parent, o) {
        var item, name='SCI_VECTOR_'+o.id;
        if (o.kind==='text') {
            item=parent.textFrames.add(); item.name=name; item.contents=o.text.replace(/\r\n|\n/g,'\r');
            item.textRange.characterAttributes.size=o.size;
            item.textRange.characterAttributes.fillColor=rgb(o.color);
            try {item.textRange.characterAttributes.textFont=app.textFonts.getByName(o.font);}
            catch (e) {throw new Error('Required font unavailable: '+o.font);}
            item.textRange.characterAttributes.horizontalScale=o.horizontal_scale;
            item.textRange.characterAttributes.verticalScale=o.vertical_scale;
            item.textRange.characterAttributes.tracking=o.tracking;
            if (o.leading!==null) {
                item.textRange.characterAttributes.autoLeading=false;
                item.textRange.characterAttributes.leading=o.leading;
            }
            item.textRange.paragraphAttributes.justification=o.justification==='center'?Justification.CENTER:(o.justification==='right'?Justification.RIGHT:Justification.LEFT);
            app.redraw(); item.left=xy(o.position)[0]; item.top=xy(o.position)[1]; item.opacity=o.opacity;
            count++;
        } else if (o.kind==='raster_evidence') {
            item=parent.placedItems.add(); item.file=new File(o.source); item.name=name;
            item.width=o.width*scene.width; item.height=o.height*scene.height;
            item.position=xy(o.position); item.opacity=o.opacity; count++;
        } else if (o.kind==='compound_path') {
            item=parent.compoundPathItems.add(); item.name=name;
            var first=null;
            for (var i=0;i<o.contours.length;i++) {
                var child=contour(item,o.contours[i],name+'_contour'+i); if (!first) first=child;
            }
            style(first,o);
            item.opacity=o.opacity; count++;
        } else { item=contour(parent,o,name); style(item,o); }
        item.note='classification='+o.classification+';semantic_type='+o.semantic_type;
    }
    function children(parent, parentId, layerName) {
        var ordered=[], i;
        for (i=0;i<groups.length;i++) if ((groups[i].parent || null)===parentId && groups[i].layer===layerName) ordered.push({group:groups[i],z:groups[i].z_order});
        for (i=0;i<elements.length;i++) if ((elements[i].group || null)===parentId && elements[i].layer===layerName) ordered.push({element:elements[i],z:elements[i].z_order});
        ordered.sort(function(a,b){return a.z-b.z;});
        for (i=0;i<ordered.length;i++) {
            var o=ordered[i];
            if (o.group) {
                var g=parent.groupItems.add(); g.name='SCI_VECTOR_GROUP_'+o.group.id;
                children(g,o.group.id,layerName);
            } else add(parent,o.element);
        }
    }
    for (var e=0;e<elements.length;e++) {
        var found=false;
        for (var l=0;l<layers.length;l++) if (layers[l]===elements[e].layer) found=true;
        if (!found) layers.push(elements[e].layer);
    }
    for (var k=0;k<layers.length;k++) {
        var layer=doc.layers.add(); layer.name=layers[k]; children(layer,null,layers[k]);
    }
    app.redraw();
    return count;
}
