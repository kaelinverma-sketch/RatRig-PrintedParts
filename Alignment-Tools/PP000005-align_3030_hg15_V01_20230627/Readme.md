# PP000005 — Alignment Tool: 30×30 HG15 Rail (V01, 2023-06-27)

**Part of the PHIL Project** — ETH Zurich Cell Systems Dynamics Group  
Original design by Philip Dettinger. Scripted implementation by Softage.

---

## Overview

`PP000005-align_3030_hg15_V01_20230627.py` generates the HG15 linear rail alignment tool as a fully parametric solid using Python with OpenCASCADE (OCP) raw BRep APIs and build123d. The script builds the part from coordinate-driven profiles without any CAD GUI, producing STEP and STL exports directly to disk.

---

## Overall Dimensions

| Dimension | Value |
|-----------|-------|
| Width (X) | 400 mm (−200 to +200) |
| Depth (Y) | 350 mm (−150 to +200) |
| Height (Z) | 150 mm (0 to +150) |
| Top chamfer | 3 mm inward × 6 mm downward |
| Bottom chamfer | 3 mm inward × 6 mm upward |
| Extrude profile mid-plane | Z = +75 mm |

---

## Build Pipeline

The script executes the following operations sequentially, each building on the previous `result` shape:

### 1. Main Body Extrusion
A 20-point non-convex closed polygon (the outer silhouette of the alignment tool) is extruded 150 mm in +Z. The profile is defined at Z=75 in the source coordinates and flattened to Z=0 for the base face. The prism is built via `BRepPrimAPI_MakePrism` and promoted to a solid through `BRepBuilderAPI_MakeSolid` after face collection with `TopExp_Explorer`.

### 2. Asymmetric Chamfer — Top & Bottom
`BRepFilletAPI_MakeChamfer` is applied to all edges of the top face (Z=150) and bottom face (Z=0) using two-distance mode:
- **D1 = 3 mm** — inward along XY
- **D2 = 6 mm** — vertical (downward from top / upward from bottom)

Horizontal faces are located by checking plane normals via `BRepAdaptor_Surface`.

### 3. Sketch Cut Tools (L1 & L2)
Two tapered loft cut tools are built from a 218-point 2D sketch profile using `BRepOffsetAPI_ThruSections`. Each tool is a tapered solid swept from a base wire to a scaled far wire at 10 mm depth in +X with a 45° taper. L2 is a Y+116.5 mm translated copy of L1.

### 4. Extrude Profile Cuts & Fuses (L3 & L4)
Two coordinate-driven profiles are extruded in +X and applied to the main body:
- **L3** — 110-point closed profile extruded 10 mm in +X, boolean cut. Applied twice (original + Y+116.5 mm copy).
- **L4** — 84-point inner profile extruded 2 mm in +X, boolean fused (adds material). Applied twice (original + Y+116.5 mm copy).

All profiles are offset +34 mm in Y (`Y_LOFT_OFFSET`) from their source coordinates.

### 5. Loft Cut — Rectangular Profile (Y=198 → Y=200)
A 25-point profile (resembling a "1" numeral shape) is lofted from Y=198 to Y=200 using `BRepOffsetAPI_ThruSections`. The two profiles are aligned by rotating both to start at their first 90° rectangular corner, then resampled section-by-section:
- Arc section: 80 resampled points
- Rect corners: 3 exact points
- Inner arc: 30 resampled points

This avoids seam twist caused by different point densities between structural regions. Applied as a boolean cut into the main body face.

### 6. Extrude Cut — Y=198 Profile (3 mm in +Y)
A 184-point closed profile at Y=198 is extruded 3 mm in +Y using `BRepPrimAPI_MakePrism`, cutting a shallow pocket into the Y=200 face. Z-shifted +75 mm to align with the mid-plane.

### 7. Loft Cut — "1" Numeral Profile (Y=198 → Y=200)
A second loft cut using a 25-point profile of a "1" numeral shape, built with section-by-section resampling to prevent twist at the rectangular notch boundary.

### 8. Extrude Cut — "5" Numeral Profile (Y=201, 4 mm depth)
A 150-point closed profile (resembling a "5" numeral) with out-of-order points corrected in pre-processing. Built using `BRepBuilderAPI_MakePolygon` directly (bypassing `make_planar_wire_on_y`) and extruded 4 mm in −Y from Y=201, cutting a visible pocket into the Y=200 face.

---

## OCP / Build123d Patterns Used

| Pattern | Usage |
|---------|-------|
| `BRepBuilderAPI_MakeFace(plane, wire, True)` | Non-convex profile faces — required for all coordinate-driven profiles |
| `BRepPrimAPI_MakePrism` | All linear extrusions (Z body, X cuts, Y pocket cuts) |
| `BRepOffsetAPI_ThruSections(True, True/False)` | Tapered loft cut tools |
| `BRepFilletAPI_MakeChamfer.Add(d1, d2, edge, face)` | Asymmetric two-distance chamfer |
| `BRepAlgoAPI_Cut / Fuse` | All boolean operations |
| `TopExp_Explorer` | Face/edge traversal for chamfer and wire extraction |
| `BRepAdaptor_Surface` | Horizontal face detection by normal direction |
| `BRepBuilderAPI_Transform` | Y-direction copies of cut/fuse tools |
| `arc_length_resample_3d` | Equal-count resampling for loft wire correspondence |
| `make_planar_wire_on_y` | Guaranteed-planar wire construction on Y-constant planes |
| Section-by-section resampling | Prevents seam twist on profiles with different point densities per structural region |

---

## File Outputs

| File | Description |
|------|-------------|
| `PP000005-align_3030_hg15_V01_20230627.step` | Full precision CAD model (ISO 10303) |
| `PP000005-align_3030_hg15_V01_20230627.stl` | Mesh for 3D printing / validation |

Both files are exported to `~/Desktop/`.

---

## Environment

| Requirement | Version |
|-------------|---------|
| Python | 3.11 (Homebrew) |
| OCP | via `pip install ocp` |
| build123d | latest |
| OCP CAD Viewer | VS Code extension (port 3940) |
| Platform | macOS |

---

## Running

```bash
cd /path/to/script
python PP000005-align_3030_hg15_V01_20230627.py
```

The OCP CAD Viewer will display the result automatically. STEP and STL files are written to `~/Desktop/`.

---

## Part of PHIL Project

This component is part of the **PHIL** (Programmable Hardware Interface for Laboratory) project developed for ETH Zurich's Cell Systems Dynamics Group. The full component suite includes Chamber, Screw, Handle, Arduino Plate, Power Box assemblies, and multiple alignment tool variants (PP000001–PP000005).
