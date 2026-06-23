# PP000004-align_3030_mgn15_V01_20230627 — Alignment Tool (3030 MGN15) `V01_20230627`

Part of the **PHIL project** for ETH Zurich's Cell Systems Dynamics Group, originally designed by Philip Dettinger.

---

## Overview

`PP000004-align_3030_mgn15_V01_20230627` is a precision alignment tool for 3030 aluminium extrusion profiles with MGN15 linear rail. The part is built entirely programmatically using Python with OpenCASCADE (OCP) raw BRep APIs, producing a single compound solid exported as STEP and binary STL.

---

## Overall Dimensions

| Parameter | Value |
|---|---|
| Width (X) | 400 mm (−200 → +200) |
| Depth (Y) | ~302 mm (main body + loft protrusions to Y=150) |
| Height (Z) | 150 mm (Z=+75 → Z=−75) |
| Body centre | X=0, Y=0, Z=0 |
| Chamfer | 3 mm inward / 6 mm vertical, top and bottom faces |

---

## Build Pipeline

The script executes the following sequential operations on a single `result` shape:

### 1. Main Body Extrusion
A 20-point non-convex closed profile defined in the XY plane at Z=+75 is extruded 150 mm in the −Z direction, producing a solid spanning Z=+75 → Z=−75.

The profile is a U-channel / saddle shape with two outer rectangular arms (±200 mm in X) connected by a raised inner bridge. Built using `BRepBuilderAPI_MakePolygon` → `BRepBuilderAPI_MakeFace` → `BRepPrimAPI_MakePrism`.

### 2. Asymmetric Chamfer
All edges on the top face (Z=+75) and bottom face (Z=−75) are chamfered using `BRepFilletAPI_MakeChamfer` with `Dis1=3.0 mm` (inward along face) and `Dis2=6.0 mm` (along side face). Faces are detected by normal direction and Z-location using `BRepAdaptor_Surface`.

### 3. Sketch Cuts (×2)
A 196-point dense closed profile (a circular arc shape) is used to build a tapered cut tool via `BRepOffsetAPI_ThruSections` (loft with 45° taper, 10 mm depth in +X from X=198). Applied twice: once at the original position and once translated +116.5 mm in Y, using `BRepAlgoAPI_Cut`.

### 4. Extrude Profiles (×2, each mirrored in Y)
Two profiles extruded in the +X direction from X=198:

- **Extrude 1** (107 pts, 10 mm depth): cut into the body — `BRepAlgoAPI_Cut`
- **Extrude 2** (84 pts, 2 mm depth): fused onto the body — `BRepAlgoAPI_Fuse`

Both features are copied and translated +116.5 mm in Y, giving four total features.

### 5. Loft Bodies 1–6 (Fused)
Six loft bodies sourced from PP000003 profiles, each built as a `BRepOffsetAPI_ThruSections` solid between two planar wire profiles at Y=128/130 (or Y=128/130 equivalent), then Z-translated and **fused** into the result:

| Body | Profile pts | Z offset | Operation |
|---|---|---|---|
| Loft 1 | 4+4 (two rectangular loops A+B) | +75.0 | Fuse |
| Loft 2 | 7-point | +75.0 | Fuse |
| Loft 3 | ~160-point dense | +75.0 | Fuse |
| Loft 4 | 10-point | +75.13 | Fuse |
| Loft 5 | 136-point (bad-point fix + corner alignment) | +75.13 | Fuse |
| Loft 6 | 27-point | +75.13 | Fuse |

### 6. New Loft Cuts 1–7 (Cut)
Seven additional loft bodies built from new profile coordinates at Y=148/150, each **cut** into the result. These represent engraved character features (numeral outlines):

| Body | Profile pts | Shape | Z offset |
|---|---|---|---|
| New 1 | 4-point rectangular | Simple slot | +5.0 |
| New 2 | 7-point | Arrow/star | +5.0 |
| New 3 | 4-point rectangular | Simple slot | +5.0 |
| New 4 | ~168-point dense | "G" shape | +5.0 |
| New 5 | 10-point | Bracket shape | +5.0 |
| New 6 | 26-point | Arc bracket | +5.0 |
| New 7 | 141+123-point dense | "5" shape | +5.0 |

Dense profiles (New 4, New 7) require bad-point removal and corner-index alignment before arc-length resampling to eliminate loft twist.

---

## OCC Patterns Used

| Pattern | API |
|---|---|
| Non-convex profile extrusion | `BRepBuilderAPI_MakeFace(wire, True)` — the `True` flag is required for non-convex planar profiles |
| Asymmetric chamfer | `BRepFilletAPI_MakeChamfer.Add(Dis1, Dis2, edge, ref_face)` |
| Loft between two wire sections | `BRepOffsetAPI_ThruSections(isSolid=True, isRuled=True/False)` |
| Boolean fuse | `BRepAlgoAPI_Fuse` |
| Boolean cut | `BRepAlgoAPI_Cut` |
| Shape translation | `BRepBuilderAPI_Transform` with `gp_Trsf.SetTranslation` |
| Face detection by normal+Z | `BRepAdaptor_Surface` + `TopExp_Explorer` |
| Shape casting (no `topods` module) | Manual `TShape/Location/Orientation` copy into `TopoDS_Face`/`TopoDS_Edge` |
| Arc-length resampling | Custom `arc_length_resample_3d()` — equalises point counts and eliminates loft twist |
| Bad-point removal | Manually identified backtracking indices removed before lofting |
| STEP export | `STEPControl_Writer` |
| STL export | `BRepMesh_IncrementalMesh` (0.1 mm / 0.5°) + `StlAPI_Writer` |

---

## Output Files

| File | Format | Path |
|---|---|---|
| `PP000004-align_3030_mgn15_V01_20230627.step` | STEP AP203 | `~/Desktop/PP000004-align_3030_mgn15_V01_20230627.step` |
| `PP000004-align_3030_mgn15_V01_20230627.stl` | Binary STL | `~/Desktop/PP000004-align_3030_mgn15_V01_20230627.stl` |

---

## Environment

| Dependency | Version |
|---|---|
| Python | 3.11 (Homebrew) |
| OCP | via `pip install ocp` |
| ocp-vscode | 3.4.0 (OCP CAD Viewer, port 3940) |
| Platform | macOS |

---

## Running

```bash
python PP000004-align_3030_mgn15_V01_20230627-align_3030_mgn15_V01_20230627.py
```

The script displays the result in OCP CAD Viewer and exports STEP + STL to `~/Desktop/`.
