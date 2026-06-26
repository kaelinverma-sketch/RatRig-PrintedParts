from build123d import *
from ocp_vscode import show

from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
                                 BRepBuilderAPI_MakeFace)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer, TopExp
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCP.gp import gp_Pnt, gp_Vec, gp_Pln, gp_Ax3, gp_Dir
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
from OCP.GeomAPI import GeomAPI_PointsToBSpline, GeomAPI_Interpolate
from OCP.TColgp import TColgp_Array1OfPnt, TColgp_HArray1OfPnt
from OCP.GeomAbs import GeomAbs_C2

# ═══════════════════════════════════════════════════════════════
# MAIN BODY — non-convex profile extruded 150mm with chamfers
# ═══════════════════════════════════════════════════════════════

main_raw_points = [
    (-250.0, 185.0, 75.0),
    (-235.0, 200.0, 75.0),
    (235.0,  200.0, 75.0),
    (250.0,  185.0, 75.0),
    (250.0, -185.0, 75.0),
    (235.0, -200.0, 75.0),
    (215.0, -200.0, 75.0),
    (200.0, -185.0, 75.0),
    (200.0,   -0.0, 75.0),
    (90.0,    0.0,  75.0),
    (75.0,   15.0,  75.0),
    (75.0,  150.0,  75.0),
    (-75.0, 150.0,  75.0),
    (-75.0,  15.0,  75.0),
    (-90.0,   0.0,  75.0),
    (-200.0,  0.0,  75.0),
    (-200.0,-185.0, 75.0),
    (-215.0,-200.0, 75.0),
    (-235.0,-200.0, 75.0),
    (-250.0,-185.0, 75.0),
]

pts_2d = [(x, y) for x, y, _ in main_raw_points]

def make_wire_from_2d(pts):
    wire_builder = BRepBuilderAPI_MakeWire()
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        p0 = gp_Pnt(x0, y0, 0.0)
        p1 = gp_Pnt(x1, y1, 0.0)
        edge = BRepBuilderAPI_MakeEdge(p0, p1).Edge()
        wire_builder.Add(edge)
    wire_builder.Build()
    if not wire_builder.IsDone():
        raise RuntimeError("Wire construction failed")
    return wire_builder.Wire()

main_wire = make_wire_from_2d(pts_2d)
main_face_builder = BRepBuilderAPI_MakeFace(main_wire, True)
main_face_builder.Build()
if not main_face_builder.IsDone():
    raise RuntimeError(f"Main face failed: {main_face_builder.Error()}")
main_solid = BRepPrimAPI_MakePrism(main_face_builder.Face(), gp_Vec(0, 0, 150)).Shape()

# Chamfer helpers
TOLERANCE = 1e-3

def get_horizontal_face(shape, z_height):
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face_s(exp.Current())
        adaptor = BRepAdaptor_Surface(f)
        if adaptor.GetType() == GeomAbs_Plane:
            pln = adaptor.Plane()
            if (abs(pln.Axis().Direction().Z()) > 0.99 and
                    abs(pln.Location().Z() - z_height) < TOLERANCE):
                return f
        exp.Next()
    raise RuntimeError(f"Horizontal face at Z={z_height} not found")

def get_face_edges(ref_face):
    edges = []
    seen = set()
    exp = TopExp_Explorer(ref_face, TopAbs_EDGE)
    while exp.More():
        edge = TopoDS.Edge_s(exp.Current())
        vexp = TopExp_Explorer(edge, TopAbs_VERTEX)
        coords = []
        while vexp.More():
            v = TopoDS.Vertex_s(vexp.Current())
            pt = BRep_Tool.Pnt_s(v)
            coords.append((round(pt.X(), 4), round(pt.Y(), 4), round(pt.Z(), 4)))
            vexp.Next()
        key = frozenset(coords)
        if key not in seen:
            seen.add(key)
            edges.append(edge)
        exp.Next()
    return edges

top_face    = get_horizontal_face(main_solid, 150.0)
bottom_face = get_horizontal_face(main_solid, 0.0)

edge_face_map = TopTools_IndexedDataMapOfShapeListOfShape()
TopExp.MapShapesAndAncestors_s(main_solid, TopAbs_EDGE, TopAbs_FACE, edge_face_map)

chamfer = BRepFilletAPI_MakeChamfer(main_solid)
for edge in get_face_edges(top_face):
    chamfer.Add(3.0, 6.0, edge, top_face)
for edge in get_face_edges(bottom_face):
    chamfer.Add(3.0, 6.0, edge, bottom_face)
chamfer.Build()
if not chamfer.IsDone():
    raise RuntimeError("Chamfer failed")

main_body = Solid(chamfer.Shape())
print(f"Main body valid: {main_body.is_valid}")



# ═══════════════════════════════════════════════════════════════
# LOFT BODY — solid_a cut by solid_b, placed on YZ plane at X=250
# ═══════════════════════════════════════════════════════════════

from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopAbs import TopAbs_EDGE as _TopAbs_EDGE
from OCP.gp import gp_Trsf, gp_Ax1, gp_Dir as gp_Dir2, gp_Pnt as gp_Pnt2, gp_Vec as gp_Vec2
import math

loft1_pts = [
    (0.0,      37.807,   0.0),
    (10.59,    35.3513,  0.0),
    (18.1105,  28.3424,  0.0),
    (22.766,   17.1896,  0.0),
    (24.4543,  -0.5116,  0.0),
    (21.7428,  -21.8452, 0.0),
    (13.6085,  -34.3793, 0.0),
    (0.0,      -38.779,  0.0),
    (-17.0362, -31.0027, 0.0),
    (-24.4543,  -0.5116, 0.0),
    (-21.7428,  20.8731, 0.0),
    (-13.6085,  33.4072, 0.0),
]

loft2_pts = [
    (-0.0139,  39.8095,  2.0),
    (11.5265,  37.124,   2.0),
    (19.7926,  29.4297,  2.0),
    (24.714,   17.6511,  2.0),
    (26.4544,  -0.517,   2.0),
    (23.6521,  -22.4529, 2.0),
    (14.8709,  -35.9438, 2.0),
    (-0.0285,  -40.7838, 2.0),
    (-18.6563, -32.2141, 2.0),
    (-26.4545,  -0.5103, 2.0),
    (-23.6516,  21.4827, 2.0),
    (-14.8704,  34.9726, 2.0),
]

