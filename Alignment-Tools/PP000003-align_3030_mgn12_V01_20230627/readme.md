# PP000003 — 3030 MGN12 Alignment Tool
**Project:** PHIL — ETH Zurich Cell Systems Dynamics Group  
**Script:** `PP000003-align_3030_mgn12_V01_20230627.py`  
**CAD Engine:** OpenCASCADE (OCP) via raw BRep APIs — no build123d  
**Visualisation:** OCP VSCode Viewer (`ocp_vscode`)  
**Export:** STEP + binary STL → `~/Desktop/`

---

## Overall Dimensions

| Dimension | Value |
|---|---|
| Body width (X) | 400 mm (−200 → +200) |
| Body depth (Y) | 280 mm (−150 → +130) |
| Body height (Z) | 150 mm (0 → 150) |
| Chamfer — top/bottom edges | 3 mm × 6 mm (asymmetric) |
| Extrude cut profile depth (X) | 10 mm (+X from X=198) |
| Extrude fuse profile depth (X) | 2 mm (+X from X=198) |
| Loft cut Z offset (all features) | +75.0 mm or +75.13 mm |
| Y-copy offset (mirrored features) | +116.5 mm |

---

## Methodology

### 1 — Main Body
A 20-point non-convex closed polygon is defined in the XY plane and extruded 150 mm in +Z using `BRepPrimAPI_MakePrism`. The profile captures the characteristic H-shaped cross-section of the alignment tool with chamfered leg corners.

Asymmetric chamfers (3 mm × 6 mm) are applied to all top and bottom horizontal edges using `BRepFilletAPI_MakeChamfer`. Edges are identified by traversing faces with `TopExp_Explorer`, filtering for horizontal planar faces at Z=0 and Z=150 via `BRepAdaptor_Surface`.

### 2 — Sketch Cuts (Taper Loft Cuts)
Two tapered loft cuts are applied at the right face (X≈198) using a 108-point profile. Each cut tool is built as a `BRepOffsetAPI_ThruSections` solid between a base wire at X=198 and a scaled far wire at X=208 (10 mm depth, 45° taper). Cut 2 is a Y-translated copy (+116.5 mm) of Cut 1, applied via `BRepBuilderAPI_Transform` + `BRepAlgoAPI_Cut`.

### 3 — Extrude Profile Features (Right Face)
Two profiles from coordinate data are extruded in +X from X=198:

- **Extrude Cut 1** (83 pts, 10 mm depth): subtracted from the main body via `BRepAlgoAPI_Cut`. Represents the outer slot profile.
- **Extrude Fuse 2** (83 pts, 2 mm depth): fused into the main body via `BRepAlgoAPI_Fuse`. Represents a raised lip feature.

Both are Z-offset by +75.13 mm. Both are Y-copied (+116.5 mm) and the respective cut/fuse operations repeated on the copy.

### 4 — Loft Body Cuts (Left Face, Y=128→130 Plane)
Six loft bodies are constructed as `BRepOffsetAPI_ThruSections` solids between two planar profiles separated by 2 mm in Y (Y=128 and Y=130). Each loft is translated +75 mm or +75.13 mm in Z to centre on the body mid-plane, then subtracted from the main body.

| Loft | Pts (Y=128 / Y=130) | Notes |
|---|---|---|
| 1 | 4 / 4 (×2 loops) | Two rectangular loops, fused |
| 2 | 7 / 7 | Single non-convex polygon |
| 3 | 171 / 171 | Dense tapered profile; corner-matched resampling |
| 4 | 10 / 10 | Pre-aligned equal-count profiles |
| 5 | 128 / 131 | Arc-length resampled; P1 self-intersection at idx 97–98 removed; both profiles rotated to first structural corner before resampling |
| 6 | 27 / 27 | P2 index 17/18 swap corrected; built directly |

#### Wire Construction Pattern
All profile wires use `BRepBuilderAPI_MakePolygon` + `.Close()` + `BRepBuilderAPI_MakeFace`. For lofts with mismatched point counts or self-intersections the following pre-processing is applied before building:

1. **Self-intersection removal** — detect crossing segments in XZ plane; remove out-of-order points.
2. **Start-index alignment** — rotate both point lists so index 0 coincides with the first structural corner (largest direction change > 100°). This ensures `ThruSections` pairs corresponding vertices without twist.
3. **Arc-length resampling** — both lists resampled to equal count N by arc-length interpolation, preserving shape fidelity.

### 5 — Export
- **STEP**: `STEPControl_Writer` with `STEPControl_AsIs` transfer mode.
- **STL**: `BRepMesh_IncrementalMesh` (0.1 mm linear deflection, 0.5° angular) followed by `StlAPI.Write_s()` in binary mode.
- Output path: `~/Desktop/PP000002_MainBody.step` and `~/Desktop/PP000002_MainBody.stl`

---

## Key OCP APIs Used

| API | Purpose |
|---|---|
| `BRepBuilderAPI_MakePolygon` | Construct polyline wires from point lists |
| `BRepBuilderAPI_MakeFace` | Create planar face from closed wire |
| `BRepPrimAPI_MakePrism` | Linear extrusion of a face |
| `BRepFilletAPI_MakeChamfer` | Asymmetric chamfer on selected edges |
| `BRepOffsetAPI_ThruSections` | Loft solid between two wires |
| `BRepAlgoAPI_Cut` | Boolean subtraction |
| `BRepAlgoAPI_Fuse` | Boolean union |
| `BRepBuilderAPI_Transform` | Translate/copy shapes via `gp_Trsf` |
| `BRepMesh_IncrementalMesh` | Tessellate for STL export |
| `STEPControl_Writer` | STEP file export |
| `StlAPI.Write_s` | STL file export |
| `TopExp_Explorer` | Traverse topology (faces, edges) |
| `BRepAdaptor_Surface` | Interrogate face geometry type and plane normal |

---

## File Structure

```
PP000003-align_3030_mgn12_V01_20230627/
├── PP000003-align_3030_mgn12_V01_20230627.py   # Main CAD script
└── README_PP000003.md                           # This file

~/Desktop/
├── PP000003_MainBody.step
└── PP000003_MainBody.stl
```

---

## Notes

- All coordinates are in **millimetres**.
- The main body origin is at XY centre of the H-profile, Z=0 at the bottom face.
- Loft profiles with Y=130 in the source file are the **outer** (wider) wire; Y=128 is the **inner** wire. The 2 mm Y separation creates a shallow tapered pocket wall.
- The `arc_length_resample_3d()` utility resamples any 3D polyline to N points by cumulative arc-length interpolation — it is defined once in the script and reused across multiple loft bodies.
