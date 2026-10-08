"""Normalized native vector elements, independent of any organ fixture."""
from typing import Literal, Optional, Union
import math
try:
    from pydantic.v1 import BaseModel, Field, root_validator, validator
except ImportError:
    from pydantic import BaseModel, Field, root_validator, validator


class VectorModel(BaseModel):
    class Config:
        extra = 'forbid'
        allow_inf_nan = False


STRUCTURED = {'text', 'rectangle', 'rounded_rectangle', 'ellipse', 'line', 'arrow', 'simple_connector'}
SEMANTIC = {'organ', 'cell', 'organelle', 'flame', 'molecule', 'biomedical_icon', 'cartoon_anatomical_structure'}
EVIDENCE = {'microscopy', 'western_blot', 'histology', 'medical_imaging', 'photograph'}


def classify_reference(kind: str) -> str:
    key = kind.lower().replace(' ', '_')
    for category, kinds in [('structured_geometry', STRUCTURED), ('semantic_vector_illustration', SEMANTIC),
                            ('irreducible_raster_evidence', EVIDENCE)]:
        if key in kinds:
            return category
    raise ValueError('Unclassified reference element: ' + kind)


def hex_color(value):
    if value is not None and (len(value) != 7 or value[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in value[1:])):
        raise ValueError('Expected #RRGGBB')
    return value


class XY(VectorModel):
    # Handles can extend outside the canvas; anchor bounds are validated separately.
    x: float
    y: float


class Anchor(VectorModel):
    anchor: XY
    in_handle: Optional[XY] = None
    out_handle: Optional[XY] = None
    point_type: Literal['smooth', 'corner'] = 'corner'

    @validator('anchor')
    def on_canvas(cls, p):
        if not (0 <= p.x <= 1 and 0 <= p.y <= 1):
            raise ValueError('Anchor must be normalized to [0, 1]')
        return p

    @root_validator(skip_on_failure=True)
    def smooth_tangents(cls, v):
        a, left, right = v['anchor'], v.get('in_handle'), v.get('out_handle')
        if v['point_type'] == 'smooth' and left and right:
            u, w = (left.x-a.x, left.y-a.y), (right.x-a.x, right.y-a.y)
            product = math.hypot(*u) * math.hypot(*w)
            if product > 1e-16 and (abs(u[0]*w[1]-u[1]*w[0])/product > 0.002 or u[0]*w[0]+u[1]*w[1] > 0):
                raise ValueError('Smooth handles must be opposite and collinear')
        return v


class GradientStop(VectorModel):
    offset: float = Field(ge=0, le=100)
    color: str
    opacity: float = Field(default=100, ge=0, le=100)
    midpoint: float = Field(default=50, ge=13, le=87)
    _color = validator('color', allow_reuse=True)(hex_color)


class GradientFill(VectorModel):
    type: Literal['linear'] = 'linear'
    axis: Literal['horizontal'] = 'horizontal'
    stops: list[GradientStop] = Field(min_items=2, max_items=64)

    @root_validator(skip_on_failure=True)
    def valid_gradient(cls, v):
        offsets = [s.offset for s in v['stops']]
        if offsets != sorted(offsets) or offsets[0] != 0 or offsets[-1] != 100:
            raise ValueError('Gradient stops must be sorted and span 0 to 100')
        return v


class ElementBase(VectorModel):
    id: str = Field(regex=r'^[A-Za-z][A-Za-z0-9_\-]{0,95}$')
    classification: Literal['structured_geometry', 'semantic_vector_illustration', 'irreducible_raster_evidence']
    semantic_type: str
    source_name: str = ''
    group: Optional[str] = None
    layer: str = 'BIOMED_ARTWORK'
    z_order: int = 0
    opacity: float = Field(default=100, ge=0, le=100)

    @root_validator(skip_on_failure=True)
    def classification_matches(cls, v):
        if classify_reference(v['semantic_type']) != v['classification']:
            raise ValueError('Classification disagrees with semantic_type')
        if v['classification']=='semantic_vector_illustration' and not v.get('group'):
            raise ValueError('Semantic paths require an illustration group for contextual QC')
        return v