loft3_pts = [
    (-0.1023,  30.1842,  0.0),
    (10.6412,  24.0962,  0.0),
    (14.9898,  -0.5116,  0.0),
    (10.6412,  -25.0682, 0.0),
    (0.0,      -31.2074, 0.0),
    (-10.6924, -25.1194, 0.0),
    (-14.9898,  -0.5116, 0.0),
    (-10.2319,  24.8124, 0.0),
]

loft4_pts = [
    (-0.1275,  28.1679,  2.0),
    (8.9087,   23.0521,  2.0),
    (12.9897,  -0.5109,  2.0),
    (8.9053,  -24.0319,  2.0),
    (-0.0016, -29.1861,  2.0),
    (-8.957,  -24.078,   2.0),
    (-12.9897,  -0.5175, 2.0),
    (-8.516,   23.7386,  2.0),
]

from OCP.TColgp import TColgp_Array1OfPnt as _Arr1, TColgp_HArray1OfPnt as _HArr1
from OCP.GeomAPI import GeomAPI_PointsToBSpline as _PtsBspl, GeomAPI_Interpolate as _Interp
from OCP.GeomAbs import GeomAbs_C2 as _C2

def _make_wire_approx(pts):
    closed = pts + [pts[0]]
    arr = _Arr1(1, len(closed))
    for i, (x, y, z) in enumerate(closed):
        arr.SetValue(i + 1, gp_Pnt(x, y, z))
    fitter = _PtsBspl(arr, 3, 8, _C2, 1e-3)
    if not fitter.IsDone():
        raise RuntimeError("PointsToBSpline failed")
    edge = BRepBuilderAPI_MakeEdge(fitter.Curve()).Edge()
    wb = BRepBuilderAPI_MakeWire(edge)
    wb.Build()
    return wb.Wire()

def _make_wire_interp(pts):
    closed = pts + [pts[0]]
    arr = _HArr1(1, len(closed))
    for i, (x, y, z) in enumerate(closed):
        arr.SetValue(i + 1, gp_Pnt(x, y, z))
    interp = _Interp(arr, False, 1e-3)
    interp.Perform()
    if not interp.IsDone():
        raise RuntimeError("GeomAPI_Interpolate failed")
    edge = BRepBuilderAPI_MakeEdge(interp.Curve()).Edge()
    wb = BRepBuilderAPI_MakeWire(edge)
    wb.Build()
    return wb.Wire()

def _make_loft(w_bot, w_top, label):
    thru = BRepOffsetAPI_ThruSections(True, False, 1e-3)
    thru.AddWire(w_bot)
    thru.AddWire(w_top)
    thru.CheckCompatibility(False)
    thru.Build()
    if not thru.IsDone():
        raise RuntimeError(f"ThruSections failed: {label}")
    return Solid(thru.Shape())

def _fillet_top_bottom(solid, radius, z_top, z_bot, tol=0.5):
    fillet = BRepFilletAPI_MakeFillet(solid.wrapped)
    exp = TopExp_Explorer(solid.wrapped, _TopAbs_EDGE)
    count = 0
    while exp.More():
        edge = TopoDS.Edge_s(exp.Current())
        adaptor = BRepAdaptor_Curve(edge)
        p0 = adaptor.Value(adaptor.FirstParameter())
        p1 = adaptor.Value(adaptor.LastParameter())
        z0, z1 = p0.Z(), p1.Z()
        if (abs(z0 - z_top) < tol and abs(z1 - z_top) < tol) or \
           (abs(z0 - z_bot) < tol and abs(z1 - z_bot) < tol):
            fillet.Add(radius, edge)
            count += 1
        exp.Next()
    fillet.Build()
    if not fillet.IsDone():
        print("  Fillet failed — returning original")
        return solid
    return Solid(fillet.Shape())

# Build loft solids
solid_a = _make_loft(_make_wire_approx(loft1_pts), _make_wire_approx(loft2_pts), "Loft A")
solid_b = _make_loft(_make_wire_interp(loft3_pts), _make_wire_interp(loft4_pts), "Loft B")

# Fillet
solid_a = _fillet_top_bottom(solid_a, 1.0, z_top=2.0, z_bot=0.0)
solid_b = _fillet_top_bottom(solid_b, 1.0, z_top=2.0, z_bot=0.0)

# Cut B from A
cut_op = BRepAlgoAPI_Cut(solid_a.wrapped, solid_b.wrapped)
cut_op.SetFuzzyValue(0.01)
cut_op.Build()
if not cut_op.IsDone():
    raise RuntimeError("BRepAlgoAPI_Cut failed")
loft_result = Solid(cut_op.Shape())
print(f"Loft cut result valid: {loft_result.is_valid}")

# ── Place on YZ plane at X=250 ────────────────────────────────
trsf = gp_Trsf()
trsf.SetRotation(
    gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)),
    math.pi / 2
)
trsf_rotx = gp_Trsf()
trsf_rotx.SetRotation(
    gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)),
    math.pi / 2
)
trsf = trsf_rotx * trsf
trsf_translate = gp_Trsf()
trsf_translate.SetTranslation(gp_Vec(248, -29.64, 76.5))
trsf_combined = trsf_translate * trsf

loft_placed = BRepBuilderAPI_Transform(loft_result.wrapped, trsf_combined, True)
loft_placed.Build()
loft_body = Solid(loft_placed.Shape())
print(f"Loft body placed valid: {loft_body.is_valid}")

# ═══════════════════════════════════════════════════════════════
# EXTRUDE CUT — subtract loft_body from main_body
# ═══════════════════════════════════════════════════════════════

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut as _Cut

# First cut
cut_main = _Cut(main_body.wrapped, loft_body.wrapped)
cut_main.SetFuzzyValue(0.01)
cut_main.Build()
if not cut_main.IsDone():
    raise RuntimeError("Main body cut failed")

