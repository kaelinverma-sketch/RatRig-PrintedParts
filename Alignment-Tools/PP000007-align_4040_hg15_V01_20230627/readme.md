# PP000007 — align_4040_hg15

**Project:** PHIL — ETH Zurich Cell Systems Dynamics Group  
**Organisation:** Softage  
**Part series:** PP000001–PP000007 alignment tool series  
**Script:** `PP000007_align_4040_hg15.py`  
**Exports:** `PP000007_align_4040_hg15.step`, `PP000007_align_4040_hg15.stl`

---

## Overview

PP000007 is a precision alignment bracket designed to interface a **4040 aluminium extrusion profile** with an **HG15 linear rail**. It is the seventh part in the PHIL alignment tool series, each of which follows a consistent build pipeline: non-convex extruded profile → asymmetric chamfer → sequential boolean loft cuts and fuses driven entirely by coordinate data.

---

## Overall Dimensions

| Axis | Range | Dimension |
|------|-------|-----------|
| X (length) | −250 to +250 mm | **500 mm** |
| Y (depth)  | −200 to +200 mm | **400 mm** |
| Z (height) | 0 to 150 mm     | **150 mm** |

Bounding box: **500 × 400 × 150 mm**

---

## Environment

| Item | Detail |
|------|--------|
| Platform | macOS, Python 3.11 (Homebrew) |
| Virtual env | `/Users/softage/NEW ENV/.venv/` |
| CAD kernel | OpenCASCADE (OCP) via build123d |
| Viewer | OCP CAD Viewer (VS Code extension v3.4.0, port 3940) |
| OCP namespace | `OCP.*` (not `OCC.Core.*`) |

---

## Build Methodology

All geometry is constructed programmatically using raw OCP BRep APIs. No interactive modelling. Each stage produces a named intermediate solid; booleans chain sequentially.

### Stage 1 — Main Body

- **Profile:** 20-point non-convex closed polygon in the XY plane at Z=75 (centred), encoding the 4040 extrusion cross-section with a central tongue recess
- **Extrusion:** `BRepPrimAPI_MakePrism` — 150 mm in +Z (Z = 0 → 150)
- **Chamfer:** `BRepFilletAPI_MakeChamfer` — asymmetric 3 mm inward × 6 mm vertical on all edges of both top (Z=150) and bottom (Z=0) horizontal faces
- **Central tongue recess:** X = −90 to +90 mm, Y = 0 to +150 mm; corner transitions at (±75, 15) and (±90, 0)
- Result: `main_body`

### Stage 2 — HG15 Rail Profile Loft (Spline)

- **Purpose:** Cuts the HG15 linear rail seating profile into the +X face (X=250)
- **Method:** Two spline-lofted solids — outer ring (`solid_a`, 12-pt `GeomAPI_PointsToBSpline`) and inner cutout (`solid_b`, 8-pt `GeomAPI_Interpolate`); B cut from A via `BRepAlgoAPI_Cut`
- **Placement:** Rotated +90° around Y then +90° around X, translated to `(248, −29.64, 76.5)` — face lies in YZ plane, 2 mm depth in +X
- **Fillet:** R=1 mm on top/bottom edges of loft result
- **Instances:** Two cuts separated by 124.31 mm in Y (rail bolt spacing)
- Result after cuts: `final_body` → `final_body2`

### Stage 3 — Loft 1 (11-pt Polygonal Slot, −Y Side, X=248→250)

- **Purpose:** HG15 carriage slot pocket on the −Y side of the +X face
- **Profiles:** 11-point closed polygons at X=248 and X=250; `BRepBuilderAPI_MakePolygon` straight-edge wires
- **Method:** `BRepOffsetAPI_ThruSections`, `CheckCompatibility(False)`, translated +75 mm in Z
- **Profile extents:** Y = −118.52 to −65.00 mm, Z = −38 to +38.33 mm (at X=248)
- Result: `final_body2`

### Stage 4 — Loft 2 (3-pt Triangular Boss, X=248→250) — FUSED

- **Purpose:** Triangular reinforcement boss fused onto the +X face at two Y positions
- **Profiles:** 3-point triangular section at X=248 and X=250
- **Method:** `BRepOffsetAPI_ThruSections`, translated +75 mm in Z, fused via `BRepAlgoAPI_Fuse` (fuzzy value 0.1 for touching faces)
- **Instances:** Base position and +124.31 mm Y copy, both fused
- Result contributes to: `final_body4`

### Stage 5 — Loft 3 (11-pt Polygonal Slot, +Y Side, X=248→250)

- **Purpose:** Mirror of Loft 1 on the +Y side of the +X face
- **Profiles:** 11-point closed polygons at X=248 and X=250
- **Profile extents:** Y = +5.79 to +59.31 mm, Z = −38 to +38.33 mm (at X=248)
- Result: `final_body3` → after Loft 2 fuses: `final_body4`

### Stage 6 — Loft 4 (12-pt H-Slot, Y=198→200)

- **Purpose:** Twin-bolt HG15 slot pattern on the +Y face (Y=200)
- **Profiles:** 12-point H-shaped closed polygon at Y=198 and Y=200
- **Profile extents:** X = +76.23 to +140.19 mm, Z = −38 to +38 mm
- **Method:** `BRepOffsetAPI_ThruSections`, translated +75 mm in Z, cut
- Result: `final_body5`

