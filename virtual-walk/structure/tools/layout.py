# Active Space Hat Yai: structural layout (phase 2).
# Builds every steel member as a centreline with role, system, assembly, phase and a PRELIMINARY section.
# Sections here are layout placeholders sized by rule of thumb; phase 3 (sizing.py) replaces them.
# Coordinates: metres, z-up, same as virtual-walk/model (mz19). Output: structure/out/layout.json
import json, math, os
import numpy as np

OUT = os.path.join(os.path.dirname(__file__), '..', 'out')
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- grids and levels
GY = [67.75, 74.65, 81.55, 88.45, 97.45, 104.05, 110.65, 117.25]   # grid 1..8
GN = [str(i + 1) for i in range(8)]
XA, XB, XR = -4.84, 16.86, 6.0                                       # grid A (front), B (rear), ridge
SLOPE = math.tan(math.radians(5.0))
EAVE_HI, EAVE_LO = 15.0, 7.0          # top of steel at the column line (from mz19)
BASE = 0.2                            # top of pedestal / base plate under main columns (column bottoms in mz19)
FFL = 1.0                             # ground floor finish inside the glass line
HIGH = lambda y: y <= 88.46

def tos_roof(x, eave):               # top of rafter steel (= underside of purlins)
    return eave + (10.84 - abs(x - XR)) * SLOPE

# front L2 plan / terraces (copied from design/tools/build_model.py, mz19)
PLAN = [(66.1, -3.99, -1.99), (74.9, -3.99, -1.99), (80.9, -3.24, -1.24), (82.4, -3.24, -1.24), (88.4, -2.09, -0.09),
        (97.62, -2.09, -0.09), (103.62, -3.24, -1.24), (105.12, -3.24, -1.24), (111.12, -3.99, -1.99), (119.1, -3.99, -1.99)]
TER = [(66.1, 74.9, 3.4), (74.9, 77.9, 3.6), (77.9, 80.9, 3.8), (80.9, 82.4, 3.8), (82.4, 85.4, 4.0), (85.4, 88.4, 4.2),
       (88.4, 97.62, 4.2), (97.62, 100.62, 4.2), (100.62, 103.62, 4.0), (103.62, 105.12, 3.8), (105.12, 108.12, 3.8),
       (108.12, 111.12, 3.6), (111.12, 119.1, 3.4)]
xe = lambda y: float(np.interp(y, [p[0] for p in PLAN], [p[2] for p in PLAN]))
lvl = lambda y: [t for a, b, t in TER if a <= y < b or (y == 119.1 and b == 119.1)][0]
XF = -4.99                             # facade line / deck outer edge

# floor build-up (decision D1, recommended): finish 20 + composite slab 120 (metal deck 0.9 mm + concrete) on steel
FIN, SLAB = 0.02, 0.12
tos_floor = lambda top: round(top - FIN - SLAB, 3)

# ---------------------------------------------------------------- sections (PRELIMINARY)
# H: h,b,tw,tf | C (lipped channel): h,b,c,t | SHS: b,t | CHS: d,t | RB: d | L: a,t | PL: w,t | FB: w,t
SEC = {}
def H(h, b, tw, tf): n = f'H{h}x{b}x{tw:g}x{tf:g}'; SEC[n] = dict(t='H', h=h, b=b, tw=tw, tf=tf); return n
def CL(h, b, c, t): n = f'C{h}x{b}x{c}x{t:g}'; SEC[n] = dict(t='C', h=h, b=b, c=c, tw=t, tf=t); return n
def SHS(b, t): n = f'SHS{b}x{b}x{t:g}'; SEC[n] = dict(t='SHS', h=b, b=b, tw=t); return n
def RHS(h, b, t): n = f'RHS{h}x{b}x{t:g}'; SEC[n] = dict(t='SHS', h=h, b=b, tw=t); return n
def CHS(d, t): n = f'CHS{d:g}x{t:g}'; SEC[n] = dict(t='CHS', h=d, b=d, tw=t); return n
def RB(d): n = f'RB{d}'; SEC[n] = dict(t='CHS', h=d, b=d, tw=d / 2); return n
def PL(w, t): n = f'PL{t:g}x{w}'; SEC[n] = dict(t='PL', h=w, b=t); return n
import re
def secdef(n):
    v = [float(x) for x in re.findall(r'[\d.]+', n)]; iv = lambda x: int(x) if x == int(x) else x
    if n.startswith('H'): return H(*map(iv, v[:4]))
    if n.startswith('C') and not n.startswith('CHS'): return CL(*map(iv, v[:4]))
    if n.startswith('SHS'): return SHS(iv(v[0]), v[2])
    if n.startswith('RHS'): return RHS(iv(v[0]), iv(v[1]), v[2])
    if n.startswith('CHS'): return CHS(v[0], v[1])
    if n.startswith('RB'): return RB(int(v[0]))
    if n.startswith('PL'): return PL(iv(v[1]), v[0])
    raise ValueError(n)
_SZ = os.path.join(OUT, 'sizes.json')
SIZES = json.load(open(_SZ)) if os.path.exists(_SZ) and os.environ.get('PRELIM') != '1' else {}
def G(grp, default):
    return secdef(SIZES[grp]) if grp in SIZES else default

# design groups -> section (out/sizes.json from sizing.py overrides the preliminary default)
FG = {'1': 'HI_END', '2': 'HI', '3': 'HI', '4': 'STEP', '5': 'LO_MEZZ', '6': 'LO', '7': 'LO', '8': 'LO_END'}
FDEF = {'HI_END': (H(588, 300, 12, 20), H(500, 200, 10, 16)), 'HI': (H(588, 300, 12, 20), H(500, 200, 10, 16)),
        'STEP': (H(588, 300, 12, 20), H(500, 200, 10, 16)), 'LO_MEZZ': (H(400, 200, 8, 13), H(400, 200, 8, 13)),
        'LO': (H(400, 200, 8, 13), H(400, 200, 8, 13)), 'LO_END': (H(400, 200, 8, 13), H(400, 200, 8, 13))}