# Copy of loft_body moved +124.31 in Y
trsf_copy = gp_Trsf()
trsf_copy.SetTranslation(gp_Vec(0, 124.31, 0))
loft_copy_shape = BRepBuilderAPI_Transform(loft_body.wrapped, trsf_copy, True)
loft_copy_shape.Build()
loft_body_copy = Solid(loft_copy_shape.Shape())
print(f"Loft copy valid: {loft_body_copy.is_valid}")

# Second cut
cut_main2 = _Cut(Solid(cut_main.Shape()).wrapped, loft_body_copy.wrapped)
cut_main2.SetFuzzyValue(0.01)
cut_main2.Build()
if not cut_main2.IsDone():
    raise RuntimeError("Main body second cut failed")

final_body = Solid(cut_main2.Shape())
print(f"Final body valid: {final_body.is_valid}")

# ═══════════════════════════════════════════════════════════════
# NEW LOFT BODY — Loft_1 → Loft_2 (X=248 to X=250)
# ═══════════════════════════════════════════════════════════════

from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections as _ThruSec

new_loft1_pts = [
    (248.0, -84.7559,  38.3274),
    (248.0, -74.9331,  38.3274),
    (248.0, -74.9331, -12.4229),
    (248.0, -65.0014, -12.4229),
    (248.0, -65.0014, -21.9018),
    (248.0, -74.9331, -21.9018),
    (248.0, -74.9331, -38.0),
    (248.0, -85.7763, -38.0),
    (248.0, -85.7763, -21.9018),
    (248.0, -118.5184,-21.9018),
    (248.0, -118.5184,-11.0954),
]

new_loft2_pts = [
    (250.0, -85.8117,  40.3274),
    (250.0, -72.9331,  40.3274),
    (250.0, -72.9331, -10.4229),
    (250.0, -63.0014, -10.4229),
    (250.0, -63.0014, -23.9018),
    (250.0, -72.9331, -23.9018),
    (250.0, -72.9331, -40.0),
    (250.0, -87.7763, -40.0),
    (250.0, -87.7763, -23.9018),
    (250.0, -120.5184,-23.9018),
    (250.0, -120.5184,-10.4775),
]

def make_poly_wire_3d(pts):
    """Closed polygonal wire through 3D points (straight edges, no spline)."""
    wb = BRepBuilderAPI_MakeWire()
    n = len(pts)
    for i in range(n):
        p0 = gp_Pnt(*pts[i])
        p1 = gp_Pnt(*pts[(i + 1) % n])
        wb.Add(BRepBuilderAPI_MakeEdge(p0, p1).Edge())
    wb.Build()
    if not wb.IsDone():
        raise RuntimeError("Poly wire failed")
    return wb.Wire()

wire_l1 = make_poly_wire_3d(new_loft1_pts)
wire_l2 = make_poly_wire_3d(new_loft2_pts)

thru_new = _ThruSec(True, False, 1e-3)
thru_new.AddWire(wire_l1)
thru_new.AddWire(wire_l2)
thru_new.CheckCompatibility(False)
thru_new.Build()
if not thru_new.IsDone():
    raise RuntimeError("New ThruSections failed")

new_loft_body_raw = Solid(thru_new.Shape())
print(f"New loft body valid: {new_loft_body_raw.is_valid}")

trsf_loft_z = gp_Trsf()
trsf_loft_z.SetTranslation(gp_Vec(0, 0, 75))
loft_moved = BRepBuilderAPI_Transform(new_loft_body_raw.wrapped, trsf_loft_z, True)
loft_moved.Build()
new_loft_body = Solid(loft_moved.Shape())
print(f"New loft body moved valid: {new_loft_body.is_valid}")

# Cut new loft from final body
cut_new_loft = _Cut(final_body.wrapped, new_loft_body.wrapped)
cut_new_loft.SetFuzzyValue(0.01)
cut_new_loft.Build()
if not cut_new_loft.IsDone():
    raise RuntimeError("New loft cut failed")

final_body2 = Solid(cut_new_loft.Shape())
print(f"Final body 2 valid: {final_body2.is_valid}")

# ═══════════════════════════════════════════════════════════════
# LOFT 2 — 3-point profiles at X=248 and X=250, moved +75 in Z
# ═══════════════════════════════════════════════════════════════

loft2_l1_pts = [
    (248.0, -85.7763,  23.4734),
    (248.0, -85.7763, -12.4229),
    (248.0, -109.9221,-12.4229),
]

loft2_l2_pts = [
    (250.0, -87.7763,  16.9168),
    (250.0, -87.7763, -10.4229),
    (250.0, -106.1664,-10.4229),
]

wire_l2_1 = make_poly_wire_3d(loft2_l1_pts)
wire_l2_2 = make_poly_wire_3d(loft2_l2_pts)

thru_l2 = _ThruSec(True, False, 1e-3)
thru_l2.AddWire(wire_l2_1)
thru_l2.AddWire(wire_l2_2)
thru_l2.CheckCompatibility(False)
thru_l2.Build()
if not thru_l2.IsDone():
    raise RuntimeError("Loft 2 ThruSections failed")

loft2_raw = Solid(thru_l2.Shape())
print(f"Loft 2 raw valid: {loft2_raw.is_valid}")

trsf_l2 = gp_Trsf()
trsf_l2.SetTranslation(gp_Vec(0, 0, 75))
loft2_moved = BRepBuilderAPI_Transform(loft2_raw.wrapped, trsf_l2, True)
loft2_moved.Build()
loft2_body = Solid(loft2_moved.Shape())
print(f"Loft 2 body valid: {loft2_body.is_valid}")

# Copy of loft2_body moved +124.31 in Y
trsf_l2_copy = gp_Trsf()
trsf_l2_copy.SetTranslation(gp_Vec(0, 124.31, 0))
loft2_copy_shape = BRepBuilderAPI_Transform(loft2_body.wrapped, trsf_l2_copy, True)
loft2_copy_shape.Build()
loft2_body_copy = Solid(loft2_copy_shape.Shape())
print(f"Loft 2 copy valid: {loft2_body_copy.is_valid}")

# ═══════════════════════════════════════════════════════════════
# LOFT 3 — 11-point profiles at X=248 and X=250, moved +75 in Z
# ═══════════════════════════════════════════════════════════════