### Stage 7 — Extrude Cut 1 (HG15 Carriage Pattern, +X Quadrant, +Y Face)

- **Purpose:** Circular bolt-hole / carriage footprint pocket on +Y face, positive-X side
- **Profile:** 155-point closed polygon in XZ plane at Y=198, covering X ≈ +2.8 to +61.3 mm, Z ≈ −40.4 to +40.4 mm
- **Method:** `BRepBuilderAPI_MakeFace` → `BRepPrimAPI_MakePrism` +2 mm in +Y (Y=198→200), translated +75 mm in Z
- Result after cut: `final_body6`

### Stage 8 — Extrude Cut 2 (HG15 Carriage Pattern, −X Quadrant, +Y Face)

- **Purpose:** Mirror carriage footprint pocket on +Y face, negative-X side
- **Profile:** 139-point closed polygon (after data-quality fix) at Y=198, covering X ≈ −139.2 to −87.6 mm, Z ≈ −40.4 to +37.9 mm
- **Data fixes applied:**
  - Swap idx 59↔60: backtrack in inner arc near (−104.8, −26.8)
  - Remove idx 87: stray out-of-order point at bottom arc near (−108.8, −40.1)
  - Swap idx 110↔111: Z-monotone break near (−139.0, −9.7)
  - Reorder: `[pt[0], pt[138], pt[137], reversed(pt[2:137]), pt[1]]` for correct winding
- **Method:** Same as Extrude Cut 1, +2 mm in +Y
- Result after cut: `final_body7`

### Stage 9 — Loft 5 (25-pt Bracket Slot, +Y Face, Y=198→200.1)

- **Purpose:** L-shaped / bracket slot pocket on +Y face, negative-X region
- **Profiles:**
  - Loft 1 (Y=198): 25 points, X = −61.25 to −30.10 mm, Z = −38 to +38.33 mm
  - Loft 2 (Y=200.1): 25 points, X = −63.25 to −28.10 mm, Z = −40 to +40.33 mm
- **Winding fix:** Loft 2 reversed from raw data (CW→CCW) to match Loft 1
- **Start-point alignment:** Loft 1 restarted at idx 15 (top-left corner, −61.25, +38.33) to match Loft 2 reversed start
- **Point count fix:** Two interpolated points added to Loft 2 (idx 9 and idx 23) to pad from 23 to 25 points, ensuring `ThruSections` vertex-to-vertex correspondence with no twist
- **Y=200.1:** Loft 2 set 0.1 mm proud of body face to prevent coincident-face boolean failure
- **Method:** `BRepOffsetAPI_ThruSections`, translated +75 mm in Z, cut via `BRepAlgoAPI_Cut` (fuzzy 0.01)
- Result: `final_body8`

---

## Boolean Operation Parameters

| Operation | Fuzzy Value | Notes |
|-----------|-------------|-------|
| All loft/extrude cuts | 0.01 mm | Standard for non-touching faces |
| Loft 2 fuses | 0.1 mm | Required for touching/coincident faces |

---

## Key OCP Patterns Used

```python
# Closed polygonal wire
wb = BRepBuilderAPI_MakeWire()
for i in range(n):
    wb.Add(BRepBuilderAPI_MakeEdge(gp_Pnt(*pts[i]), gp_Pnt(*pts[(i+1)%n])).Edge())
wb.Build()

# ThruSections loft
thru = BRepOffsetAPI_ThruSections(True, False, 1e-3)
thru.AddWire(wire1); thru.AddWire(wire2)
thru.CheckCompatibility(False)
thru.Build()

# Boolean cut with fuzzy
cut = BRepAlgoAPI_Cut(body.wrapped, cutter.wrapped)
cut.SetFuzzyValue(0.01); cut.Build()
result = Solid(cut.Shape())

# Static casts
face = TopoDS.Face_s(exp.Current())
edge = TopoDS.Edge_s(exp.Current())
```

---

## Export

Both files written to `~/Desktop/` on script completion:

```
PP000007_align_4040_hg15.step   — via STEPControl_Writer / STEPControl_AsIs
PP000007_align_4040_hg15.stl    — via BRepMesh_IncrementalMesh (0.1mm, 0.5°) + StlAPI.Write_s
```

---

## File Structure

```
PP000007_align_4040_hg15.py          Main build script
PP000007_align_4040_hg15_README.md   This file
PP000007_align_4040_hg15.step        STEP export (Desktop)
PP000007_align_4040_hg15.stl         STL export (Desktop)
```

---

## Part Series Context

| Part | Name | Rail | Extrusion |
|------|------|------|-----------|
| PP000001 | align_2020_mgn12 | MGN12 | 2020 |
| PP000002 | align_2020_mgn15 | MGN15 | 2020 |
| PP000003 | align_3030_mgn12 | MGN12 | 3030 |
| PP000004 | align_3030_mgn15 | MGN15 | 3030 |
| PP000005 | align_4040_mgn12 | MGN12 | 4040 |
| PP000006 | align_4040_hg25  | HG25  | 4040 |
| PP000007 | align_4040_hg15  | HG15  | 4040 |

---

*Generated for the PHIL project — ETH Zurich Cell Systems Dynamics Group / Softage*