FSEC = {k: (G(f'MF_{k}_COL', c), G(f'MF_{k}_RAF', r)) for k, (c, r) in FDEF.items()}
S_COL_HI, S_RAF_HI = FSEC['HI']; S_COL_LO, S_RAF_LO = FSEC['LO']
S_RAF_STEP_LO = G('MF_STEP_LRAF', H(400, 200, 8, 13))
S_GP1 = G('WP_G1', H(300, 150, 6.5, 9)); S_GP8 = G('WP_G8', H(300, 150, 6.5, 9)); S_GP4 = G('WP_G4', H(300, 150, 6.5, 9))
S_GPB = G('WP_B', H(300, 150, 6.5, 9)); S_GPOST = S_GP1
S_PUR = G('PUR', CL(150, 65, 20, 3.2))
S_PUR9 = G('PUR9', CL(200, 75, 20, 3.2))
S_GIRT = G('GIRT', CL(150, 65, 20, 3.2))
S_EAVE = G('EAVE_HI', CL(150, 65, 20, 3.2)); S_EAVE_LO = G('EAVE_LO', CL(150, 65, 20, 3.2))
S_STRUT = G('STRUT_ROOF', CHS(114.3, 4.5)); S_STRUT_W = G('STRUT_WALL', CHS(114.3, 4.5))
S_ROD = G('ROD_ROOF_HI', RB(20)); S_ROD_LO = G('ROD_ROOF_LO', RB(20)); S_RODW = G('ROD_WALL_HI', RB(24)); S_RODW_LO = G('ROD_WALL_LO', RB(20))
S_SAG = RB(12)
S_FL2_X = G('FL2_X', H(300, 150, 6.5, 9))      # front L2 cross beam on grid
S_FL2_E = G('FL2_E', H(250, 125, 6, 9))        # front L2 edge beams
S_FL2_S = G('FL2_S', H(250, 125, 6, 9))        # step beams
S_FL2_W = G('FL2_E', H(250, 125, 6, 9))        # wing cantilevers = continuation of the edge beams (same section)
S_FL2_J = G('FL2_J', H(200, 100, 5.5, 8))      # front L2 joists
S_FL2_C = G('FL2_C', SHS(150, 6))              # front L2 inner column ("เสา 150")
S_BD_G = G('BD_G', H(700, 300, 13, 24))        # bouldering deck north girder (13.45 m clear, no column in the fall zone)
S_BD_J = G('BD_J', H(300, 150, 6.5, 9)); S_BD_S = G('BD_S', H(300, 150, 6.5, 9))
S_BD_C = G('BD_C', H(250, 250, 9, 14)); S_BD_P = G('BD_P', SHS(150, 6)); S_BD_BR = G('BD_BR', CHS(114.3, 4.5))
S_CM_B = G('CM_B9', H(400, 200, 8, 13))        # co-working mezzanine 9.0 m beams
S_CM_P = G('CM_P', H(400, 200, 8, 13))         # mezz primary beams on grid 4 / 5
S_CM_C = G('CM_C', H(200, 200, 8, 12))
S_BR_B = G('BR_B', H(300, 150, 6.5, 9)); S_BR_J = G('BR_J', H(200, 100, 5.5, 8))
S_STR = G('ST_STR', H(250, 125, 6, 9)); S_STL = G('ST_LB', H(200, 100, 5.5, 8)); S_STP = G('ST_POST', SHS(100, 4.5))
S_SPC = G('SP_COL', CHS(216.3, 8.2)); S_SPA = G('SP_ARM', H(150, 75, 5, 7))
S_POST = SHS(50, 3.2)              # guard posts
S_RAIL = CHS(48.6, 3.2)
S_FASC = PL(450, 6)
S_GF = RHS(100, 50, 3.2)           # glass / partition frame
S_BRC = CHS(114.3, 4.5)            # deck side bracing

# main columns sit flush with the outer cladding line (outer flange face x -4.98 / +17.00), not centred on the grid
XFACE_A, XFACE_B = -4.98, 17.00
def xcol(sec, side):
    h = SEC[sec]['h'] / 1000
    return round(XFACE_A + h / 2, 3) if side == 'A' else round(XFACE_B - h / 2, 3)
# ---------------------------------------------------------------- member store
M = []
def mem(prefix, system, asm, phase, p0, p1, sec, role, web=None, grade='SS400', note='', ref=None):
    p0 = [round(float(v), 4) for v in p0]; p1 = [round(float(v), 4) for v in p1]
    if web is None:                      # default web direction: vertical for beams, x for columns
        d = np.subtract(p1, p0); d = d / np.linalg.norm(d)
        web = [1, 0, 0] if abs(d[2]) > 0.9 else [0, 0, 1]
    M.append(dict(pre=prefix, sys=system, asm=asm, ph=phase, p0=p0, p1=p1, sec=sec, role=role, web=list(map(float, web)),
                  grade=grade, note=note, ref=ref or ''))

def y_name(y):
    for g, n in zip(GY, GN):
        if abs(y - g) < 0.02: return n
    return f'y{y:.2f}'