loft3_l1_pts = [
    (248.0, 39.5552,  38.3274),
    (248.0,  5.7926, -11.0954),
    (248.0,  5.7926, -21.9018),
    (248.0, 38.5348, -21.9018),
    (248.0, 38.5348, -38.0),
    (248.0, 49.3779, -38.0),
    (248.0, 49.3779, -21.9018),
    (248.0, 59.3097, -21.9018),
    (248.0, 59.3097, -12.4229),
    (248.0, 49.3779, -12.4229),
    (248.0, 49.3779,  38.3274),
]

loft3_l2_pts = [
    (250.0, 38.4993,  40.3274),
    (250.0,  3.7926, -10.4775),
    (250.0,  3.7926, -23.9018),
    (250.0, 36.5348, -23.9018),
    (250.0, 36.5348, -40.0),
    (250.0, 51.3779, -40.0),
    (250.0, 51.3779, -23.9018),
    (250.0, 61.3097, -23.9018),
    (250.0, 61.3097, -10.4229),
    (250.0, 51.3779, -10.4229),
    (250.0, 51.3779,  40.3274),
]

wire_l3_1 = make_poly_wire_3d(loft3_l1_pts)
wire_l3_2 = make_poly_wire_3d(loft3_l2_pts)

thru_l3 = _ThruSec(True, False, 1e-3)
thru_l3.AddWire(wire_l3_1)
thru_l3.AddWire(wire_l3_2)
thru_l3.CheckCompatibility(False)
thru_l3.Build()
if not thru_l3.IsDone():
    raise RuntimeError("Loft 3 ThruSections failed")

loft3_raw = Solid(thru_l3.Shape())
print(f"Loft 3 raw valid: {loft3_raw.is_valid}")

trsf_l3 = gp_Trsf()
trsf_l3.SetTranslation(gp_Vec(0, 0, 75))
loft3_moved = BRepBuilderAPI_Transform(loft3_raw.wrapped, trsf_l3, True)
loft3_moved.Build()
loft3_body = Solid(loft3_moved.Shape())
print(f"Loft 3 body valid: {loft3_body.is_valid}")

# Cut loft3_body from final_body2
cut_l3 = _Cut(final_body2.wrapped, loft3_body.wrapped)
cut_l3.SetFuzzyValue(0.01)
cut_l3.Build()
if not cut_l3.IsDone():
    raise RuntimeError("Loft 3 cut failed")

final_body3 = Solid(cut_l3.Shape())
print(f"Final body 3 valid: {final_body3.is_valid}")

# Fuse loft2_body and loft2_body_copy into final_body3
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse as _Fuse

fuse1 = _Fuse(final_body3.wrapped, loft2_body.wrapped)
fuse1.SetFuzzyValue(0.1)
fuse1.Build()
if not fuse1.IsDone():
    raise RuntimeError("Fuse loft2_body failed")

fuse2 = _Fuse(Solid(fuse1.Shape()).wrapped, loft2_body_copy.wrapped)
fuse2.SetFuzzyValue(0.1)
fuse2.Build()
if not fuse2.IsDone():
    raise RuntimeError("Fuse loft2_body_copy failed")

final_body4 = Solid(fuse2.Shape())
print(f"Final body 4 valid: {final_body4.is_valid}")

# ═══════════════════════════════════════════════════════════════
# LOFT 4 — 12-point profiles at Y=198 and Y=200, moved +75 in Z
# ═══════════════════════════════════════════════════════════════

loft4_l1_pts = [
    (126.0382, 198.0,  6.513),
    (126.0382, 198.0, 38.0),
    (138.191,  198.0, 38.0),
    (138.191,  198.0, -38.0),
    (126.0382, 198.0, -38.0),
    (126.0382, 198.0, -3.0205),
    (90.3875,  198.0, -3.0205),
    (90.3875,  198.0, -38.0),
    (78.2347,  198.0, -38.0),
    (78.2347,  198.0, 38.0),
    (90.3875,  198.0, 38.0),
    (90.3875,  198.0,  6.513),
]

loft4_l2_pts = [
    (124.0382, 200.0,  8.513),
    (124.0382, 200.0, 40.0),
    (140.191,  200.0, 40.0),
    (140.191,  200.0, -40.0),
    (124.0382, 200.0, -40.0),
    (124.0382, 200.0, -5.0205),
    (92.3875,  200.0, -5.0205),
    (92.3875,  200.0, -40.0),
    (76.2347,  200.0, -40.0),
    (76.2347,  200.0, 40.0),
    (92.3875,  200.0, 40.0),
    (92.3875,  200.0,  8.513),
]

wire_l4_1 = make_poly_wire_3d(loft4_l1_pts)
wire_l4_2 = make_poly_wire_3d(loft4_l2_pts)

thru_l4 = _ThruSec(True, False, 1e-3)
thru_l4.AddWire(wire_l4_1)
thru_l4.AddWire(wire_l4_2)
thru_l4.CheckCompatibility(False)
thru_l4.Build()
if not thru_l4.IsDone():
    raise RuntimeError("Loft 4 ThruSections failed")

loft4_raw = Solid(thru_l4.Shape())
print(f"Loft 4 raw valid: {loft4_raw.is_valid}")

trsf_l4 = gp_Trsf()
trsf_l4.SetTranslation(gp_Vec(0, 0, 75))
loft4_moved = BRepBuilderAPI_Transform(loft4_raw.wrapped, trsf_l4, True)
loft4_moved.Build()
loft4_body = Solid(loft4_moved.Shape())
print(f"Loft 4 body valid: {loft4_body.is_valid}")

# Cut loft4 from main body
cut_l4 = _Cut(final_body4.wrapped, loft4_body.wrapped)
cut_l4.SetFuzzyValue(0.01)
cut_l4.Build()
if not cut_l4.IsDone():
    raise RuntimeError("Loft 4 cut failed")

final_body5 = Solid(cut_l4.Shape())
print(f"Final body 5 valid: {final_body5.is_valid}")

# ═══════════════════════════════════════════════════════════════
# EXTRUDE CUT 1 — XZ profile at Y=199, extruded 2mm in +Y
# ═══════════════════════════════════════════════════════════════