class PathStyle(ElementBase):
    fill: Optional[Union[str, GradientFill]] = None
    stroke: Optional[str] = None
    stroke_width: float = Field(default=1, ge=0, le=100)
    stroke_cap: Literal['butt', 'round', 'projecting'] = 'round'
    stroke_join: Literal['miter', 'round', 'bevel'] = 'round'
    stroke_dashes: list[float] = Field(default_factory=list, max_items=12)
    fill_rule: Literal['nonzero', 'evenodd'] = 'nonzero'

    @validator('fill')
    def fill_color(cls, v):
        return hex_color(v) if isinstance(v, str) else v

    _stroke = validator('stroke', allow_reuse=True)(hex_color)

    @validator('stroke_dashes', each_item=True)
    def dash_positive(cls, v):
        if v < 0:
            raise ValueError('Dash length cannot be negative')
        return v

    @root_validator(skip_on_failure=True)
    def no_vectorized_evidence(cls, v):
        if v['classification'] == 'irreducible_raster_evidence':
            raise ValueError('Measured raster evidence must not be redrawn as vector data')
        return v


class Contour(VectorModel):
    closed: bool = True
    anchors: list[Anchor] = Field(min_items=2, max_items=20000)

    @root_validator(skip_on_failure=True)
    def closed_minimum(cls, v):
        if v['closed'] and len(v['anchors']) < 3:
            raise ValueError('Closed paths need at least three anchors')
        return v


class BezierPath(PathStyle, Contour):
    kind: Literal['bezier_path'] = 'bezier_path'


class StrokePath(PathStyle, Contour):
    kind: Literal['stroke_path'] = 'stroke_path'
    closed: bool = False
    fill: None = None
    stroke: str

    @root_validator(skip_on_failure=True)
    def visible_stroke(cls, v):
        if v['stroke_width'] <= 0:
            raise ValueError('stroke_path needs a positive stroke_width')
        return v


class CompoundPath(PathStyle):
    kind: Literal['compound_path'] = 'compound_path'
    contours: list[Contour] = Field(min_items=2, max_items=1000)


class VectorText(ElementBase):
    kind: Literal['text'] = 'text'
    text: str = Field(min_length=1, max_length=10000)
    position: XY
    font: str = 'ArialMT'
    size: float = Field(default=12, gt=0, le=1000)
    color: str = '#000000'
    horizontal_scale: float = Field(default=100, gt=0, le=1000)
    vertical_scale: float = Field(default=100, gt=0, le=1000)
    leading: Optional[float] = Field(default=None, gt=0)
    tracking: float = 0
    justification: Literal['left', 'center', 'right'] = 'left'
    _color = validator('color', allow_reuse=True)(hex_color)

    @root_validator(skip_on_failure=True)
    def text_category(cls, v):
        if v['semantic_type'] != 'text':
            raise ValueError('Text requires structured_geometry / text')
        return v


class RasterEvidence(ElementBase):
    kind: Literal['raster_evidence'] = 'raster_evidence'
    source: str
    position: XY
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
    evidence_note: str = Field(min_length=1)

    @root_validator(skip_on_failure=True)
    def evidence_only(cls, v):
        if v['classification'] != 'irreducible_raster_evidence':
            raise ValueError('Raster placement is reserved for scientific evidence')
        if v['position'].x < 0 or v['position'].y < 0 or v['position'].x+v['width'] > 1 or v['position'].y+v['height'] > 1:
            raise ValueError('Evidence must fit the normalized canvas')
        return v


class VectorGroup(VectorModel):
    id: str
    parent: Optional[str] = None
    layer: str
    z_order: int = 0
    source_name: str = ''
    complexity: Literal['simple', 'moderate', 'complex'] = 'moderate'
    complexity_note: str = ''

    @root_validator(skip_on_failure=True)
    def complex_justification(cls, v):
        if v['complexity'] == 'complex' and not v['complexity_note'].strip():
            raise ValueError('Complex illustrations require a scientific complexity explanation')
        return v


VectorElement = Union[BezierPath, StrokePath, CompoundPath, VectorText, RasterEvidence]