# ================================================================ 1. main portal frames (phase 1)
for g, n in zip(GY, GN):
    hi = HIGH(g)
    E = EAVE_HI if hi else EAVE_LO
    sc, sr = FSEC[FG[n]]
    for x, side in ((xcol(sc, 'A'), 'A'), (xcol(sc, 'B'), 'B')):
        mem('C', 'MAIN', f'MF{n}', 1, [x, g, BASE], [x, g, E], sc, f'portal column {side}/{n}', web=[1, 0, 0],
            note='fixed base' if hi else 'pinned base')
    d = SEC[sr]['h'] / 1000
    for x0, x1, side in ((xcol(sc, 'A'), XR, 'A'), (XR, xcol(sc, 'B'), 'B')):
        z0 = tos_roof(x0, E) - d / 2; z1 = tos_roof(x1, E) - d / 2
        mem('R', 'MAIN', f'MF{n}', 1, [x0, g, z0], [x1, g, z1], sr, f'rafter {side}-ridge {n}')
        # haunch at the knee: 10 % of span, depth = rafter depth
        xh = x0 + 2.2 if side == 'A' else x1 - 2.2
        xk = x0 if side == 'A' else x1
        mem('HN', 'MAIN', f'MF{n}', 1, [xk, g, tos_roof(xk, E) - d - d / 2], [xh, g, tos_roof(xh, E) - d - d / 2], sr,
            f'haunch {side}/{n}', note='cut from rafter section, welded under rafter')
    if n == '4':                         # grid 4 also carries the low lobby roof at +7 (step frame)
        dl = SEC[S_RAF_STEP_LO]['h'] / 1000
        for x0, x1, side in ((xcol(sc, 'A'), XR, 'A'), (XR, xcol(sc, 'B'), 'B')):
            mem('R', 'MAIN', 'MF4', 1, [x0, g, tos_roof(x0, EAVE_LO) - dl / 2], [x1, g, tos_roof(x1, EAVE_LO) - dl / 2],
                S_RAF_STEP_LO, f'low rafter {side}-ridge 4 (lobby roof, end plate to high column)')
        for x in (0.6, 6.0, 11.4):        # clerestory posts +7 roof -> +15 rafter
            mem('WP', 'MAIN', 'MF4', 1, [x, g, tos_roof(x, EAVE_LO)], [x, g, tos_roof(x, EAVE_HI) - SEC[FSEC['STEP'][1]]['h'] / 1000],
                S_GP4, 'clerestory wind post 4', web=[0, 1, 0])

# gable wind posts: grid 1 (also carry the bouldering deck at +6.18) and grid 8
GP1 = [-1.40, 2.30, 6.00, 9.62]          # clear of the gable window x 9.72-14.61
GP8 = [0.60, 6.00, 11.40]
for g, n, xs, E in ((GY[0], '1', GP1, EAVE_HI), (GY[7], '8', GP8, EAVE_LO)):
    for x in xs:
        mem('WP', 'MAIN', f'MF{n}', 1, [x, g, BASE], [x, g, tos_roof(x, E) - SEC[FSEC['HI_END' if n == '1' else 'LO_END'][1]]['h'] / 1000],
            S_GP1 if n == '1' else S_GP8, f'gable wind post {n}', web=[0, 1, 0], note='pinned top (slotted for rafter deflection), pinned base')
# lobby rear wall: 9.0 m bay on grid B gets a mid wind post for the girts
mem('WP', 'MAIN', 'WB', 1, [XB, 92.95, BASE], [XB, 92.95, EAVE_LO], S_GPB, 'wind post B lobby bay', web=[1, 0, 0])

# ================================================================ 2. roof: purlins, sag rods, eave struts, bracing (phase 2)
def purlin_xs():
    xs = list(np.linspace(XA + 0.19, XR - 0.12, 10)) + list(np.linspace(XR + 0.12, XB - 0.19, 10))
    return [round(x, 3) for x in xs]
PX = purlin_xs()
COURT = (88.75, 95.5)                    # open courtyard roof cut-out west of the glass line (x < -1.98)
def roof_bays():
    out = []
    for i in range(7):
        y0, y1 = GY[i], GY[i + 1]
        out.append((y0, y1, EAVE_HI if i < 3 else EAVE_LO, f'{GN[i]}-{GN[i + 1]}'))
    return out
for y0, y1, E, bn in roof_bays():
    sp = S_PUR9 if (y1 - y0) > 8 else S_PUR
    hp = SEC[sp]['h'] / 1000
    for x in PX:
        if bn == '4-5' and x < -1.98: continue      # courtyard open to sky
        z = tos_roof(x, E) + hp / 2
        mem('P', 'ROOF', f'RF{bn}', 2, [x, y0, z], [x, y1, z], sp, f'purlin bay {bn}', web=[-math.sin(math.radians(5)) * np.sign(x - XR) or 0, 0, 1])
    # sag rods: 1 line at mid-span (2 lines at third points for 9 m), each slope eave->ridge
    ns = 2                                    # sag rods at third points (uplift: R-factor method needs them)
    for k in range(1, ns + 1):
        ys = y0 + (y1 - y0) * k / (ns + 1)
        for xa, xb in ((PX[0], PX[9]), (PX[10], PX[19])):
            mem('SR', 'ROOF', f'RF{bn}', 2, [xa, ys, tos_roof(xa, E) + hp / 2], [xb, ys, tos_roof(xb, E) + hp / 2], S_SAG, f'sag rod {bn}')
    if bn == '4-5':    # trimmer on the courtyard edge
        mem('P', 'ROOF', 'RF4-5', 2, [-1.80, y0, tos_roof(-1.80, E) + hp / 2], [-1.80, y1, tos_roof(-1.80, E) + hp / 2], S_PUR9, 'courtyard edge purlin')
# eave struts (in addition to the eave purlins), both sides, each zone
for (ya, yb, E) in ((GY[0], GY[3], EAVE_HI), (GY[3], GY[7], EAVE_LO)):
    for x in (XA, XB):
        for i in range(len(GY) - 1):
            if GY[i] >= ya - 0.01 and GY[i + 1] <= yb + 0.01:
                se = S_EAVE if E == EAVE_HI else S_EAVE_LO
                xs_ = xcol(FSEC['HI'][0] if E == EAVE_HI else FSEC['LO'][0], 'A' if x < 0 else 'B')
                mem('ES', 'ROOF', 'EAVE', 2, [xs_, GY[i], E - 0.25], [xs_, GY[i + 1], E - 0.25], se,
                    f'eave strut {"A" if x < 0 else "B"} {GN[i]}-{GN[i+1]}', web=[1, 0, 0])