extrude_pts = [
    (3.9402, 199.0, 15.9809), (4.4803, 199.0, 17.3907), (5.0433, 199.0, 18.6689),
    (5.7045, 199.0, 19.9146), (6.4966, 199.0, 21.0997), (7.4033, 199.0, 22.1859),
    (8.3835, 199.0, 23.1858), (9.3823, 199.0, 24.0905), (10.3551, 199.0, 24.9631),
    (11.2039, 199.0, 25.4563), (13.3541, 199.0, 26.6233), (14.4816, 199.0, 27.1414),
    (15.6502, 199.0, 27.5828), (16.856, 199.0, 27.9233), (18.0757, 199.0, 28.1648),
    (20.5221, 199.0, 28.4392), (22.6018, 199.0, 28.5598), (24.2368, 199.0, 28.4414),
    (26.4712, 199.0, 28.2312), (28.6923, 199.0, 27.9008), (30.8734, 199.0, 27.3763),
    (31.9393, 199.0, 27.0171), (32.979, 199.0, 26.5821), (33.9836, 199.0, 26.0761),
    (34.9551, 199.0, 25.5102), (36.8085, 199.0, 24.2423), (38.5725, 199.0, 22.859),
    (40.1775, 199.0, 21.5215), (41.1361, 199.0, 20.096), (42.4172, 199.0, 18.1121),
    (43.6049, 199.0, 16.0647), (44.6305, 199.0, 13.9265), (45.0612, 199.0, 12.8223),
    (45.4261, 199.0, 11.6949), (45.9672, 199.0, 9.3927), (46.3091, 199.0, 7.0516),
    (46.51, 199.0, 4.6897), (46.6257, 199.0, 2.3239), (46.6759, 199.0, 0.9302),
    (46.6152, 199.0, -0.9833), (46.4832, 199.0, -3.6918), (46.2346, 199.0, -6.3907),
    (45.7982, 199.0, -9.0594), (45.4866, 199.0, -10.3755), (45.0987, 199.0, -11.6729),
    (44.6321, 199.0, -12.9449), (44.0968, 199.0, -14.1908), (42.8619, 199.0, -16.6025),
    (41.4819, 199.0, -18.9282), (40.1151, 199.0, -21.0891), (38.8558, 199.0, -22.2169),
    (37.1643, 199.0, -23.6618), (35.3895, 199.0, -25.0069), (34.4584, 199.0, -25.6189),
    (33.4933, 199.0, -26.1764), (32.4907, 199.0, -26.6684), (31.4528, 199.0, -27.0849),
    (30.3927, 199.0, -27.4273), (29.3152, 199.0, -27.7054), (27.1251, 199.0, -28.1086),
    (24.9126, 199.0, -28.3714), (22.7715, 199.0, -28.5602), (21.9421, 199.0, -28.5161),
    (19.913, 199.0, -28.3738), (18.8892, 199.0, -28.263), (17.8631, 199.0, -28.1108),
    (15.8361, 199.0, -27.6577), (13.8763, 199.0, -27.0635), (12.2212, 199.0, -26.5007),
    (11.4661, 199.0, -26.1828), (9.3076, 199.0, -25.2316), (8.2354, 199.0, -24.7088),
    (7.1779, 199.0, -24.1386), (5.1523, 199.0, -22.8747), (2.8199, 199.0, -21.2558),
    (2.8199, 199.0, -9.5866), (21.3193, 199.0, -9.5866), (21.3193, 199.0, 1.8922),
    (-11.4966, 199.0, 1.8922), (-11.4966, 199.0, -28.5008), (-8.2441, 199.0, -31.0539),
    (-6.9687, 199.0, -31.9582), (-5.6652, 199.0, -32.7993), (-4.3205, 199.0, -33.5717),
    (-2.9316, 199.0, -34.2876), (-0.0488, 199.0, -35.6009), (2.5618, 199.0, -36.6896),
    (4.1117, 199.0, -37.2152), (8.0436, 199.0, -38.4621), (10.009, 199.0, -38.9912),
    (11.9721, 199.0, -39.4248), (13.9705, 199.0, -39.7534), (15.9905, 199.0, -39.989),
    (20.1031, 199.0, -40.2811), (21.7209, 199.0, -40.3631), (23.5781, 199.0, -40.2756),
    (26.1717, 199.0, -40.1184), (28.7246, 199.0, -39.8784), (31.2247, 199.0, -39.5086),
    (33.6624, 199.0, -38.9626), (36.0574, 199.0, -38.2154), (38.4335, 199.0, -37.3041),
    (40.8049, 199.0, -36.2781), (43.1114, 199.0, -35.2231), (44.5037, 199.0, -34.2889),
    (46.2859, 199.0, -33.0536), (47.9941, 199.0, -31.7772), (49.5974, 199.0, -30.4322),
    (51.0708, 199.0, -28.9872), (52.3986, 199.0, -27.4214), (53.6263, 199.0, -25.7254),
    (54.7786, 199.0, -23.9301), (55.885, 199.0, -22.0647), (56.7248, 199.0, -20.5989),
    (57.3902, 199.0, -18.9554), (58.3025, 199.0, -16.6189), (59.1328, 199.0, -14.2829),
    (59.8387, 199.0, -11.9385), (60.3813, 199.0, -9.5723), (60.7611, 199.0, -7.1582),
    (61.0169, 199.0, -4.6982), (61.3181, 199.0, 0.2738), (61.2261, 199.0, 2.1538),
    (61.0633, 199.0, 4.7806), (60.8187, 199.0, 7.3682), (60.4459, 199.0, 9.9048),
    (59.8992, 199.0, 12.3813), (59.1558, 199.0, 14.8184), (58.2534, 199.0, 17.2382),
    (57.2402, 199.0, 19.6534), (56.1983, 199.0, 22.0062), (55.2516, 199.0, 23.474),
    (54.0028, 199.0, 25.3483), (52.7096, 199.0, 27.1482), (51.3432, 199.0, 28.8422),
    (49.8752, 199.0, 30.4009), (48.2697, 199.0, 31.8232), (46.5346, 199.0, 33.1407),
    (44.6973, 199.0, 34.383), (42.7881, 199.0, 35.5796), (41.2963, 199.0, 36.4842),
    (39.8401, 199.0, 37.0753), (36.4188, 199.0, 38.3696), (34.7095, 199.0, 38.9167),
    (32.9911, 199.0, 39.3693), (31.251, 199.0, 39.7122), (29.4788, 199.0, 39.9584),
    (25.8519, 199.0, 40.241), (22.5925, 199.0, 40.3637), (20.5625, 199.0, 40.2941),
    (17.5065, 199.0, 40.1375), (14.5158, 199.0, 39.8511), (13.0522, 199.0, 39.6356),
    (11.6135, 199.0, 39.3597), (10.2021, 199.0, 39.0137), (8.8152, 199.0, 38.5866),
    (7.4466, 199.0, 38.0831), (6.0902, 199.0, 37.5111), (3.3942, 199.0, 36.1987),
    (-0.0947, 199.0, 34.2985), (-1.3031, 199.0, 33.194), (-3.0225, 199.0, 31.5597),
    (-4.6199, 199.0, 29.8842), (-6.0395, 199.0, 28.1348), (-6.6675, 199.0, 27.2208),
    (-7.2364, 199.0, 26.2723), (-8.2288, 199.0, 24.2576), (-9.0694, 199.0, 22.1113),
    (-9.8088, 199.0, 19.8672), (-10.1829, 199.0, 18.623),
]

