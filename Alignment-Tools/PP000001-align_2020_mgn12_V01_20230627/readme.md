# PP000001-align_2020_mgn12_V01_20230627

**Alignment Tool — 2020 Extrusion / MGN12 Linear Rail**
Original design by Philip Dettinger · ETH Zurich Cell Systems Dynamics Group · PHIL Project

---

## Overview

This script programmatically reconstructs the PP000001 alignment tool used for positioning 2020 aluminium extrusions with MGN12 linear rails. The part is built entirely in Python using raw OpenCASCADE (OCP) APIs — no GUI, no manual CAD operations. The output is a single STEP + STL file ready for 3D printing or CNC machining.

---

## Overall Dimensions

| Parameter | Value |
|---|---|
| Overall width (X) | 300 mm |
| Overall depth (Y) | 230 mm |
| Overall height (Z) | 150 mm |
| Bounding envelope | 300 × 230 × 150 mm |
| Chamfer — top face | 6 mm (side) × 3 mm (face) |
| Chamfer — bottom face | 6 mm (side) × 3 mm (face) |
| New loft cut depth | 2 mm (Y=128 → Y=130) |

---

## Main Body Profile

The main body is extruded from a 20-point non-convex closed polygon in the XY plane. Key profile vertices:

| Feature | Coordinates |
|---|---|
| Outer corners (top) | (±150, 115) → (±135, 130) |
| Outer corners (bottom) | (±150, −85) → (±135, −100) |
| Notch corners | (±115, −100) → (±100, −85) |
| Inner shelf | (±100, 0) → (±75, 0) |
| Inner recess | (±60, 15) → (±60, 80) |

The profile is extruded 150 mm in the −Z direction (Z=0 to Z=−150).

---

## Methodology

### 1. Main Body Construction
- 20-point closed polygon built with `BRepBuilderAPI_MakePolygon`
- Face created with `BRepBuilderAPI_MakeFace`
- Extruded with `BRepPrimAPI_MakePrism` (150 mm, −Z)

### 2. Chamfering
- Top (Z≈0) and bottom (Z≈−150) perimeter edges selected by Z centroid via `BRepGProp.LinearProperties_s`
- Adjacent lateral faces found by nested `TopExp_Explorer` + `IsSame()` edge matching
- Asymmetric chamfer applied with `BRepFilletAPI_MakeChamfer.Add(6.0, 3.0, edge, lateral_face)`
  - 6 mm measured along side wall
  - 3 mm measured inward across flat face

### 3. Loft Tool Bodies
Loft bodies are built using `BRepOffsetAPI_ThruSections` from pairs of closed 3D polygon wires. Each body is defined by two profiles (inner and outer) resampled to equal point counts via arc-length resampling for clean surface correspondence.

| Body | Type | Operation | Extra Y offset |
|---|---|---|---|
| Body 2 | Circular loft cut | Boolean cut | +8.14 mm |
| Body 3 | Circular loft cut | Boolean cut | — |
| Body 4 | Body 2 copy (+86 Y) | Boolean cut | +8.14 mm |
| Body 5 | Side boss | **Fuse** | +8.14 mm |
| Body 5 copy | Side boss (−86 Y) | **Fuse** | +8.14 mm |
| Body 6 | Body 3 copy (+86 Y) | Boolean cut | +8.14 mm |
| Body 8 | Letter G loft | Boolean cut | — |
| Body 9 | Letter Z-arrow loft | Boolean cut | — |
| Body 10 | Letter G copy (−X) | Boolean cut | — |
| Body 12 | Rectangle loft | Boolean cut | — |
| Body 13 | K-arrow loft | Boolean cut | — |
| Body 14 | Rectangle loft | Boolean cut | — |

All loft bodies are translated **+130 mm Y / −150 mm Z** before the boolean operation to align with the main body coordinate system. Bodies 2, 3, 4, 5, 5 copy and 6 receive an additional **+8.14 mm Y** offset.

### 4. New Loft Body (Front Face Engraving)
A additional engraving profile is applied to the front face (Y=130):
- Source profiles: Loft1 (X=148, inner) and Loft2 (X=150, outer)
- Coordinates remapped: `orig_Y → new_X`, `orig_Z → new_Z`, both centred at origin
- Inner wire placed at Y=130, outer wire at Y=128
- Rotated 180° around Z axis through profile centroid
- Translated: −111.35 mm X, −66.36 mm Z
- Applied as boolean cut

### 5. Boolean Operations
All cuts use `BRepAlgoAPI_Cut` with `SetFuzzyValue(0.01)` for tolerance. Fuse operations use `SetFuzzyValue(0.1)` to handle coincident faces. Operations are applied sequentially to the result shape.

---

## File Structure

```
PP000001-align_2020_mgn12_V01_20230627.py   ← Main build script
README.md                                    ← This file
```

### Exports (written to Desktop)
```
~/Desktop/PP000001-align_2020_mgn12_V01_20230627.step
~/Desktop/PP000001-align_2020_mgn12_V01_20230627.stl
```

---

## Requirements

| Package | Purpose |
|---|---|
| `OCP` | OpenCASCADE Python bindings (via `pip install ocp`) |
| `build123d` | `Solid` wrapper used by loft section |
| `ocp_vscode` | OCP CAD Viewer for visualisation |

Python 3.11 (Homebrew), venv recommended.

```bash
pip install ocp build123d ocp-vscode
python PP000001-align_2020_mgn12_V01_20230627.py
```

---

## Key OCC Patterns Used

- `BRepBuilderAPI_MakePolygon` — closed 3D polygon wire construction
- `BRepPrimAPI_MakePrism` — linear extrusion
- `BRepFilletAPI_MakeChamfer` — asymmetric two-distance chamfer
- `BRepOffsetAPI_ThruSections` — loft between two closed wires
- `BRepAlgoAPI_Cut` / `BRepAlgoAPI_Fuse` — boolean operations
- `TopExp_Explorer` + `IsSame()` — edge-to-face adjacency lookup
- `BRepGProp.LinearProperties_s` — edge centroid for Z classification
- `gp_Trsf` + `BRepBuilderAPI_Transform` — translation and rotation
- `STEPControl_Writer` — STEP export
- `StlAPI_Writer` + `BRepMesh_IncrementalMesh` — STL export at 0.1 mm tolerance

---

*Part of the PHIL (Philip's Hardware Interface Library) open-source lab automation project.*
*ETH Zurich · Cell Systems Dynamics Group*