# roof bracing: X rods per slope in braced bays, strut tubes on node lines
NODES = [XA, 0.58, XR, 11.43, XB]
for (i, E) in ((0, EAVE_HI), (2, EAVE_HI), (3, EAVE_LO), (6, EAVE_LO)):
    y0, y1 = GY[i], GY[i + 1]; bn = f'{GN[i]}-{GN[i + 1]}'
    for xa, xb in zip(NODES[:-1], NODES[1:]):
        za, zb = tos_roof(xa, E) - 0.1, tos_roof(xb, E) - 0.1
        rr = S_ROD if E == EAVE_HI else S_ROD_LO
        mem('RB', 'BRACE', f'RBR{bn}', 2, [xa, y0, za], [xb, y1, zb], rr, f'roof X-brace {bn}')
        mem('RB', 'BRACE', f'RBR{bn}', 2, [xa, y1, za], [xb, y0, zb], rr, f'roof X-brace {bn}')
    for x in NODES[1:-1]:
        z = tos_roof(x, E) - 0.1
        mem('ST', 'BRACE', f'RBR{bn}', 2, [x, y0, z], [x, y1, z], S_STRUT, f'roof strut {bn}')
# wall (vertical) bracing (P3): line B bay 3-4 (high), line B bay 7-8 (low), line A bay 3-4 only (high, tiers around the
# front L2 deck). Line A bays 1-2 / 7-8 clash with the facade counters on L2, so low-zone line A force travels along the +7
# eave strut into node A/4. Tiers: (z at y0, z at y1) per level.
def deck_tiers(y0, y1):
    lo0, lo1 = tos_floor(lvl(y0)) - SEC[S_FL2_E]['h'] / 1000, tos_floor(lvl(y1 - 0.01)) - SEC[S_FL2_E]['h'] / 1000
    return [(BASE, BASE), (lo0, lo1), (lvl(y0), lvl(y1 - 0.01)), (EAVE_LO, EAVE_LO), (EAVE_HI, EAVE_HI)]
VB = [('B', 2, EAVE_HI, [(BASE, BASE), (7.6, 7.6), (EAVE_HI, EAVE_HI)]), ('B', 6, EAVE_LO, [(BASE, BASE), (EAVE_LO, EAVE_LO)]),
      ('A', 2, EAVE_HI, deck_tiers(GY[2], GY[3]))]
for side, i, E, tiers in VB:
    y0, y1 = GY[i], GY[i + 1]; bn = f'{side}{GN[i]}-{GN[i + 1]}'
    # brace plane just inboard of the inset girts (girt depth + 15 mm + half the brace)
    rb = SEC[S_RODW if E == EAVE_HI else S_RODW_LO]['h'] / 2000; hg = SEC[S_GIRT]['h'] / 1000
    x = XFACE_A + 0.025 + hg + 0.015 + rb if side == 'A' else XFACE_B - 0.025 - hg - 0.015 - rb
    rod = S_RODW if E == EAVE_HI else S_RODW_LO
    for (a0, a1), (b0, b1) in zip(tiers[:-1], tiers[1:]):
        if b0 - a0 < 1.0:          # deck zone: the slab / edge beam is the strut, no rods
            continue
        mem('VB', 'BRACE', f'VBR{bn}', 2, [x, y0, a0], [x, y1, b1], rod, f'wall X-brace {bn}', web=[1, 0, 0])
        mem('VB', 'BRACE', f'VBR{bn}', 2, [x, y1, a1], [x, y0, b0], rod, f'wall X-brace {bn}', web=[1, 0, 0])
    for z0_, z1_ in tiers[1:-1]:
        if abs(z0_ - EAVE_LO) < 0.01 or abs(z0_ - 7.6) < 0.01:
            xs_ = XFACE_A + 0.025 + hg + 0.015 + SEC[S_STRUT_W]['h'] / 2000 if side == 'A' else XFACE_B - 0.025 - hg - 0.015 - SEC[S_STRUT_W]['h'] / 2000
            mem('ST', 'BRACE', f'VBR{bn}', 2, [xs_, y0, z0_], [xs_, y1, z1_], S_STRUT_W, f'wall strut {bn}', web=[1, 0, 0])

# ================================================================ 3. girts (phase 2)
def girt_levels(z0, z1, start=2.2, step=1.5):
    zs = []; z = start
    while z < z1 - 0.3:
        if z > z0: zs.append(round(z, 3))
        z += step
    return zs
FL2_ZONE = lambda y: (tos_floor(lvl(y)) - 0.35, lvl(y) + 1.2)     # no girt behind the front L2 deck / guard zone
for x, side in ((XA, 'A'), (XB, 'B')):
    for i in range(7):
        y0, y1 = GY[i], GY[i + 1]; E = EAVE_HI if i < 3 else EAVE_LO
        if side == 'A' and i == 3: continue                     # lobby bay A: courtyard screen frame (by GF)
        stops = [y0, y1] if not (side == 'B' and i == 3) else [y0, 92.95, y1]
        for za in girt_levels(BASE, E):
            if side == 'A':                             # facade below +L2 is the open arcade; first girt clears the L2 counters (top +1.05)
                mx = max(lvl(yy) for yy in np.linspace(y0 + 0.01, y1 - 0.01, 12))
                if za < mx + 1.15: continue
            for ya, yb in zip(stops[:-1], stops[1:]):
                hg = SEC[S_GIRT]['h'] / 1000          # inset girt: cladding sits on the column face, girt between the flanges
                xo = XFACE_A + 0.025 + hg / 2 if side == 'A' else XFACE_B - 0.025 - hg / 2
                mem('G', 'WALL', f'GT{side}{GN[i]}-{GN[i+1]}', 2, [xo, ya, za], [xo, yb, za], S_GIRT, f'girt {side} {GN[i]}-{GN[i+1]}', web=[1, 0, 0],
                    note='inset between column flanges, cleat to column web')
