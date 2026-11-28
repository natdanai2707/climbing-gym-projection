# Active Space Hat Yai: steel structure

Phase status (28 Nov 2026)

| Phase | Status | Output |
|---|---|---|
| 1 Load + check | done | build_model.py reproduces `model/geo.bin` byte-identical (sha256 b2231fa9…a8158); grids match |
| 2 Layout | **for review** | `out/layout.json`, `out/p2/*.png`, `out/clash_P2-layout-r1.csv`, `viewer/index.html` |
| 3 Sizing | waiting for D1–D10 + climbing wall loads | |
| 4 Connections | | |
| 5 Drawings + export | | |

`model/` is not touched. All structure work lives here.

## Run

```
cd structure/tools
python3 layout.py        # member layout -> out/layout.json (prints tonnage by system)
python3 p2_drawings.py   # plan / grid / line elevations over the mz19 architecture -> out/p2/
python3 clash.py         # member section boxes vs mz19 -> out/clash_<version>.json/.csv
```
Needs numpy, scipy, matplotlib. Viewer: serve `virtual-walk/` and open `/structure/viewer/` (loads `../out/layout.json` and `../../model/geo.*`).

## Conventions
- Coordinates as mz19: metres, z-up, x front (street, -4.99) to rear (17.0), y along the building.
- Grids 1–8: y 67.75, 74.65, 81.55, 88.45, 97.45, 104.05, 110.65, 117.25. A x -4.84, B x 16.86, ridge x 6.0.
- Main columns sit flush with the outer cladding line (outer flange face x -4.98 / 17.00); grid lines stay as in architecture.
- Member record: `id` (mark), `pre` (C column, R rafter, HN haunch, WP wind post, P purlin, SR sag rod, ES eave strut, RB/VB roof/wall brace, ST strut, G girt, B beam, J joist, FP fascia plate, SS/SB/SC/TR stair parts, HP/HR guard post/rail, GF glass frame), `sys`, `asm`, `ph` (erection phase 1–6), `p0`/`p1` centroid line, `web` web direction, `sec`, `grade`, `L`, `kg`.
- Sections in phase 2 are PRELIMINARY. Phase 3 replaces them from calculation.

## Design basis (proposed, confirm before phase 3)
- AISC 360-16 LRFD. SS400 hot-rolled, SM520 option for the +6.3 girder, cold-formed C to TIS 1228 SSC400 galvanised, rods SR24, HSFG F10T for moment joints, 8.8 secondary, anchors SS400.
- LL: gym / mezz / front L2 / stairs 5.0 kPa, guard 0.75 kN/m at +1.1, roof 0.30 kPa + 1.0 kN point on purlins.
- SDL: composite slab 120 mm 2.6 kPa, finishes + ceiling + services 1.0 kPa, roof sheet 0.15 kPa, duct zone 0.25 kPa.
- Wind มยผ. 1311-50: Songkhla group 4A, V50 25 m/s, TF 1.2, Iw 1.0 (verify table).
- Deflection L/360 LL, L/240 total, purlins L/180, climbing-zone drift H/200. Floor vibration AISC DG11, target fn ≥ 9 Hz for the bouldering deck.
- Climbing wall loads (proposal, EN 12572-1/-2 basis, to confirm with the wall builder and device manuals): wall DL 0.50 kPa of wall face; protection point 8.0 kN per lane; top anchor 12.0 kN per lane; auto-belay 12.0 kN per device; climber 1.0 kN per lane; global case falls in 1 of 2 adjacent lanes.