def make_spline_wire_xz(pts):
    """Closed polygonal wire through XZ profile points (straight edges)."""
    wb = BRepBuilderAPI_MakeWire()
    n = len(pts)
    for i in range(n):
        p0 = gp_Pnt(*pts[i])
        p1 = gp_Pnt(*pts[(i + 1) % n])
        wb.Add(BRepBuilderAPI_MakeEdge(p0, p1).Edge())
    wb.Build()
    if not wb.IsDone():
        raise RuntimeError("Wire failed")
    return wb.Wire()

extrude_pts_moved = [(x, y - 1, z + 75) for x, y, z in extrude_pts]
extrude_wire = make_spline_wire_xz(extrude_pts_moved)

extrude_face_b = BRepBuilderAPI_MakeFace(extrude_wire, True)
extrude_face_b.Build()
if not extrude_face_b.IsDone():
    raise RuntimeError(f"Extrude face failed: {extrude_face_b.Error()}")

extrude_solid = BRepPrimAPI_MakePrism(extrude_face_b.Face(), gp_Vec(0, 2, 0))
extrude_solid.Build()
if not extrude_solid.IsDone():
    raise RuntimeError("Extrude prism failed")

extrude_body = Solid(extrude_solid.Shape())
print(f"Extrude body valid: {extrude_body.is_valid}")

# Cut extrude_body from main body
cut_ext1 = _Cut(final_body5.wrapped, extrude_body.wrapped)
cut_ext1.SetFuzzyValue(0.01)
cut_ext1.Build()
if not cut_ext1.IsDone():
    raise RuntimeError("Extrude cut 1 failed")

final_body6 = Solid(cut_ext1.Shape())
print(f"Final body 6 valid: {final_body6.is_valid}")

# ═══════════════════════════════════════════════════════════════
# EXTRUDE CUT 2 — XZ profile at Y=199, 2mm in +Y
# FIX: three out-of-order points corrected (swap 59/60, remove 87, swap 111/112)
# ═══════════════════════════════════════════════════════════════