for g, n, xs, E in ((GY[0], '1', GP1, EAVE_HI), (GY[7], '8', GP8, EAVE_LO)):
    posts = [XA] + xs + [XB]
    yo = g if n == '1' else g + SEC[S_GP8]['h'] / 2000 + SEC[S_GIRT]['h'] / 2000   # grid 1: inset in the post depth; grid 8: on the outer flange
    for xa, xb in zip(posts[:-1], posts[1:]):
        for za in girt_levels(BASE, min(tos_roof(xa, E), tos_roof(xb, E))):
            if xa < -1.97 and za < 3.7: continue    # gable end of the street arcade is open below the front L2
            mem('G', 'WALL', f'GT{n}', 2, [xa, yo, za], [xb, yo, za], S_GIRT, f'gable girt {n}', web=[0, 1, 0])
posts = [XA, 0.6, 6.0, 11.4, XB]
for xa, xb in zip(posts[:-1], posts[1:]):       # grid 4 clerestory
    z = EAVE_LO + 1.2
    while z < min(tos_roof(xa, EAVE_HI), tos_roof(xb, EAVE_HI)) - 0.6:
        mem('G', 'WALL', 'GT4', 2, [xa, GY[3], z], [xb, GY[3], z], S_GIRT, 'clerestory girt 4', web=[0, 1, 0]); z += 1.5

# ================================================================ 4. front L2 mezzanine (phase 3)
FL2_COLS = []
for g in GY:
    x = xe(g) - 0.1
    if abs(x + 1.97) < 0.12: x = -1.97 + (0.13 if x > -1.97 else -0.13)      # clear of the glass line
    FL2_COLS.append((round(x, 3), g))
FL2_COLS += [(-1.85, 91.0), (-1.85, 95.0)]
FL2_BASE = {67.75: 0.2, 74.65: 0.2, 81.55: 1.0, 88.45: 1.1, 97.45: 1.0, 104.05: 1.0, 110.65: 0.0, 117.25: 0.0, 91.0: 1.0, 95.0: 1.0}
dX, dE, dJ = SEC[S_FL2_X]['h'] / 1000, SEC[S_FL2_E]['h'] / 1000, SEC[S_FL2_J]['h'] / 1000
for (x, y) in FL2_COLS:
    t = tos_floor(lvl(y)); top = t - (dX if y in GY else dE)
    mem('C', 'FL2', f'FL2-{y_name(y)}', 3, [x, y, FL2_BASE[y]], [x, y, top], S_FL2_C, f'front L2 inner column {y_name(y)}', web=[1, 0, 0])
for (x, y) in FL2_COLS:
    if y not in GY: continue
    t = tos_floor(lvl(y))
    mem('B', 'FL2', f'FL2-{y_name(y)}', 3, [XFACE_A + SEC[S_COL_HI if HIGH(y) else S_COL_LO]['h'] / 1000, y, t - dX / 2], [xe(y) - 0.05, y, t - dX / 2], S_FL2_X,
        f'front L2 cross beam {y_name(y)} (column A flange -> inner edge)', note='end plate to column A flange; inner end on SHS cap plate')
# edge / step / joist layout per terrace segment
STEPS = sorted(set([a for a, b, t in TER] + [119.1]))
segs = []
for a, b, top in TER:
    cuts = sorted(set([a, b] + [g for g in GY if a < g < b]))
    for ya, yb in zip(cuts[:-1], cuts[1:]):
        segs.append((ya, yb, top))
for ya, yb, top in segs:
    t = tos_floor(top)
    if 88.4 <= ya < 97.62 and ya >= 88.4:       # entrance bay: outer zone only where the floor exists (courtyard hole)
        pass
    # inner edge beam
    mem('B', 'FL2', f'FL2-T{top:.1f}', 3, [xe(ya) - 0.07, ya, t - dE / 2], [xe(yb) - 0.07, yb, t - dE / 2], S_FL2_E, f'front L2 inner edge beam y{ya:.2f}-{yb:.2f}')
    # outer edge beam on the column line (skip across the courtyard)
    if not (90.4 <= ya and yb <= 95.5):
        oa, ob = max(ya, 90.4) if ya >= 90.4 else ya, yb
        if 88.4 <= ya < 90.4 and yb > 90.4: ob = 90.4
        if 95.5 > ya and yb > 95.5 and ya >= 88.4: oa = 95.5
        mem('B', 'FL2', f'FL2-T{top:.1f}', 3, [XA, oa, t - dE / 2], [XA, ob, t - dE / 2], S_FL2_E, f'front L2 outer edge beam y{oa:.2f}-{ob:.2f}', web=[0, 0, 1],
            note='fin plate to column A web side')
    # joists @ <= 2.3 m (composite deck span)
    n = max(1, math.ceil((yb - ya) / 2.3))
    for j in range(1, n):
        yy = ya + (yb - ya) * j / n
        xw = XA if not (90.4 < yy < 95.5) else -2.09
        mem('J', 'FL2', f'FL2-T{top:.1f}', 3, [xw + 0.1, yy, t - dJ / 2], [xe(yy) - 0.12, yy, t - dJ / 2], S_FL2_J, f'front L2 joist y{yy:.2f}')
# step beams at terrace changes (not on a grid): beam at the lower level, 200 mm welded upstand carries the upper slab edge
for (a, b, top), (a2, b2, top2) in zip(TER[:-1], TER[1:]):
    if abs(top - top2) < 0.01 or any(abs(b - g) < 0.05 for g in GY): continue
    lo = tos_floor(min(top, top2))
    dS = SEC[S_FL2_S]['h'] / 1000
    mem('B', 'FL2', f'FL2-S{b:.2f}', 3, [XA + 0.1, b, lo - dS / 2], [xe(b) - 0.07, b, lo - dS / 2], S_FL2_S,
        f'front L2 step beam y{b:.2f} (+{min(top,top2):.1f}/+{max(top,top2):.1f})', note='PL10 upstand 200 mm welded on top flange')
