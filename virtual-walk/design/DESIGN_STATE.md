# Active Space Hat Yai: design state (model mz19, 28 Nov 2026)

Live 3D model: https://hdy-active-space.vercel.app/model/ (orbit, cut slider, layer toggles, walk mode)
Repo: github.com/natdanai2707/climbing-gym-projection, branch `virtual-walk`

## Where the data is

| Path | What |
|---|---|
| `virtual-walk/model/geo.json` + `geo.bin` | Current geometry (mz19), the source of truth |
| `virtual-walk/design/base/` | Base geometry before the front-L2 redesign |
| `virtual-walk/design/tools/build_model.py` | Builds mz19 from base (`SRC`, `OUT` env vars). Output is byte-identical to the live model |
| `virtual-walk/design/tools/geo.py` | `load(dir)` gives `(mats, chunks)`, `save(dir, mats, chunks)` |
| `virtual-walk/design/tools/comps.py` | `python3 comps.py <dir> x0,x1,y0,y1,z0,z1 [key filter]` lists connected parts with bounding boxes |
| `airtight.py`, `audit_*.py`, `overlap_chk.py` | AC seal check, floating-item, guardrail-gap and clash audits |

### geo format
- `geo.json`: `{mats:{key:{color,rough,metal,glass,emit,names}}, chunks:[{k,p,n,i,c,b,mn,ex,(t,tn)}]}`.
- Vertices are uint16, quantized in the box `mn..mn+ex`. Indices are u16, or u32 when `b=1`. `t`/`tn` hold instance offsets (foliage).
- The material key is `layer#(r, g, b)|rough|metal|glass|emit`.
  - Layers: roof, structure, upper, wall, ceiling, duct, climb, interior, services, outside, site.
  - Steel structure key: `structure#(0.1, 0.025, 0.025)|0.75|0|0|0`. Red steel (front L2, rails): `interior#(0.25, 0.025, 0.025)|0.75|0|0|0`.
- Coordinates are in metres, z-up (Blender). The viewer uses three.js `(x, z, -y)`.

## Coordinate system and levels
- x runs from the front facade (x = -4.99, street side, west) to the rear wall (x ≈ 17.0, east).
- y runs along the building. End walls are at y = 67.58 (climbing / south) and y = 117.63 (Edge / north).

| Level | Value |
|---|---|
| Street | +0.2 |
| Ground floor | +1.0 |
| Front L2 terraces (by y) | 66.1–74.9 +3.4 · 74.9–77.9 +3.6 · 77.9–82.4 +3.8 · 82.4–85.4 +4.0 · 85.4–100.62 +4.2 · 100.62–103.62 +4.0 · 103.62–108.12 +3.8 · 108.12–111.12 +3.6 · 111.12–119.1 +3.4 |
| L2 bouldering deck | +6.30 (slab 6.0–6.3, x -1.45–12.26, y 69.54–74.15) |
| Co-working mezzanine | +4.2 |
| WC block / Edge rooms | +3.6 |

## Main building frame (existing, from the model)
- Portal frames on grid y = 67.75, 74.65, 81.55, 88.45, 97.45, 104.05, 110.65, 117.25.
- Columns are H300-class at x = -4.84 (front) and x = 16.86 (rear). Span is about 21.7 m.
  - Climbing zone (y 67.75–88.45): columns to +15.0.
  - Low zone (y 97.45–117.25): columns to +7.0.
- Gable rafters: ridge at x = 6.0, 5° pitch. Rafter underside z = 7.53 - |x-6|·0.0888 on the low zone frames.
- The 9 m bay between 88.45 and 97.45 is the entrance / lobby.

## Front L2 (new steel mezzanine along the facade, designed in this model)
- Plan:
  - The red ribbon zig-zag edge is defined by `PLAN` in build_model.py (y, x_west, x_east). The inner edge runs from x -1.99 to x -0.09.
  - Inside the end walls the deck runs out to the facade line (x -4.99).
  - Wings overhang 1.5 m past both end walls, full width to x -4.99.
- Deck: finish + 12 mm plate, edge beams 100×200, joists 80×150 at ≤1.2 m, riser plates at the terrace steps.
- Supports:
  - Outer side: the building's own front columns.
  - Inner side: 150×150 columns on the building grid.
  - At the entrance bay: 2 columns on the glass line (x -1.85, y 91.0 and 95.0). The inner columns at y 91/95 were removed.
  - Cross beams 150×300 on every grid line, from the facade to the inner column.
- Fascia: 6 mm plate on the outer face only, z = und(y)+0.35 to und(y)+0.80, parallel to the original sloped soffit.
- Guards: 1.1 m on the front L2. L2 bouldering guards are 0.84 m to match the original.
- Barriers and partitions:
  - Full-height barrier at y 88.4 (central zone | climbing side).
  - Glass partition with a double door at y 97.56 (central | Edge side), with gypsum above it up to the rafter underside.
- AC: the front L2 is sealed. Glass runs up to the deck plate and glass sits behind the courtyard screens (airtight.py reports SEALED).

## Stairs
- Scissor stair inside the glass line. Climbing floor +1.0 up to a shared landing +3.8 at y 77.66–78.56. From the landing, the upper flight goes to the L2 bouldering edge (+6.3, y 74.15).
  - Lower flight: x -0.45–0.5.
  - Upper flight: x -1.45 to -0.5.
- Central spiral: centre (1.31, 95.38), R 1.4, 220° clockwise, +1.0 to +4.2. It arrives at the walkway (x -0.09–2.09, y 95.5–97.53, +4.2).

## Open items for the steel design
- None of the member sizes above are engineered. They are placeholders for look and coordination only.
- Pre-existing issues the audits flagged and left alone:
  - One WC grab bar floats at y 92.5.
  - Small rower parts are flagged (audit false positives).