extrude2_pts = [
    (-135.6439, 199.0, 37.9086), (-96.9272, 199.0, 37.9086), (-89.4163, 199.0, -1.8883),
    (-100.3381, 199.0, -3.4691), (-100.9638, 199.0, -2.8657), (-101.7734, 199.0, -2.1077),
    (-102.6957, 199.0, -1.3037), (-103.6627, 199.0, -0.5481), (-104.6862, 199.0, 0.1368),
    (-105.7775, 199.0, 0.7269), (-106.9254, 199.0, 1.1962), (-108.107, 199.0, 1.5557),
    (-109.3036, 199.0, 1.8274), (-110.506, 199.0, 2.0374), (-111.6423, 199.0, 2.1964),
    (-112.5004, 199.0, 2.3152), (-113.1599, 199.0, 2.2573), (-114.3442, 199.0, 2.1387),
    (-115.2975, 199.0, 2.0), (-116.2518, 199.0, 1.8), (-117.1964, 199.0, 1.5137),
    (-118.1149, 199.0, 1.119), (-118.9738, 199.0, 0.6282), (-119.7752, 199.0, 0.0702),
    (-121.2488, 199.0, -1.1493), (-121.8864, 199.0, -1.7189), (-122.3066, 199.0, -2.3763),
    (-123.3203, 199.0, -4.0322), (-123.9963, 199.0, -5.3271), (-124.5529, 199.0, -6.6942),
    (-124.9429, 199.0, -8.116), (-125.1832, 199.0, -9.5566), (-125.3182, 199.0, -11.0005),
    (-125.389, 199.0, -12.4364), (-125.4206, 199.0, -13.4224), (-125.3477, 199.0, -15.5442),
    (-125.1227, 199.0, -18.0267), (-124.9012, 199.0, -19.2636), (-124.5748, 199.0, -20.4865),
    (-124.1335, 199.0, -21.6745), (-123.6026, 199.0, -22.8177), (-122.3873, 199.0, -24.9767),
    (-121.8812, 199.0, -25.8099), (-121.4239, 199.0, -26.2578), (-120.3009, 199.0, -27.3139),
    (-119.3855, 199.0, -28.0616), (-118.3826, 199.0, -28.7229), (-117.2797, 199.0, -29.2444),
    (-116.1305, 199.0, -29.6003), (-114.9727, 199.0, -29.8341), (-113.823, 199.0, -29.9938),
    (-112.968, 199.0, -30.0914), (-112.41, 199.0, -30.0355), (-111.0386, 199.0, -29.8715),
    (-109.999, 199.0, -29.6778), (-108.9617, 199.0, -29.3809), (-107.9579, 199.0, -28.9502),
    (-107.0305, 199.0, -28.4145), (-106.1674, 199.0, -27.8154), (-104.8402, 199.0, -26.779),
    (-105.3519, 199.0, -27.1876), (-103.472, 199.0, -25.1264), (-102.7974, 199.0, -24.193),
    (-102.1956, 199.0, -23.1897), (-101.7071, 199.0, -22.1182), (-101.3377, 199.0, -21.0179),
    (-101.055, 199.0, -19.9085), (-100.8601, 199.0, -18.9331), (-87.595, 199.0, -20.307),
    (-88.023, 199.0, -22.2439), (-88.4483, 199.0, -23.8853), (-88.9469, 199.0, -25.4651),
    (-89.5441, 199.0, -26.9693), (-90.2665, 199.0, -28.3873), (-91.1336, 199.0, -29.7405),
    (-92.1268, 199.0, -31.0499), (-93.2212, 199.0, -32.3319), (-94.3863, 199.0, -33.5992),
    (-95.3815, 199.0, -34.6463), (-98.0028, 199.0, -36.3648), (-100.0395, 199.0, -37.5634),
    (-102.103, 199.0, -38.5596), (-103.1562, 199.0, -38.9622), (-104.2321, 199.0, -39.294),
    (-106.4707, 199.0, -39.78), (-111.2178, 199.0, -40.2709), (-112.7771, 199.0, -40.3616),
    (-108.8076, 199.0, -40.0836), (-115.2547, 199.0, -40.1145), (-117.7486, 199.0, -39.7998),
    (-120.1503, 199.0, -39.3636), (-122.4269, 199.0, -38.7469), (-123.5092, 199.0, -38.3538),
    (-124.545, 199.0, -37.8974), (-125.5528, 199.0, -37.3618), (-126.5271, 199.0, -36.7545),
    (-128.4066, 199.0, -35.3432), (-129.3196, 199.0, -34.5529), (-130.2188, 199.0, -33.7169),
    (-131.5387, 199.0, -32.4052), (-132.8557, 199.0, -31.0278), (-133.664, 199.0, -30.1659),
    (-134.7536, 199.0, -28.3999), (-135.8299, 199.0, -26.5558), (-136.7901, 199.0, -24.7017),
    (-137.5863, 199.0, -22.8227), (-138.1805, 199.0, -20.8936), (-138.5957, 199.0, -18.8811),
    (-138.8781, 199.0, -16.797), (-139.0753, 199.0, -14.6584), (-139.1886, 199.0, -13.1482),
    (-138.7012, 199.0, -7.7651), (-138.925, 199.0, -9.6923), (-138.3816, 199.0, -5.8962),
    (-137.9343, 199.0, -4.0987), (-137.3264, 199.0, -2.3817), (-136.5373, 199.0, -0.7237),
    (-135.5919, 199.0, 0.8977), (-134.5222, 199.0, 2.4989), (-133.3671, 199.0, 4.0907),
    (-132.3624, 199.0, 5.4252), (-129.8085, 199.0, 7.5886), (-127.9712, 199.0, 8.9758),
    (-126.0863, 199.0, 10.1484), (-125.1171, 199.0, 10.6326), (-124.1206, 199.0, 11.0405),
    (-123.0848, 199.0, 11.3805), (-120.9068, 199.0, 11.8916), (-119.7722, 199.0, 12.0799),
    (-117.4347, 199.0, 12.3678), (-115.7826, 199.0, 12.5304), (-113.6208, 199.0, 12.3694),
    (-111.4752, 199.0, 12.0775), (-110.4452, 199.0, 11.8462), (-109.4257, 199.0, 11.543),
    (-107.3802, 199.0, 10.7683), (-105.6741, 199.0, 10.0316), (-104.0103, 199.0, 9.3005),
    (-106.8829, 199.0, 25.5566), (-135.6439, 199.0, 25.5566),
]

# ── Fix 1: swap idx 59 ↔ 60 (inner arc backtrack near -105, -27) ──
extrude2_pts[59], extrude2_pts[60] = extrude2_pts[60], extrude2_pts[59]

# ── Fix 2: remove idx 87 (stray backtrack point at bottom arc near -108, -40) ──
extrude2_pts.pop(87)
# List is now 139 points; indices 88+ shifted down by 1

# ── Fix 3: swap idx 110 ↔ 111 (Z monotone break near -139, -9.7) ──
# Original idx 111/112 are now at 110/111 after the pop above
extrude2_pts[110], extrude2_pts[111] = extrude2_pts[111], extrude2_pts[110]

# Reorder: list is now 139 pts (indices 0..138)
extrude2_pts_reordered = (
    [extrude2_pts[0]]
    + [extrude2_pts[138]]
    + [extrude2_pts[137]]
    + list(reversed(extrude2_pts[2:137]))
    + [extrude2_pts[1]]
)

# Offset: +75 Z, +1 Y
extrude2_pts_moved = [(x, y - 1, z + 75) for x, y, z in extrude2_pts_reordered]
extrude2_wire = make_spline_wire_xz(extrude2_pts_moved)

extrude2_face_b = BRepBuilderAPI_MakeFace(extrude2_wire, True)
extrude2_face_b.Build()
if not extrude2_face_b.IsDone():
    raise RuntimeError(f"Extrude2 face failed: {extrude2_face_b.Error()}")

extrude2_solid = BRepPrimAPI_MakePrism(extrude2_face_b.Face(), gp_Vec(0, 2, 0))
extrude2_solid.Build()
if not extrude2_solid.IsDone():
    raise RuntimeError("Extrude2 prism failed")

extrude2_body = Solid(extrude2_solid.Shape())
print(f"Extrude2 body valid: {extrude2_body.is_valid}")

# Cut extrude2_body from main body
cut_ext2 = _Cut(final_body6.wrapped, extrude2_body.wrapped)
cut_ext2.SetFuzzyValue(0.01)
cut_ext2.Build()
if not cut_ext2.IsDone():
    raise RuntimeError("Extrude cut 2 failed")

final_body7 = Solid(cut_ext2.Shape())
print(f"Final body 7 valid: {final_body7.is_valid}")

show(final_body7,
     names=["Final Body"],
     port=3940)