# wings past both end walls (cantilever 1.65 m from grid 1 / grid 8)
for yg, yw, top in ((GY[0], 66.1, 3.4), (GY[7], 119.1, 3.4)):
    t = tos_floor(top)
    for x in (XA, xe(yg) - 0.07):
        mem('B', 'FL2', 'FL2-WING', 3, [x, yg, t - dE / 2], [x, yw + (0.05 if yw < yg else -0.05), t - dE / 2], S_FL2_W, 'wing cantilever beam',
            web=[0, 0, 1], note='continuous over grid, back-span to first joist')
    mem('B', 'FL2', 'FL2-WING', 3, [XF + 0.05, yw + (0.05 if yw < yg else -0.05), t - dE / 2], [xe(yw) - 0.05, yw + (0.05 if yw < yg else -0.05), t - dE / 2], S_FL2_E, 'wing end beam')
# fascia plate on the facade face + brackets @ 1.2 m
UND = [(66.1, 2.8), (74.9, 2.8), (80.9, 3.2), (82.4, 3.2), (88.4, 3.6), (97.62, 3.6), (103.62, 3.2), (105.12, 3.2), (111.12, 2.8), (119.1, 2.8)]
und = lambda y: float(np.interp(y, [u[0] for u in UND], [u[1] for u in UND]))
yk = [66.1] + [u[0] for u in UND[1:-1]] + [119.1]
for ya, yb in zip(yk[:-1], yk[1:]):
    mem('FP', 'FL2', 'FL2-FASCIA', 3, [XF - 0.003, ya, und(ya) + 0.575], [XF - 0.003, yb, und(yb) + 0.575], S_FASC, 'fascia plate 6 mm', web=[0, 0, 1], note='z und+0.35..und+0.80')
# guard on the inner edge (posts @1.2 m, CHS top rail at +1.1)
OPEN = [(77.6, 78.6), (95.5, 97.62)]
for ya, yb, top in segs:
    n = max(1, math.ceil((yb - ya) / 1.2))
    for j in range(n):
        yy = ya + (yb - ya) * (j + 0.5) / n
        if any(a <= yy <= b for a, b in OPEN): continue
        mem('HP', 'MISC', 'HR-FL2', 6, [xe(yy) - 0.03, yy, top], [xe(yy) - 0.03, yy, top + 1.1], S_POST, 'guard post front L2', web=[1, 0, 0])
    if not any(a < (ya + yb) / 2 < b for a, b in OPEN):
        mem('HR', 'MISC', 'HR-FL2', 6, [xe(ya) - 0.03, ya, top + 1.1], [xe(yb) - 0.03, yb, top + 1.1], S_RAIL, 'top rail front L2')

# ================================================================ 5. L2 bouldering deck +6.3 (phase 4)
BD_TOP = 6.3; tb = tos_floor(BD_TOP); dG, dJb = SEC[S_BD_G]['h'] / 1000, SEC[S_BD_J]['h'] / 1000
BDN = 74.05
mem('C', 'BD', 'BD', 4, [-1.35, BDN, FFL], [-1.35, BDN, tb - dG], S_BD_C, 'bouldering deck column NW', web=[0, 1, 0])
mem('C', 'BD', 'BD', 4, [12.10, BDN, FFL], [12.10, BDN, tb - dG], S_BD_C, 'bouldering deck column NE', web=[0, 1, 0])
mem('B', 'BD', 'BD', 4, [-1.35, BDN, tb - dG / 2], [12.10, BDN, tb - dG / 2], S_BD_G, 'bouldering deck north girder (13.45 m)',
    note='no column in the fall zone; option: SM520 H600x300')
dS_ = SEC[S_BD_S]['h'] / 1000
mem('B', 'BD', 'BD', 4, [-1.40, GY[0] + 0.25, tb - dS_ / 2], [12.20, GY[0] + 0.25, tb - dS_ / 2], S_BD_S, 'bouldering deck south beam on gable posts')
mem('C', 'BD', 'BD', 4, [12.20, 67.95, FFL], [12.20, 67.95, tb - dS_], S_BD_P, 'deck SE post (inside the gable glass, gap glass 67.71 / wall 68.06)', web=[1, 0, 0])
xs = np.linspace(-1.35, 12.10, 7)
for x in xs:
    mem('J', 'BD', 'BD', 4, [x, GY[0] + 0.3, tb - dJb / 2], [x, BDN - 0.15, tb - dJb / 2], S_BD_J, f'bouldering deck joist x{x:.2f}')
for x in (-1.40, 12.15):    # N-S bracing in the deck side planes (inside the wall cavity, confirm with wall builder)
    mem('VB', 'BD', 'BD', 4, [x, GY[0] + 0.3, FFL + 0.2], [x, BDN - 0.2, tb - dG], S_BD_BR, 'deck side brace (N-S)')
for x0, x1 in ((-1.45, 12.26),):
    for xx in np.arange(-1.40, 12.26, 1.2):
        if -1.45 <= xx <= -0.5 or -0.5 < xx < 1.32 and False: pass
    mem('HR', 'MISC', 'HR-BD', 6, [-1.475, 69.56, BD_TOP + 0.84], [-1.475, 74.13, BD_TOP + 0.84], S_RAIL, 'deck guard west (0.84)')
    mem('HR', 'MISC', 'HR-BD', 6, [-0.48, 74.13, BD_TOP + 0.84], [1.32, 74.13, BD_TOP + 0.84], S_RAIL, 'deck guard north (0.84)')

# ================================================================ 6. co-working mezzanine +4.2 and bridge (phase 4)
CM_TOP = 4.2; tc = tos_floor(CM_TOP); dB = SEC[S_CM_B]['h'] / 1000; dP = SEC[S_CM_P]['h'] / 1000
CMX = [8.15, 11.60]            # P3: clear spots on grid 4 / 5 (checked against the mz19 ground floor: counter, WC partitions)
CMW = 6.76                     # mezz west edge beam (slab edge x 6.71)
XBC = xcol(FSEC['LO_MEZZ'][0], 'B') - SEC[FSEC['LO_MEZZ'][0]]['h'] / 2000     # inner flange face of column B/4, B/5
for g in (GY[3], GY[4]):
    for x in CMX:
        mem('C', 'CM', f'CM-{y_name(g)}', 4, [x, g, FFL], [x, g, tc - dP], S_CM_C, f'mezz column {y_name(g)}', web=[1, 0, 0])
    xcb = xcol(FSEC['STEP' if g == GY[3] else 'LO_MEZZ'][0], 'B') - SEC[FSEC['STEP' if g == GY[3] else 'LO_MEZZ'][0]]['h'] / 2000
    pts = [CMW] + CMX + [xcb]
    for xa, xb in zip(pts[:-1], pts[1:]):
        mem('B', 'CM', f'CM-{y_name(g)}', 4, [xa, g, tc - dP / 2], [xb, g, tc - dP / 2], S_CM_P,
            f'mezz primary beam {y_name(g)}' + (' (cantilever)' if xa == CMW else ''),
            note='end plate to main column B flange' if xb > 16 else ('continuous over column, cantilever 1.39 m' if xa == CMW else ''))
