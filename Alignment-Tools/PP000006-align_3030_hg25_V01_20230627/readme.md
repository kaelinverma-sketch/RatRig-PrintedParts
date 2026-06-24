# PP000006 — Alignment Tool for 3030 Aluminium Extrusion Profile with HG25 Linear Rail

**Part Number:** PP000006-align_3030_hg25_V01_20230627  
**Project:** PHIL — ETH Zurich Cell Systems Dynamics Group  
**Original Design:** Philip Dettinger  
**CAD Environment:** Python 3.11 (Homebrew venv) · build123d · OCP CAD Viewer (port 3940)  
**Kernel:** OpenCASCADE (OCP) via build123d  

---

## Overview

PP000006 is a precision alignment tool designed to locate and register a 3030 aluminium extrusion profile fitted with an HG25 linear rail. It is part of the PP000001–PP000006 alignment tool series developed for the PHIL project.

The part is built entirely programmatically from coordinate point data using raw OCP BRep APIs, following the same pipeline established across the PP000001–PP000005 series.

---

## Overall Dimensions

| Dimension | Value |
|-----------|-------|
| Width (X) | 400 mm |
| Depth (Y) | 420 mm |
| Height (Z) | 150 mm |
| Bounding envelope | 400 × 420 × 150 mm |
| Chamfer | 3 mm inward × 6 mm vertical (top & bottom) |
| Loft taper depth | 2 mm (Y=268 → Y=270) |

---

## Build Methodology

### 1. Main Body Extrusion

A non-convex 20-point 2D profile (XY plane) is extruded 150 mm along +Z using `build123d`'s native `Wire → Face → extrude()` pipeline. The profile describes the outer perimeter of the alignment tool — a rectangular stadium shape with two inset notches at the bottom centre for the rail slot clearance.

```
Profile extents: X = ±200 mm, Y = −150 → +270 mm
Extrusion:       Z = 0 → 150 mm
```

### 2. Asymmetric Chamfer (Top & Bottom Faces)

An asymmetric chamfer is applied to all edges on both the top (Z=150) and bottom (Z=0) horizontal faces using `BRepFilletAPI_MakeChamfer` with the two-distance overload:

- **d1 = 3 mm** — inward along the flat face
- **d2 = 6 mm** — vertical drop along the side wall

Faces are detected by filtering for Y-normal planes at the target Z level using `BRepAdaptor_Surface`.

### 3. Sketch Cut Tools (PP000003 Features)

Two tapered sketch cut tools are built from a 197-point 2D YZ profile using `BRepOffsetAPI_ThruSections` with a 45° taper over 10 mm in +X, applied at X=198. A second copy is translated +116.5 mm in Y. Both are boolean-cut into the main body.

### 4. Extrude Profile Cuts & Fuses (PP000003 Features)

Four extrude operations derived from PP000003 coordinate data:

| Feature | Profile | Direction | Operation |
|---------|---------|-----------|-----------|
| Extrude1 | 107-pt oval at X=198 | +10 mm in X | Cut |
| Extrude1-Copy | Same, +116.5 mm Y | +10 mm in X | Cut |
| Extrude2 | 83-pt inner oval at X=198 | +2 mm in X | **Fuse** |
| Extrude2-Copy | Same, +116.5 mm Y | +2 mm in X | **Fuse** |

All four features are shifted Y+69.15 mm and Z−150 mm before application.

### 5. Tapered Loft Cuts

Two tapered loft cut bodies are built from paired coordinate profiles using `BRepOffsetAPI_ThruSections(solid=True, ruled=False)`:

**Loft Cut 1 — H-slot (rail slot)**
- Profile 1: 12-point H-slot at Y=268
- Profile 2: 12-point H-slot (scaled +2 mm outward) at Y=270
- Winding fix: Loft2 reversed (CW→CCW) and corner-rotated to match Loft1[0]
- Shift: Z−75 mm
- Operation: Boolean cut

**Loft Cut 2 — Oval (rail bearing profile)**
- Profile 1: 126-point oval at Y=270
- Profile 2: 125-point oval at Y=268
- Winding fix: Loft2 reversed (CW→CCW), arc-length resampled to 200 points each
- Shift: Z−75 mm
- Operation: Boolean cut

### 6. Extrude Cuts 3 & 4 (G-profile Features)

Two additional extrude cuts from YZ coordinate profiles at Y=269, extruded −4 mm in Y and shifted Z−75 mm, Y+1 mm:

- **Extrude Cut 3**: 158-point "G right" profile (bad backtracking points at indices 70–71 removed)
- **Extrude Cut 4**: 139-point "G left" profile (bad backtracking points at indices 35–36 removed)

Bad points were identified by detecting near-180° direction reversals (>90° turn angle) in the XZ plane and removed before face construction.

---

## Key OCP API Patterns

```python
# Non-convex face from polygon wire
poly = BRepBuilderAPI_MakePolygon()
for x, y, z in pts: poly.Add(gp_Pnt(x, y, z))
poly.Close()
face = BRepBuilderAPI_MakeFace(poly.Wire(), True)

# Tapered loft between two wires
loft = BRepOffsetAPI_ThruSections(True, False)
loft.AddWire(wire1); loft.AddWire(wire2)
loft.CheckCompatibility(False); loft.Build()

# Asymmetric chamfer
chamfer = BRepFilletAPI_MakeChamfer(solid)
chamfer.Add(d1, d2, edge, ref_face)

# Boolean cut with fuzzy tolerance
cut = BRepAlgoAPI_Cut(base.wrapped, tool)
cut.SetFuzzyValue(0.01); cut.Build()
```

---

## Winding & Twist Fix Protocol

All `ThruSections` loft pairs require matching winding direction (both CCW or both CW). The fix applied throughout:

1. Compute cross product of first 3 points in XZ plane to determine winding
2. If mismatched → `list(reversed(profile2))`
3. Rotate reversed profile so its closest point to `profile1[0]` becomes index 0
4. Arc-length resample both profiles to equal point count (200 pts) before building wires

---

## File Structure

```
PP000006-align_3030_hg25_V01_20230627/
├── PP000006-align_3030_hg25_V01_20230627.py   # Main build script
├── README.md                                   # This file
├── PP000006-align_3030_hg25_V01_20230627.step  # STEP export
└── PP000006-align_3030_hg25_V01_20230627.stl   # STL export
```

---

## Dependencies

```
build123d
ocp-vscode
OCP (OpenCASCADE via build123d)
Python 3.11 (Homebrew venv)
```

---

## Running

```bash
cd ~/PHIL/PP000006-align_3030_hg25_V01_20230627
python PP000006-align_3030_hg25_V01_20230627.py
```

OCP CAD Viewer must be running on port 3940. STEP and STL files are exported to `~/Desktop`.

---

*Part of the PHIL alignment tool series: PP000001 · PP000002 · PP000003 · PP000004 · PP000005 · **PP000006***