# ═══════════════════════════════════════════════════════════════
# LOFT 5 — 25-pt / 23-pt profiles at Y=198 and Y=200, moved +75 in Z
# Loft2 reversed to match Loft1 CCW winding
# ═══════════════════════════════════════════════════════════════

# Loft1 restarted at idx 15 (top-left corner X=-61.25, Z=38.33)
# to align with Loft2_rev idx 0 (top-left corner X=-63.25, Z=40.33)
_loft5_l1_raw = [
    (-30.1037, 198.0, 9.0911), (-30.1037, 198.0, 18.7406), (-33.3663, 198.0, 20.1718),
    (-34.9913, 198.0, 20.9911), (-36.5766, 198.0, 21.8975), (-38.1005, 198.0, 22.8712),
    (-39.5714, 198.0, 23.8883), (-42.4012, 198.0, 25.972), (-45.2959, 198.0, 28.5477),
    (-46.7077, 198.0, 29.9449), (-48.0455, 198.0, 31.4555), (-49.2602, 198.0, 33.0971),
    (-50.316, 198.0, 34.8185), (-51.2433, 198.0, 36.5717), (-52.0852, 198.0, 38.3274),
    (-61.2469, 198.0, 38.3274), (-61.2469, 198.0, -38.0), (-49.9127, 198.0, -38.0),
    (-49.9127, 198.0, 22.0597), (-45.1939, 198.0, 18.1277), (-42.8451, 198.0, 16.233),
    (-40.4795, 198.0, 14.4615), (-38.0617, 198.0, 12.8685), (-35.5383, 198.0, 11.4794),
    (-32.8755, 198.0, 10.238),
]
loft5_l1_pts = _loft5_l1_raw[15:] + _loft5_l1_raw[:15]

# Loft2 reversed to match CCW winding and align start to top-left corner.
# Y=200.1 (proud of body face by 0.1mm) to avoid coincident-face boolean failure.
# 2 interpolated points added (idx 9 and 23) to match L1's 25-pt count so
# ThruSections maps vertices 1:1 with no twist.
loft5_l2_pts = [
    (-63.2469, 200.1, 40.3274),   # [0]  top-left
    (-63.2469, 200.1, -40.0),     # [1]  bot-left
    (-47.9127, 200.1, -40.0),     # [2]  bot-right
    (-47.9127, 200.1, 17.7899),   # [3]  notch-top
    (-43.4019, 200.1, 14.1338),   # [4]
    (-41.0706, 200.1, 12.4346),   # [5]
    (-38.6483, 200.1, 10.8902),   # [6]
    (-36.1161, 200.1, 9.5328),    # [7]
    (-33.4947, 200.1, 8.3266),    # [8]
    (-30.7992, 200.1, 7.2465),    # [9]  interpolated — aligns with L1 right-bot approach
    (-28.1037, 200.1, 6.1664),    # [10] right-bot
    (-28.1037, 200.1, 20.0818),   # [11] right-top
    (-31.5847, 200.1, 21.5512),   # [12]
    (-33.285,  200.1, 22.3576),   # [13]
    (-34.9372, 200.1, 23.2497),   # [14]
    (-36.5367, 200.1, 24.2357),   # [15]
    (-38.0956, 200.1, 25.2939),   # [16]
    (-41.146,  200.1, 27.5307),   # [17]
    (-44.1927, 200.1, 30.2581),   # [18]
    (-45.6111, 200.1, 31.7002),   # [19]
    (-46.9035, 200.1, 33.2363),   # [20]
    (-48.037,  200.1, 34.891),    # [21]
    (-49.035,  200.1, 36.6469),   # [22]
    (-49.9200, 200.1, 38.4872),   # [23] interpolated — aligns with L1 arc-end approach
    (-50.8049, 200.1, 40.3274),   # [24] arc-end
]

wire_l5_1 = make_poly_wire_3d(loft5_l1_pts)
wire_l5_2 = make_poly_wire_3d(loft5_l2_pts)

thru_l5 = _ThruSec(True, False, 1e-3)
thru_l5.AddWire(wire_l5_1)
thru_l5.AddWire(wire_l5_2)
thru_l5.CheckCompatibility(False)
thru_l5.Build()
if not thru_l5.IsDone():
    raise RuntimeError("Loft 5 ThruSections failed")

loft5_raw = Solid(thru_l5.Shape())
print(f"Loft 5 raw valid: {loft5_raw.is_valid}")

trsf_l5 = gp_Trsf()
trsf_l5.SetTranslation(gp_Vec(0, 0, 75))
loft5_moved = BRepBuilderAPI_Transform(loft5_raw.wrapped, trsf_l5, True)
loft5_moved.Build()
loft5_body = Solid(loft5_moved.Shape())
print(f"Loft 5 body valid: {loft5_body.is_valid}")

# Cut loft5 from final_body7
cut_l5 = _Cut(final_body7.wrapped, loft5_body.wrapped)
cut_l5.SetFuzzyValue(0.01)
cut_l5.Build()
if not cut_l5.IsDone():
    raise RuntimeError("Loft 5 cut failed")

final_body8 = Solid(cut_l5.Shape())
print(f"Final body 8 valid: {final_body8.is_valid}")

show(final_body8,
     names=["Final Body"],
     port=3940)

# ═══════════════════════════════════════════════════════════════
# EXPORT — STEP and STL to Desktop
# ═══════════════════════════════════════════════════════════════

import os
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI

desktop = os.path.expanduser("~/Desktop")
base_name = "PP000007_align_4040_hg15"

# STEP export
step_path = os.path.join(desktop, f"{base_name}.step")
step_writer = STEPControl_Writer()
step_writer.Transfer(final_body8.wrapped, STEPControl_AsIs)
status = step_writer.Write(step_path)
if status == IFSelect_RetDone:
    print(f"STEP exported: {step_path}")
else:
    print(f"STEP export failed (status={status})")

# STL export
stl_path = os.path.join(desktop, f"{base_name}.stl")
BRepMesh_IncrementalMesh(final_body8.wrapped, 0.1, False, 0.5).Perform()
StlAPI.Write_s(final_body8.wrapped, stl_path)
print(f"STL exported: {stl_path}")