for x in np.linspace(CMW, 16.66, 6):
    mem('B', 'CM', 'CM', 4, [x, GY[3] + 0.1, tc - dB / 2], [x, GY[4] - 0.1, tc - dB / 2], S_CM_B, f'mezz 9.0 m beam x{x:.2f}', web=[0, 0, 1])
# bridge x -0.09 -> mezz, y 95.5-97.6, level +4.2 (D8: the +4.2 grey slab south of grid 4 is a room roof only, no steel)
dBr = SEC[S_BR_B]['h'] / 1000
mem('B', 'BR', 'BR', 4, [-0.19, GY[4], tc - dBr / 2], [CMW, GY[4], tc - dBr / 2], S_BR_B, 'bridge north beam (grid 5)', note='on mezz primary beam cantilever tip')
mem('B', 'BR', 'BR', 4, [-0.12, 95.55, tc - dBr / 2], [CMW, 95.55, tc - dBr / 2], S_BR_B, 'bridge south beam (y 95.55)', note='ends on front L2 edge beam and mezz edge beam; spiral head tied in')
for x in (1.6, 3.4, 5.1):
    mem('J', 'BR', 'BR', 4, [x, 95.6, tc - SEC[S_BR_J]['h'] / 2000], [x, GY[4] - 0.05, tc - SEC[S_BR_J]['h'] / 2000], S_BR_J, 'bridge joist')
mem('HR', 'MISC', 'HR-BR', 6, [1.27, 95.5, CM_TOP + 1.1], [2.09, 95.5, CM_TOP + 1.1], S_RAIL, 'walkway guard south')

# ================================================================ 7. stairs (phase 5)
# 7a scissor stair (from mz19): lower flight +1.0 -> landing +3.8, upper flight landing -> +6.3
YT, GO = 74.15, 0.27; YB = YT + 13 * GO; YF = YB - 15 * GO
for x in (-0.42, 0.47):
    mem('SS', 'STAIR', 'ST1', 5, [x, YB + 0.2, 3.8 - 0.2], [x, YF - 0.2, FFL + 0.05], S_STR, 'scissor stair lower flight stringer', web=[0, 0, 1])
for x in (-1.42, -0.53):
    mem('SS', 'STAIR', 'ST1', 5, [x, YT, 6.3 - 0.2], [x, YB + 0.2, 3.8 - 0.2], S_STR, 'scissor stair upper flight stringer', web=[0, 0, 1])
FX0 = xe(YB + 0.45) - 0.02
for yy in (YB, YB + 0.9):
    mem('SB', 'STAIR', 'ST1', 5, [FX0, yy, 3.8 - 0.05 - SEC[S_STL]['h'] / 2000], [0.5, yy, 3.8 - 0.05 - SEC[S_STL]['h'] / 2000], S_STL, 'scissor landing beam')
mem('SC', 'STAIR', 'ST1', 5, [-1.30, YB + 0.82, FFL], [-1.30, YB + 0.82, 3.8 - 0.05 - SEC[S_STL]['h'] / 1000], S_STP, 'landing post', web=[1, 0, 0])
for x in (-1.45, -0.5):
    mem('HR', 'MISC', 'HR-ST1', 6, [x, YT, 6.3 + 0.9], [x, YB, 3.8 + 0.9], S_RAIL, 'stair handrail upper')
for x in (-0.45, 0.5):
    mem('HR', 'MISC', 'HR-ST1', 6, [x, YB, 3.8 + 0.9], [x, YF, FFL + 0.9], S_RAIL, 'stair handrail lower')
# 7b spiral (centre column, 18 cantilever treads 220 deg cw, +1.0 -> +4.2)
CX, CY, R = 1.31, 95.38, 1.4
mem('SC', 'STAIR', 'ST2', 5, [CX, CY, FFL], [CX, CY, 4.2 + 1.0], S_SPC, 'spiral centre column', web=[1, 0, 0], note='base plate + 4 anchors to slab/footing; head tied to bridge south beam')
SW = math.radians(220); A0 = math.pi + SW; N = 18; d = SW / N
for i in range(N):
    a = A0 - (i + 0.5) * d; z = FFL + (i + 1) * (4.2 - FFL) / N - 0.03
    mem('TR', 'STAIR', 'ST2', 5, [CX + 0.11 * math.cos(a), CY + 0.11 * math.sin(a), z], [CX + R * math.cos(a), CY + R * math.sin(a), z], S_SPA,
        f'spiral tread arm {i+1}', note='folded PL6 tread on arm (or PL tread welded to column)')
pts = [(CX + (R - 0.05) * math.cos(A0 - k * d), CY + (R - 0.05) * math.sin(A0 - k * d), FFL + k * (4.2 - FFL) / N + 0.95) for k in range(N + 1)]
for p, q in zip(pts[:-1], pts[1:]):
    mem('HR', 'MISC', 'HR-ST2', 6, p, q, S_RAIL, 'spiral helical rail')

