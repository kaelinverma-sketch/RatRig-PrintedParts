# PP000002-align_2020_mgn15_V01_20230627

**PHIL Project — ETH Zurich Cell Systems Dynamics Group**
*Originally designed by Philip Dettinger*

---

## Overview

Parametric alignment tool for 2020 aluminium extrusion profile with MGN15 linear rail. The part is a non-convex extruded body with asymmetric chamfers and multiple loft-cut pockets, generated entirely through programmatic 3D CAD scripting in Python using raw OCP/OpenCASCADE APIs.

**Script file:** `PP000002-align_2020_mgn15_V01_20230627.py`
**Export files:** `PP000002_final_delivery.step`, `PP000002_final_delivery.stl`

---

## Overall Dimensions

Derived from the 20-point base profile and extrusion parameters:

| Parameter | Value |
|---|---|
| Profile span (X) | 300 mm (−150 to +150) |
| Profile depth (Y) | 250 mm (0 to −250) |
| Extrusion height (Z) | 150 mm |
| Chamfer — horizontal | 6 mm |
| Chamfer — vertical | 3 mm |

The body occupies the approximate bounding envelope **300 × 250 × 150 mm** before loft-cut subtractions.

---

## Script Methodology

### 1. Base Body (Body 1) — Non-Convex Profile Extrusion

A 20-point 2D non-convex closed profile is defined in the XY plane and extruded 150 mm along +Z using `BRepPrimAPI_MakePrism`. Asymmetric chamfers (6 mm horizontal × 3 mm vertical) are applied to all horizontal edges at Z = 0 and Z = 150 via build123d's `.chamfer()` method with explicit edge filtering.

### 2. Loft Cut Tools — General Pattern

All loft-cut bodies follow a shared construction idiom:

1. Define two sets of 3D profile points at different X (or Y) positions, typically 2 mm apart.
2. Arc-length resample both profiles to the same point count (N = 200) via `arc_length_resample()` for clean `ThruSections` correspondence.
3. Where profiles have sharp corners or non-uniform windings, apply corner-matched segment resampling to preserve angular fidelity across the loft.
4. Build closed 3D polygon wires with `BRepBuilderAPI_MakePolygon`.
5. Loft the two wires into a solid with `BRepOffsetAPI_ThruSections(solid=True, ruled=False)`.
6. Subtract the loft solid from the running result using `BRepAlgoAPI_Cut`, then unwrap the result from the output `Compound` to recover a single `Solid`.

### 3. Loft Cut Features

| Body | Description | Operation |
|---|---|---|
| Body 2 | Right-side organic pocket (X = 148 → 150, Y ≈ −171 to −207) | Cut |
| Body 3 | Right-side lower pocket (X = 148 → 150, Y ≈ −128 to −163) | Cut |
| Body 4 | Body 2 copy, shifted +86 mm in Y | Cut |
| Body 5 | Right-side boss loft (X = 146 → 150, Y ≈ −52 to −68) | Fuse |
| Body 5 copy | Body 5 copy, shifted −86 mm in Y | Fuse |
| Body 6 | Body 3 copy, shifted +86 mm in Y | Cut |
| Body 8 | Bottom-face N-shape pocket (Y = −2 → 0, XZ ≈ 15–64) | Cut |
| Body 9 | N-letter engraving pocket (Y = −2 → +4, XZ via 10-pt profile) | Cut |
| Body 10 | Left bracket pocket (X ≈ −51 to −75, Y = 0 → −2) | Cut |
| Body 11 | Left arc pocket (X ≈ −92 to −128, Y = 0 → −2) | Cut |
| Body 12 | Right rectangular slot (X = 118 → 128, Y = 0 → −2) | Cut |
| Body 13 | K-arrow shaped pocket (X = 82 → 121, Y = −2 → 0) | Cut |
| Body 14 | Left rectangular slot (X = 75 → 85, Y = −2 → 0) | Cut |

### 4. Boolean Sequence

All boolean operations are performed sequentially on a single accumulating `result` solid:

```
body1  →  [cut B2] →  [cut B3] →  [cut B4] →  [cut B6]
       →  [cut B8] →  [cut B9] →  [cut B10] → [cut B11]
       →  [fuse B5] → [fuse B5_copy]
       →  [cut B12] → [cut B13] → [cut B14]
       =  final result
```

`BRepAlgoAPI_Cut` output is always unwrapped via `Compound(...).solids()[0]` to guarantee a clean `Solid` topology before the next operation. Fuse operations use `SetFuzzyValue(0.1)` to bridge minor geometric gaps.

### 5. Key OCC Utilities

```python
arc_length_resample(pts, n)   # Uniform arc-length resampling of 3D point lists
make_3d_wire(pts)             # BRepBuilderAPI_MakePolygon closed wire from XYZ list
make_closed_wire(pts)         # 2D XY closed wire for base profile
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `build123d` | High-level solid/edge access, chamfer, STEP/STL export |
| `OCP` (`opencascade-core`) | Raw BRep kernel — wires, faces, prisms, lofts, booleans |
| `ocp_vscode` | OCP CAD Viewer visualisation (port 3940) |

Python 3.11 (Homebrew), macOS. Virtual environment recommended.

```bash
pip install build123d ocp-vscode
```

---

## Running the Script

```bash
python PP000002-align_2020_mgn15_V01_20230627.py
```

Output files are written automatically to `~/Desktop/`:
- `PP000002_final_delivery.step`
- `PP000002_final_delivery.stl`

The OCP CAD Viewer must be running on port 3940 for live visualisation.

Part number: `PP000001`
Version: `V01`
Date: `2023-06-27`