# ================================================================ 8. secondary: glass / partition frames, barrier (phase 6)
for y in (90.37, 95.53):     # courtyard glass +4.2 -> +8.4: mullion posts @ <=1.5 m between facade and glass line
    for x in np.linspace(-4.84, -1.99, 3):
        mem('GF', 'MISC', 'GF-COURT', 6, [x, y, 4.2], [x, y, 8.4], S_GF, 'courtyard glass mullion', web=[1, 0, 0])
    mem('GF', 'MISC', 'GF-COURT', 6, [-4.84, y, 8.35], [-1.99, y, 8.35], S_GF, 'courtyard glass head')
for x in np.linspace(-4.84, -0.09, 5):   # glass partition y 97.56 (+4.2 -> +6.3) and gypsum head support
    mem('GF', 'MISC', 'GF-97', 6, [x, 97.60, 4.2], [x, 97.60, 6.3], S_GF, 'Edge partition post', web=[0, 1, 0])
mem('GF', 'MISC', 'GF-97', 6, [-4.84, 97.60, 6.30], [16.86, 97.60, 6.30], RHS(100, 50, 3.2), 'partition head beam +6.3 (gypsum above to rafter 5)')
mem('GF', 'MISC', 'GF-88', 6, [-4.66, 88.40, 4.2 + 2.3], [xe(88.4) - 0.02, 88.40, 4.2 + 2.3], S_GF, 'full-height barrier head (h 2.3)')

# ---------------------------------------------------------------- numbering, lengths, weights
RHO = 7850.0
def area_mm2(s):
    d = SEC[s]
    if d['t'] == 'H': return 2 * d['b'] * d['tf'] + (d['h'] - 2 * d['tf']) * d['tw']
    if d['t'] == 'C': t = d['tw']; return t * (d['h'] + 2 * d['b'] + 2 * d['c'] - 4 * t)
    if d['t'] == 'SHS': t = d['tw']; return 2 * t * (d['h'] + d['b'] - 2 * t)
    if d['t'] == 'CHS':
        D, t = d['h'], d['tw']; return math.pi / 4 * (D ** 2 - (D - 2 * t) ** 2)
    if d['t'] == 'PL': return d['h'] * d['b']
for s in SEC: SEC[s]['A'] = round(area_mm2(s), 1); SEC[s]['kgm'] = round(SEC[s]['A'] * 1e-6 * RHO, 2)
def classify(m):
    r, p, s_, a = m['role'], m['pre'], m['sys'], m['asm']
    if s_ == 'MAIN':
        if p in ('C', 'R', 'HN'):
            n = a[2:]; k = FG.get(n, 'X')
            if 'low rafter' in r: return 'MF_STEP_LRAF'
            return f'MF_{k}_COL' if p == 'C' else f'MF_{k}_RAF'
        if p == 'WP': return {'MF1': 'WP_G1', 'MF8': 'WP_G8', 'MF4': 'WP_G4', 'WB': 'WP_B'}[a]
    if p == 'P': return 'PUR9' if '4-5' in a else 'PUR'
    if p == 'SR': return 'SAG'
    if p == 'ES': return 'EAVE_HI' if m['p0'][2] > 10 else 'EAVE_LO'
    if p == 'RB': return 'ROD_ROOF_HI' if m['p0'][2] > 10 else 'ROD_ROOF_LO'
    if p == 'VB' and s_ == 'BRACE': return 'ROD_WALL_HI' if a in ('VBRB3-4', 'VBRA3-4') else 'ROD_WALL_LO'
    if p == 'ST' and s_ == 'BRACE': return 'STRUT_ROOF' if a.startswith('RBR') else 'STRUT_WALL'
    if p == 'G': return 'GIRT'
    if s_ == 'FL2':
        if p == 'C': return 'FL2_C'
        if p == 'J': return 'FL2_J'
        if p == 'FP': return 'FL2_FASCIA'
        if 'cross beam' in r: return 'FL2_X'
        if 'step beam' in r: return 'FL2_S'
        if 'wing cantilever' in r: return 'FL2_W'
        return 'FL2_E'
    if s_ == 'BD':
        if 'girder' in r: return 'BD_G'
        if 'south beam' in r: return 'BD_S'
        if 'SE post' in r: return 'BD_P'
        if p == 'C': return 'BD_C'
        if p == 'J': return 'BD_J'
        if p == 'VB': return 'BD_BR'
    if s_ == 'CM':
        if p == 'C': return 'CM_C'
        if '9.0 m' in r: return 'CM_B9'
        return 'CM_P'
    if s_ == 'BR': return 'BR_J' if p == 'J' else 'BR_B'
    if s_ == 'STAIR':
        return {'SS': 'ST_STR', 'SB': 'ST_LB', 'TR': 'SP_ARM'}.get(p) or ('SP_COL' if 'spiral' in r else 'ST_POST')
    return 'MISC_' + p
cnt = {}
for m in M:
    m['grp'] = classify(m)
    L = float(np.linalg.norm(np.subtract(m['p1'], m['p0'])))
    cnt[m['pre']] = cnt.get(m['pre'], 0) + 1
    m['id'] = f"{m['pre']}{cnt[m['pre']]:03d}"
    m['L'] = round(L, 3); m['kg'] = round(L * SEC[m['sec']]['kgm'], 1)
lay = dict(version=os.environ.get('LAYVER', 'P3-r1'), grids=dict(y=dict(zip(GN, GY)), x=dict(A=XA, B=XB, R=XR)),
           levels=dict(base=BASE, ffl=FFL, eave_hi=EAVE_HI, eave_lo=EAVE_LO, bouldering=BD_TOP, mezz=CM_TOP, terraces=TER),
           sections=SEC, members=M)
json.dump(lay, open(os.path.join(OUT, 'layout.json'), 'w'), separators=(',', ':'))
if __name__ == '__main__':
    import collections
    by = collections.defaultdict(lambda: [0, 0.0])
    for m in M: by[m['sys']][0] += 1; by[m['sys']][1] += m['kg']
    tot = sum(v[1] for v in by.values())
    for k, v in by.items(): print(f'{k:6s} {v[0]:5d} members {v[1]/1000:8.2f} t')
    print(f'TOTAL {len(M)} members {tot/1000:.1f} t (preliminary, no connections)')
