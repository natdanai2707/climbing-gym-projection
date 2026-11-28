# Phase 3: loads, analysis and member sizing (AISC 360-16 LRFD, Direct Analysis Method for the portal frames).
# Reads out/layout.json (geometry), picks the lightest catalogue section per design group that passes strength,
# deflection, drift and vibration, writes out/sizes.json (consumed by layout.py) and out/calc.json (report data).
import json, math, os, itertools
import numpy as np
from steel import *
from frame2d import Frame

D = os.path.join(os.path.dirname(__file__), '..', 'out')
LAY = json.load(open(os.path.join(D, 'layout.json')))
MEM = LAY['members']
g9 = 9.81e-3                                    # kg -> kN
FY = 245.0; FU = 400.0; FY_CF = 245.0; FY_STK = 235.0; FY_ROD = 235.0; FU_ROD = 380.0

# ================================================================ design basis
BASIS = dict(
    method='AISC 360-16 LRFD; portal frames by the Direct Analysis Method (2nd-order P-Delta, 0.8EI/0.8EA, notional 0.002Yi, K=1)',
    combos=['1.4D', '1.2D+1.6L+0.5Lr', '1.2D+1.6Lr+0.5L', '1.2D+1.6W+0.5L+0.5Lr', '0.9D+1.6W'],
    wind='มยผ. 1311-50 simplified procedure: Songkhla group 4A, V50 = 25 m/s, TF = 1.2, Iw = 1.0, terrain A (open, conservative). '
         'q = 0.5*1.25*V^2*TF = 0.469 kPa; Ce = (z/10)^0.2 >= 0.9; low-rise CpCg: wall 0.75 / -0.55, roof -1.3 / -0.7, side wall -0.7; '
         'internal CpiCgi +0.3 / -0.3. 50-year wind with load factor 1.6.',
    loads=dict(roof_SDL='sheet + insulation 0.15 kPa, MEP + lighting hung 0.20 kPa, purlins by section', roof_Lr='0.30 kPa (กฎกระทรวง) + 1.0 kN point on purlins',
               floor_SDL='composite slab 120 mm on metal deck 2.6 kPa, finish + ceiling + MEP 1.0 kPa, partitions co-working 1.0 kPa',
               floor_L='5.0 kPa (gym, mezz, front L2, stairs, bridge); guard 0.75 kN/m at +1.1',
               climbing='wall DL 0.5 kPa of face; protection point 8 kN/lane; top anchor 12 kN/lane; auto-belay 12 kN/device; climber 1 kN/lane; '
                        'global: 1 of 2 adjacent lanes active (3 of 5 rear lanes); climbing loads factored as L (1.6)'),
    serviceability='beams L/360 live, L/240 total; cantilevers 2L/360; purlins/girts L/180; rafters L/240 Lr; climbing-zone drift H/200, low zone H/150 (1.0W, full EI)',
    vibration='AISC DG11 walking: co-working / front L2 ap/g <= 0.5 %; bouldering deck ap/g <= 1.5 % and fn >= 9 Hz (target)',
    materials='SS400 Fy 245 (hot-rolled H, plates), TIS 1228 SSC400 Fy 245 (lipped C), STKR400 Fy 245 (SHS), STK400 Fy 235 (CHS), SR24 rods Fy 235 / Fu 380')

q = 0.5 * 1.25 * 25 ** 2 * 1.2 / 1000           # kPa
Ce = lambda z: max(0.9, (z / 10) ** 0.2)
qh_hi, qh_lo = q * Ce(15.95), q * Ce(8.0)
CPI = 0.3

GY = [67.75, 74.65, 81.55, 88.45, 97.45, 104.05, 110.65, 117.25]
XR = 6.0; SL = math.tan(math.radians(5))
tos = lambda x, E: E + (10.84 - abs(x - XR)) * SL
XFA, XFB = -4.98, 17.00
PLAN = [(66.1, -3.99, -1.99), (74.9, -3.99, -1.99), (80.9, -3.24, -1.24), (82.4, -3.24, -1.24), (88.4, -2.09, -0.09),
        (97.62, -2.09, -0.09), (103.62, -3.24, -1.24), (105.12, -3.24, -1.24), (111.12, -3.99, -1.99), (119.1, -3.99, -1.99)]
xe = lambda y: float(np.interp(y, [p[0] for p in PLAN], [p[2] for p in PLAN]))

DL_SLAB, DL_SDL, DL_PART, LL = 2.6, 1.0, 1.0, 5.0

H_ALL = sorted([n for n, p in LIB.items() if p['t'] == 'H'], key=lambda n: LIB[n]['kgm'])
C_ALL = sorted([n for n, p in LIB.items() if p['t'] == 'C'], key=lambda n: LIB[n]['kgm'])
SHS_ALL = sorted([n for n, p in LIB.items() if p['t'] == 'SHS'], key=lambda n: LIB[n]['kgm'])
CHS_ALL = sorted([n for n, p in LIB.items() if p['t'] == 'CHS'], key=lambda n: LIB[n]['kgm'])
RB_ALL = sorted([n for n, p in LIB.items() if p['t'] == 'RB'], key=lambda n: LIB[n]['kgm'])

SIZES, CALC = {}, {}
def record(grp, sec, checks, note='', extra=None):
    ur = max(c[1] for c in checks)
    SIZES[grp] = sec
    CALC[grp] = dict(sec=sec, ur=round(ur, 3), checks=[(c[0], round(c[1], 3), c[2]) for c in checks], note=note, **(extra or {}))
    return ur

# ================================================================ simple beam checker
def beam_check(sec, L, wD, wL, Lb=0.5, Cb=1.0, pD=(), pL=(), cant=False, lim_L=360, lim_T=240, Fy=FY, Nu=0.0, extra_M=0.0):
    """simply supported (or cantilever) beam, UDL kN/m (self weight added) + point loads [(a_frac, P)].
    returns list of checks (name, UR, text)"""
    p = LIB[sec]; sw = p['kgm'] * g9
    wDt = wD + sw
    def MV(w, pts):
        if cant:
            M = w * L * L / 2 + sum(P * a * L for a, P in pts); V = w * L + sum(P for _, P in pts)
        else:
            M = w * L * L / 8 + sum(P * a * (1 - a) * L for a, P in pts); V = w * L / 2 + sum(P * max(a, 1 - a) for a, P in pts)
        return M, V
    def defl(w, pts):
        EI = E * p['Ix'] * 1e-12 * 1e3   # kN m2
        if cant: return w * L ** 4 / (8 * EI) + sum(P * (a * L) ** 2 * (3 * L - a * L) / (6 * EI) for a, P in pts)
        d = 5 * w * L ** 4 / (384 * EI)
        for a, P in pts:
            aa = a * L; b = L - aa; x = L / 2
            d += P * b * x * (L * L - b * b - x * x) / (6 * EI * L) if aa >= x else P * aa * (L - x) * (2 * L * x - x * x - aa * aa) / (6 * EI * L)
        return d
    out = []
    for nm, fD, fL in (('1.4D', 1.4, 0), ('1.2D+1.6L', 1.2, 1.6)):
        Mu, Vu = MV(fD * wDt + fL * wL, [(a, fD * P) for a, P in pD] + [(a, fL * P) for a, P in pL])
        Mu += extra_M
        if p['t'] == 'H':
            Mc = flex_I(p, Fy, Lb * 1000 if not cant else L * 1000, Cb); Vc = shear_I(p, Fy)
            if Nu: Pc, _ = comp_I(p, Fy, L * 1000, Lb * 1000); ur = interact(Nu, Pc, Mu, Mc)
            else: ur = Mu / Mc
        elif p['t'] == 'C':
            Mc = flex_C(p, Fy); Vc = 0.95 * 0.6 * Fy * p['h'] * p['tw'] / 1e3; ur = Mu / Mc
        else:
            Mc = flex_hss(p, Fy); Vc = 0.9 * 0.6 * Fy * 2 * p['h'] * p['tw'] / 1e3; ur = Mu / Mc
        out.append((f'flexure {nm}', ur, f'Mu {Mu:.1f} / φMn {Mc:.1f} kNm'))
        out.append((f'shear {nm}', Vu / Vc, f'Vu {Vu:.1f} / φVn {Vc:.1f} kN'))
    k = 2 if cant else 1
    dL = defl(wL, pL); dT = defl(wDt + wL, list(pD) + list(pL))
    out.append(('deflection live', dL / (k * L / lim_L), f'{dL*1000:.1f} mm vs {k}L/{lim_L} = {k*L/lim_L*1000:.1f}'))
    out.append(('deflection total', dT / (k * L / lim_T), f'{dT*1000:.1f} mm vs {k}L/{lim_T} = {k*L/lim_T*1000:.1f}'))
    return out

def pick(cands, fn, maxdepth=None, mindepth=0, minb=0):
    best = None
    for s in cands:
        p = LIB[s]
        if maxdepth and p['h'] > maxdepth: continue
        if p['h'] < mindepth or p['b'] < minb: continue
        ch = fn(s)
        if max(c[1] for c in ch) <= 1.0: return s, ch
        if best is None or max(c[1] for c in ch) < max(c[1] for c in best[1]): best = (s, ch)
    return best

# ================================================================ composite vibration (AISC DG11 walking)
def vib(joist, Lj, Sj, girder, Lg, wD_kpa, floor_width, beta=0.03, Po=0.29, w_live=0.5):
    """joist panel + girder panel; transformed composite I with Ec dyn = 1.35 Ec, slab de = 0.09 m (deck ribs)"""
    Es, Ec = 200e6, 1.35 * 4700 * math.sqrt(28) * 1e3   # kN/m2
    n = Es / Ec; de = 0.09; hs = 0.12
    def Icomp(sec, b_eff):
        p = LIB[sec]; As = p['A'] * 1e-6; Is = p['Ix'] * 1e-12; d = p['h'] / 1000
        Ac = b_eff * de / n; yc = d + hs - de / 2; ys = d / 2
        yb = (As * ys + Ac * yc) / (As + Ac)
        return Is + As * (yb - ys) ** 2 + b_eff * de ** 3 / (12 * n) + Ac * (yc - yb) ** 2
    Ij = Icomp(joist, min(Sj, 0.4 * Lj))
    wj = (wD_kpa + w_live) * Sj + LIB[joist]['kgm'] * g9
    dj = 5 * wj * Lj ** 4 / (384 * Es * Ij)
    Ds = de ** 3 / (12 * n); Dj = Ij / Sj
    Bj = min(2.0 * (Ds / Dj) ** 0.25 * Lj, 2 / 3 * floor_width)
    Wj = wj / Sj * Bj * Lj
    if girder:
        Ig = Icomp(girder, min(Lj, 0.4 * Lg))
        wg = (wD_kpa + w_live) * Lj + LIB[girder]['kgm'] * g9
        dg = 5 * wg * Lg ** 4 / (384 * Es * Ig)
        Dg = Ig / Lj; Bg = min(1.8 * (Dj / Dg) ** 0.25 * Lg, 2 / 3 * floor_width)
        Wg = wg / Lj * Bg * Lg
    else:
        dg, Wg = 0.0, 1.0
    fn = 0.18 * math.sqrt(9.81 / (dj + dg))
    W = dj / (dj + dg) * Wj + dg / (dj + dg) * Wg
    ap = Po * math.exp(-0.35 * fn) / (beta * W)
    return fn, ap, W

# ================================================================ 1. purlins, girts
def purlin(span, sp, grp):
    wD = (0.15 + 0.20) * sp; wLr = 0.30 * sp; wW = -(1.3 + CPI) * qh_hi * sp      # uplift (zone 2 + internal)
    def fn(s):
        p = LIB[s]; sw = p['kgm'] * g9
        Mg = max((1.2 * (wD + sw) + 1.6 * wLr) * span ** 2 / 8, 1.2 * (wD + sw) * span ** 2 / 8 + 1.6 * 1.0 * span / 4)
        Mu_up = (1.6 * abs(wW) - 0.9 * (wD + sw)) * span ** 2 / 8
        if p['t'] == 'C':
            Mc_g = flex_C(p, FY_CF, True); Mc_u = flex_C(p, FY_CF, False)
        else:
            Mc_g = flex_I(p, FY, 0.0); Mc_u = flex_I(p, FY, span / 3 * 1000, 1.0)
        EI = E * p['Ix'] * 1e-9
        dW = 5 * (abs(wW) - (wD + sw)) * span ** 4 / (384 * EI); dL = 5 * (wLr + wD + sw) * span ** 4 / (384 * EI)
        return [('gravity 1.2D+1.6Lr', Mg / Mc_g, f'Mu {Mg:.2f} / φMn {Mc_g:.2f} kNm'),
                ('uplift 0.9D+1.6W (R-factor)', Mu_up / Mc_u, f'Mu {Mu_up:.2f} / φMn {Mc_u:.2f} kNm'),
                ('deflection D+Lr', dL / (span / 180), f'{dL*1000:.1f} mm vs L/180'),
                ('deflection W', dW / (span / 180), f'{dW*1000:.1f} mm vs L/180')]
    s, ch = pick(C_ALL + [h for h in H_ALL if LIB[h]['h'] <= 200], fn)
    record(grp, s, ch, f'span {span} m @ {sp} m, sag rods at third points, uplift {wW/sp:.2f} kPa (service)')
purlin(6.9, 1.175, 'PUR')
purlin(9.0, 1.175, 'PUR9')

def girt():
    span, sp = 6.9, 1.5
    w = (0.75 + CPI) * qh_hi * sp; ws = -(0.7 + CPI) * qh_hi * sp * 1.15      # pressure / suction (end zone factor)
    def fn(s):
        p = LIB[s]
        Mp = 1.6 * w * span ** 2 / 8; Ms = 1.6 * abs(ws) * span ** 2 / 8
        EI = E * p['Ix'] * 1e-9; d = 5 * max(w, abs(ws)) * span ** 4 / (384 * EI)
        return [('pressure', Mp / flex_C(p, FY_CF, True), f'Mu {Mp:.2f} kNm'), ('suction (R-factor)', Ms / flex_C(p, FY_CF, False), f'Mu {Ms:.2f} kNm'),
                ('deflection W', d / (span / 180), f'{d*1000:.1f} mm vs L/180')]
    s, ch = pick(C_ALL, fn); record('GIRT', s, ch, f'span {span} m @ {sp} m, wind {w/sp:.2f} / {ws/sp:.2f} kPa (service)')
girt()

# ================================================================ 2. floors
# --- front L2: worst deck width (facade -> inner edge) 4.85 m central zone, joists @ <= 2.3 m
wD_fl = DL_SLAB + DL_SDL; wd = 4.85; sj = 2.3
def fl2():
    s, ch = pick(H_ALL, lambda s: beam_check(s, wd, wD_fl * sj, LL * sj), maxdepth=250); record('FL2_J', s, ch, f'span {wd} m, @ {sj} m')
    s, ch = pick(H_ALL, lambda s: beam_check(s, wd, wD_fl * sj, LL * sj), maxdepth=300); record('FL2_X', s, ch, f'grid cross beam span {wd} m (simple), trib {sj} m')
    s, ch = pick(H_ALL, lambda s: beam_check(s, wd, wD_fl * sj + 0.5, LL * sj), maxdepth=300); record('FL2_S', s, ch, f'step beam span {wd} m, trib {sj} m + upstand')
    # edge beams: span 6.9 between grid supports, half deck width + guard/fascia
    trib = wd / 2
    s, ch = pick(H_ALL, lambda s: beam_check(s, 6.9, wD_fl * trib + 0.35, LL * trib), maxdepth=300)
    fn, ap, W = vib(LIB[SIZES['FL2_J']] and SIZES['FL2_J'], wd, sj, s, 6.9, wD_fl, 6.9 * 3)
    ch = ch + [('vibration walking ap/g ≤ 0.5 %', ap / 0.005, f'fn {fn:.1f} Hz, W {W:.0f} kN, ap/g {ap*100:.2f} %')]
    if ap > 0.005:   # stiffen the edge beams until the bay passes
        for s2 in H_ALL:
            if LIB[s2]['h'] > 350 or LIB[s2]['kgm'] < LIB[s]['kgm']: continue
            fn, ap, W = vib(SIZES['FL2_J'], wd, sj, s2, 6.9, wD_fl, 6.9 * 3)
            if ap <= 0.005:
                s = s2; ch = beam_check(s2, 6.9, wD_fl * trib + 0.35, LL * trib) + [('vibration walking ap/g ≤ 0.5 %', ap / 0.005, f'fn {fn:.1f} Hz, W {W:.0f} kN, ap/g {ap*100:.2f} %')]; break
    record('FL2_E', s, ch, f'edge beams span 6.9 m, trib {trib:.2f} m + guard / fascia 0.35 kN/m')
    # wing cantilever 1.65 m, trib 1.5 m + tip load from wing end beam
    s = SIZES['FL2_E']; ch = beam_check(s, 1.65, wD_fl * 1.5, LL * 1.5, cant=True, pD=[(1.0, 0.5)], pL=[(1.0, 0.75 * 1.5)])
    record('FL2_W', s, ch, 'cantilever 1.65 m = continuation of the edge beam (same section), back-span over grid')
    # inner columns: two edge-beam reactions + cross beam
    N_D = (wD_fl + 0.15) * (wd / 2) * 7.8 + 0.35 * 7.8; N_L = LL * (wd / 2) * 7.8
    Hc = 3.9
    def fc(s):
        p = LIB[s]; Nu = 1.2 * N_D + 1.6 * N_L; Mu = 1.6 * N_L / 2 * (0.1 + p['h'] / 2000)   # one side live, end plate eccentricity
        Pc, kl = comp_simple(p, FY, Hc * 1000)
        return [('axial + bending', interact(Nu, Pc, Mu, flex_hss(p, FY)), f'Nu {Nu:.0f} / φPn {Pc:.0f} kN, Mu {Mu:.1f} kNm, KL/r {kl:.0f}')]
    s, ch = pick([x for x in SHS_ALL if LIB[x]['h'] == LIB[x]['b']], fc, mindepth=150, minb=150)
    record('FL2_C', s, ch, f'H {Hc} m, trib {wd/2:.2f} x 7.8 m')
    return N_D, N_L
FL2_COLRD = fl2()
# reaction of the front L2 on main column A (per grid): half deck width x tributary bay
def fl2_on_A(g):
    b = {67.75: 6.9 / 2 + 1.65, 74.65: 6.9, 81.55: 6.9, 88.45: (6.9 + 2.0) / 2, 97.45: (2.1 + 6.6) / 2, 104.05: 6.6, 110.65: 6.6, 117.25: 6.6 / 2 + 1.65}[g]
    w = xe(g) - XFA; trib = w / 2
    return (DL_SLAB + DL_SDL + 0.3) * trib * b + 0.35 * b, LL * trib * b

# --- bouldering deck +6.3
wD_bd = DL_SLAB + 0.5 + 0.15          # slab, ceiling/MEP below, crash mats
Lj_bd, sj_bd, Lg_bd = 6.15, 13.45 / 6, 13.45
wall_D, wall_L = 2.9, 0.67            # upper bouldering wall line load kN/m along x, at 1.3 m from the south support
def bd():
    s, ch = pick(H_ALL, lambda s: beam_check(s, Lj_bd, wD_bd * sj_bd, LL * sj_bd, pD=[(0.21, wall_D * sj_bd)], pL=[(0.21, wall_L * sj_bd)]), maxdepth=400)
    record('BD_J', s, ch, f'joist span {Lj_bd} m @ {sj_bd:.2f} m + upper wall line load')
    J = s
    R_end = lambda fD, fL: fD * (wD_bd * sj_bd + LIB[J]['kgm'] * g9) * Lj_bd / 2 + fL * LL * sj_bd * Lj_bd / 2   # girder-side reaction per joist
    PD = (wD_bd * sj_bd + LIB[J]['kgm'] * g9) * Lj_bd / 2 + wall_D * sj_bd * 0.21; PL = LL * sj_bd * Lj_bd / 2 + wall_L * sj_bd * 0.21
    pts = [(k / 6, None) for k in range(1, 6)]
    def fg(s, Fy=FY):
        ch = beam_check(s, Lg_bd, wD_bd * 0.1, LL * 0.1, Lb=sj_bd, pD=[(a, PD) for a, _ in pts], pL=[(a, PL) for a, _ in pts], Fy=Fy)
        fn, ap, W = vib(J, Lj_bd, sj_bd, s, Lg_bd, wD_bd, 13.45, beta=0.03)
        return ch + [('vibration ap/g ≤ 1.5 %', ap / 0.015, f'ap/g {ap*100:.2f} %, W {W:.0f} kN'), ('vibration fn ≥ 6 Hz', 6.0 / fn, f'fn {fn:.1f} Hz (9 Hz needs 2 columns at the fall-zone edge)')]
    s, ch = pick(H_ALL, fg)
    alt = pick(H_ALL, lambda s: fg(s, 355.0))
    opts = []
    for g_ in ['H700x300x13x24', 'H800x300x14x26', 'H900x300x16x28']:
        fn_, ap_, _ = vib(J, Lj_bd, sj_bd, g_, Lg_bd, wD_bd, 13.45); opts.append((g_, round(fn_, 1), round(ap_ * 100, 2)))
    for g_ in ['H350x175x7x11']:
        fn_, ap_, _ = vib(J, Lj_bd, sj_bd, g_, 4.5, wD_bd, 13.45); opts.append(('2 extra columns + ' + g_, round(fn_, 1), round(ap_ * 100, 2)))
    record('BD_G', s, ch, f'girder span {Lg_bd} m, 5 joist point loads, Lb {sj_bd:.2f} m (no column in the fall zone)',
           extra=dict(vib_options=opts))
    G_ = s
    # south beam on gable posts: span 3.7, joist reactions near the wall (wall line load mostly here)
    PDs = (wD_bd * sj_bd + LIB[J]['kgm'] * g9) * Lj_bd / 2 + wall_D * sj_bd * 0.79; PLs = LL * sj_bd * Lj_bd / 2 + wall_L * sj_bd * 0.79
    s, ch = pick(H_ALL, lambda s: beam_check(s, 3.7, PDs / sj_bd, PLs / sj_bd), maxdepth=400); record('BD_S', s, ch, 'span 3.7 m between gable posts, UDL from joists + wall')
    # NE / NW columns: girder end reaction + edge joist
    RgD = (5 * PD + LIB[G_]['kgm'] * g9 * Lg_bd) / 2 + PD / 2; RgL = 5 * PL / 2 + PL / 2
    def fc(s):
        p = LIB[s]; Nu = 1.2 * RgD + 1.6 * RgL; Mu = 1.6 * RgL * 0.25 * (0.1 + p['h'] / 2000)
        Pc, kl = comp_I(p, FY, 4.5e3, 4.5e3); return [('axial + bending', interact(Nu, Pc, Mu, flex_I(p, FY, 4500)), f'Nu {Nu:.0f} / φPn {Pc:.0f} kN, KL/r {kl:.0f}')]
    s, ch = pick(H_ALL, fc, minb=200); record('BD_C', s, ch, f'H 4.5 m, girder end reaction D {RgD:.0f} / L {RgL:.0f} kN')
    def fp(s):
        p = LIB[s]; Nu = 1.2 * (PDs / 2 + 2) + 1.6 * PLs / 2; Pc, kl = comp_simple(p, FY, 5.0e3)
        return [('axial', Nu / Pc, f'Nu {Nu:.0f} / φPn {Pc:.0f} kN')]
    s, ch = pick([x for x in SHS_ALL if LIB[x]['h'] == LIB[x]['b']], fp, mindepth=150); record('BD_P', s, ch, 'SE post, H 5.0 m')
    # N-S side bracing: 2.5 % of deck gravity + climbers 0.5 kN/m along the wall, to two braced planes
    Hd = 0.025 * (1.2 * wD_bd + 1.6 * LL) * 13.45 * 6.3 + 1.6 * 0.5 * 13.45
    Lbr = math.hypot(6.0, 4.8); Nb = Hd / 2 * Lbr / 6.0
    s, ch = pick(CHS_ALL, lambda s: [('compression', Nb / comp_simple(LIB[s], FY_STK, Lbr * 1000)[0], f'Nu {Nb:.1f} kN, L {Lbr:.1f} m'),
                                     ('slenderness KL/r ≤ 200', comp_simple(LIB[s], FY_STK, Lbr * 1000)[1] / 200, '')])
    record('BD_BR', s, ch, f'deck lateral {Hd:.1f} kN (2.5 % gravity + climbers), 2 planes')
    return RgD, RgL
bd()

# --- co-working mezz +4.2: 9.0 m beams @ 1.98 m, primary beams on grid 4/5 continuous over the columns
wD_cm = DL_SLAB + DL_SDL + DL_PART; Sm = (16.66 - 6.76) / 5
def cm():
    def fb(s):
        ch = beam_check(s, 9.0, wD_cm * Sm, LL * Sm)
        fn, ap, W = vib(s, 9.0, Sm, None, 0, DL_SLAB + DL_SDL, 9.2)
        return ch + [('vibration walking ap/g ≤ 0.5 %', ap / 0.005, f'fn {fn:.1f} Hz, W {W:.0f} kN, ap/g {ap*100:.2f} %')]
    s, ch = pick(H_ALL, fb, maxdepth=500); record('CM_B9', s, ch, f'span 9.0 m @ {Sm:.2f} m, simple')
    B9 = s
    PD = (wD_cm * Sm + LIB[B9]['kgm'] * g9) * 9.0 / 2; PL = LL * Sm * 9.0 / 2
    # primary beam: supports at 8.15, 11.60 (columns), end at B column face ~16.4; cantilever to 6.76; point loads at beam lines
    xs_b = list(np.linspace(6.76, 16.66, 6)); sup = [8.15, 11.60, 16.40]
    def fp(s):
        p = LIB[s]; f = Frame(); EIfac = 1.0
        nodes = sorted(set([round(x, 3) for x in xs_b + sup + [6.76]]))
        nid = [f.node(x, 0) for x in nodes]; els = []
        for a, b in zip(nid[:-1], nid[1:]): els.append(f.elem(a, b, E * 1e3, p['A'] * 1e-6, p['Ix'] * 1e-12))
        for x in sup: f.support(f.node(round(x, 3), 0), True, True, False)
        for x in xs_b:
            n_ = f.node(round(x, 3), 0); share = 0.5 if (x < 6.8 or x > 16.6) else 1.0   # edge beams carry half a bay each side
            f.load_node('D', n_, fz=-2 * PD * share); f.load_node('L', n_, fz=-2 * PL * share)
        for e in els: f.udl('D', e, wz=-p['kgm'] * g9)
        Mmax = Vmax = 0
        for combo in ({'D': 1.4}, {'D': 1.2, 'L': 1.6}, {'D': 1.2}):
            r = f.solve(combo, pdelta=False, red=1.0)
            for ei in range(len(els)):
                for st in f.stations(ei, r, combo, 5): Mmax = max(Mmax, abs(st[3])); Vmax = max(Vmax, abs(st[2]))
        rL = f.solve({'L': 1.0}, pdelta=False, red=1.0); dmax = max(abs(rL['U'][1::3]))
        Mc = flex_I(p, FY, 1.5e3); Vc = shear_I(p, FY)
        return [('flexure', Mmax / Mc, f'Mu {Mmax:.0f} / φMn {Mc:.0f} kNm'), ('shear', Vmax / Vc, f'Vu {Vmax:.0f} / φVn {Vc:.0f} kN'),
                ('deflection live (cantilever tip / span)', dmax / (2 * 1.39 / 360), f'{dmax*1000:.1f} mm')]
    s, ch = pick(H_ALL, fp, maxdepth=500); record('CM_P', s, ch, 'continuous over columns x 8.15 / 11.60, cantilever 1.39 m to x 6.76')
    # columns
    Rc_D = PD * 2 * 1.25 + 1.0; Rc_L = PL * 2 * 1.25
    def fc(s):
        p = LIB[s]; Nu = 1.2 * Rc_D + 1.6 * Rc_L; Pc, kl = comp_I(p, FY, 3.1e3, 3.1e3)
        return [('axial', Nu / Pc, f'Nu {Nu:.0f} / φPn {Pc:.0f} kN, KL/r {kl:.0f}')]
    s, ch = pick(H_ALL, fc, minb=150); record('CM_C', s, ch, 'H 3.1 m, two 9 m beam reactions x 1.25 continuity')
    return PD, PL
CM_PD, CM_PL = cm()
# reaction of the mezz on column B/4, B/5 (primary beam end, 1 beam line at x 14.6 + half of the edge line)
CM_ON_B = (CM_PD * 2 * 0.5 + CM_PD * 2 * 0.45, CM_PL * 2 * 0.5 + CM_PL * 2 * 0.45)

# --- bridge
def br():
    s, ch = pick(H_ALL, lambda s: beam_check(s, 6.95, (DL_SLAB + DL_SDL) * 1.0 + 0.65 + 0.3, LL * 1.0), maxdepth=350)
    record('BR_B', s, ch, 'span 6.95 m, trib 1.0 m + glass partition 0.65 kN/m + guard')
    s, ch = pick(H_ALL, lambda s: beam_check(s, 1.95, (DL_SLAB + DL_SDL) * 1.8, LL * 1.8), maxdepth=250); record('BR_J', s, ch, 'span 1.95 m @ 1.8 m')
br()

# --- stairs
def stairs():
    wDs, b = 1.2, 0.95 / 2          # tread pan + finish kPa (plan), half width per stringer
    s, ch = pick(H_ALL + C_ALL, lambda s: beam_check(s, 4.45, wDs * b + 0.3, LL * b), maxdepth=250)
    record('ST_STR', s, ch, 'lower flight horizontal span 4.45 m (upper 3.71 m), plan loads')
    Pst = (1.2 * wDs * b + 1.6 * LL * b) * 4.45 / 2
    s, ch = pick(H_ALL, lambda s: beam_check(s, 2.1, (wDs + 0.5) * 0.45, LL * 0.45, pD=[(0.3, wDs * b * 4.45 / 2), (0.75, wDs * b * 4.45 / 2)],
                                             pL=[(0.3, LL * b * 4.45 / 2), (0.75, LL * b * 4.45 / 2)]), maxdepth=250)
    record('ST_LB', s, ch, 'landing beam span 2.1 m with 2 stringer reactions')
    def fp(s):
        Nu = 2 * 2 * Pst * 0.5; Pc, kl = comp_simple(LIB[s], FY, 2.7e3); return [('axial', Nu / Pc, f'Nu {Nu:.0f} / φPn {Pc:.0f} kN')]
    s, ch = pick([x for x in SHS_ALL if LIB[x]['h'] == LIB[x]['b']], fp, mindepth=100); record('ST_POST', s, ch, 'landing post H 2.7 m')
    # spiral: 18 treads, each 0.209 m2, 220 deg sweep, column tied at head to the bridge beam
    At = 0.5 * 1.4 ** 2 * math.radians(220) / 18
    wt = 1.2 * 1.0 + 1.6 * LL; Ptot = 18 * At * wt + 1.2 * 3.0
    Mov = 18 * At * wt * 0.93 * math.sin(math.radians(110)) / math.radians(110)
    def fsc(s):
        p = LIB[s]; Pc, kl = comp_simple(p, FY_STK, 4.2e3); Mc = flex_hss(p, FY_STK)
        return [('axial + overturning', interact(Ptot, Pc, Mov * 0.6, Mc), f'Nu {Ptot:.0f} kN, Mu {Mov*0.6:.1f} kNm (propped head)')]
    s, ch = pick(CHS_ALL, fsc, mindepth=160); record('SP_COL', s, ch, 'CHS centre column, head tied to the bridge south beam')
    def fa(s):
        p = LIB[s]; Mu = wt * At * 1.3 * 2 / 3 + 1.6 * 1.3 * 1.25
        return [('cantilever arm', Mu / flex_I(p, FY, 1.3e3), f'Mu {Mu:.2f} kNm (tread + 1.3 kN point at tip)')]
    s, ch = pick(H_ALL, fa); record('SP_ARM', s, ch, 'tread arm cantilever 1.29 m')
stairs()

# ================================================================ 3. wind posts (gable, clerestory, B lobby)
def post(grp, Ltot, braced_at, trib, qref, P_extra=(0.0, 0.0), N_D=5.0, N_L=0.0):
    w = (0.75 + CPI) * qref * trib
    spans = [(braced_at[i + 1] - braced_at[i]) for i in range(len(braced_at) - 1)]
    def fn(s):
        p = LIB[s]; out = []
        for Ls in spans:
            Mu = 1.6 * w * Ls ** 2 / 8 + 1.6 * P_extra[0] * Ls / 4
            Nu = 1.2 * (N_D + p['kgm'] * g9 * Ltot) + 0.5 * N_L
            Pc, kl = comp_I(p, FY, Ls * 1000, 1.5e3)
            out.append((f'span {Ls:.1f} m wind + axial', interact(Nu, Pc, Mu, flex_I(p, FY, 3.0e3)), f'Mu {Mu:.1f} kNm, Nu {Nu:.0f} kN'))
            d = 5 * w * Ls ** 4 / (384 * E * p['Ix'] * 1e-9); out.append((f'deflection span {Ls:.1f}', d / (Ls / 180), f'{d*1000:.0f} mm vs L/180'))
            Nu2 = 1.2 * (N_D + p['kgm'] * g9 * Ltot) + 1.6 * N_L
            out.append((f'gravity 1.2D+1.6L', Nu2 / Pc, f'Nu {Nu2:.0f} kN'))
        return out
    s, ch = pick(H_ALL, fn); record(grp, s, ch, f'spans {spans}, trib {trib} m, wind {(0.75+CPI)*qref:.2f} kPa')
RgD_bdS = ((wD_bd * sj_bd) * Lj_bd / 2 + wall_D * sj_bd * 0.79) / sj_bd * 3.7
RgL_bdS = (LL * sj_bd * Lj_bd / 2 + wall_L * sj_bd * 0.79) / sj_bd * 3.7
post('WP_G1', 15.4, [0.2, 6.0, 15.4], 3.7, qh_hi, P_extra=(3.3, 0), N_D=RgD_bdS + 0.15 * 3.7 * 15, N_L=RgL_bdS)
post('WP_G8', 7.4, [0.2, 7.4], 5.4, qh_lo, N_D=0.15 * 5.4 * 7.5)
post('WP_G4', 8.2, [0.0, 8.2], 5.4, qh_hi, N_D=0.15 * 5.4 * 8)
post('WP_B', 6.8, [0.2, 7.0], 4.5, qh_lo, N_D=0.15 * 4.5 * 7 + CM_PD * 0.5, N_L=CM_PL * 0.5)

# ================================================================ 4. portal frames (Direct Analysis Method)
FR = dict(HI_END=dict(grids=[0], E=15.0, base='fixed', b_roof=3.45, b_wall=3.45),
          HI=dict(grids=[1, 2], E=15.0, base='fixed', b_roof=6.9, b_wall=6.9),
          STEP=dict(grids=[3], E=15.0, base='fixed', b_roof=3.45, b_wall=3.45, low_b=4.5),
          LO_MEZZ=dict(grids=[4], E=7.0, base='pinned', b_roof=7.8, b_wall=7.8),
          LO=dict(grids=[5, 6], E=7.0, base='pinned', b_roof=6.6, b_wall=6.6),
          LO_END=dict(grids=[7], E=7.0, base='pinned', b_roof=3.3 + 0.5, b_wall=3.3))
PUR_KGM = LIB[SIZES['PUR']]['kgm']
ROOF_D = 0.15 + 0.20 + PUR_KGM * g9 / 1.175          # kPa
# climbing wall (rear, y 69.3-77.3, 5 lanes): auto-belay 12 kN at +13.0, 3 of 5 lanes active; share by grid
LANES = [70.1, 71.7, 73.3, 74.9, 76.5]
def lane_share(gi):
    g = GY[gi]; sh = []
    for y in LANES:
        if GY[max(gi - 1, 0)] <= y <= g and gi > 0: sh.append((y - GY[gi - 1]) / (g - GY[gi - 1]))
        elif g <= y <= GY[gi + 1]: sh.append((GY[gi + 1] - y) / (GY[gi + 1] - g))
        else: sh.append(0)
    return sum(sorted(sh, reverse=True)[:3])
CW_V = {gi: 12.0 * lane_share(gi) for gi in (0, 1, 2)}

def build_frame(key, gi, col, raf, lraf=None):
    cf = FR[key]; E_ = cf['E']; g = GY[gi]
    pc, pr = LIB[col], LIB[raf]; hc, dr = pc['h'] / 1000, pr['h'] / 1000
    xA, xB = XFA + hc / 2, XFB - hc / 2
    f = Frame(); Es = E * 1e3
    zr = lambda x: tos(x, E_) - dr / 2
    nA0, nB0 = f.node(xA, 0.2), f.node(xB, 0.2)
    nAk, nBk = f.node(xA, zr(xA)), f.node(xB, zr(xB))
    if cf['base'] == 'fixed': f.support(nA0); f.support(nB0)
    else: f.support(nA0, True, True, False); f.support(nB0, True, True, False)
    # column nodes at load points
    zA = [0.2]; zB = [0.2]
    zdeck = {67.75: 3.4, 74.65: 3.4, 81.55: 3.8, 88.45: 4.2, 97.45: 4.2, 104.05: 3.8, 110.65: 3.6, 117.25: 3.4}[g] - 0.14 - 0.15
    zA.append(zdeck)
    if gi in (3, 4): zB.append(4.06 - 0.2)
    if gi in (0, 1, 2): zB += [4.0, 8.5, 13.0]
    if gi == 3: zA.append(zr(xA) - (15 - 7)); zB.append(zr(xB) - 8)        # low rafter at +7
    zA = sorted(set(zA + [zr(xA)])); zB = sorted(set(zB + [zr(xB)]))
    cols = []
    for x, zs in ((xA, zA), (xB, zB)):
        ns = [f.node(x, z) for z in zs]
        for a, b in zip(ns[:-1], ns[1:]):
            cols.append(f.elem(a, b, Es, pc['A'] * 1e-6, pc['Ix'] * 1e-12, 'col', meta=dict(side='A' if x < 6 else 'B')))
    # rafter with haunch (2 sub-elements per side, 2.2 m)
    xs = [xA, xA + 1.1, xA + 2.2, xA + 5.0, XR, xB - 5.0, xB - 2.2, xB - 1.1, xB]
    rn = [f.node(x, zr(x)) for x in xs]
    raf_el = []
    hn = built_I(pr['h'] * 1.75, pr['b'], pr['tw'], pr['tf']); hn2 = built_I(pr['h'] * 1.25, pr['b'], pr['tw'], pr['tf'])
    for k, (a, b) in enumerate(zip(rn[:-1], rn[1:])):
        pp = hn if k in (0, 7) else (hn2 if k in (1, 6) else pr)
        raf_el.append(f.elem(a, b, Es, pp['A'] * 1e-6, pp['Ix'] * 1e-12, 'haunch' if k in (0, 1, 6, 7) else 'raf', meta=dict(k=k)))
    els_low = []
    if lraf:  # step frame: low rafter pinned to the high columns at +7
        pl = LIB[lraf]; dl = pl['h'] / 1000; zl = lambda x: tos(x, 7.0) - dl / 2
        ln = [None, f.node(XR, zl(XR)), None]
        ln[0] = f.node(xA, zA[[abs(z - zl(xA)) for z in zA].index(min(abs(z - zl(xA)) for z in zA))])
        ln[2] = f.node(xB, zB[[abs(z - zl(xB)) for z in zB].index(min(abs(z - zl(xB)) for z in zB))])
        els_low.append(f.elem(ln[0], ln[1], Es, pl['A'] * 1e-6, pl['Ix'] * 1e-12, 'lraf', rel=(True, False)))
        els_low.append(f.elem(ln[1], ln[2], Es, pl['A'] * 1e-6, pl['Ix'] * 1e-12, 'lraf', rel=(False, True)))
    # ---- loads
    br_, bw = cf['b_roof'], cf['b_wall']
    for e in raf_el:
        f.udl('D', e, wz=-ROOF_D * br_, proj=True); f.udl('Lr', e, wz=-0.30 * br_, proj=True)
        f.udl('D', e, wz=-pr['kgm'] * g9)
    for e in cols: f.udl('D', e, wz=-pc['kgm'] * g9 - 0.15 * bw)                # self + girts/cladding
    for e in els_low:
        lb = cf['low_b']; f.udl('D', e, wz=-ROOF_D * lb, proj=True); f.udl('Lr', e, wz=-0.30 * lb, proj=True); f.udl('D', e, wz=-LIB[lraf]['kgm'] * g9)
    # front L2 on column A (deck level), eccentric to the inner face
    RD, RL = fl2_on_A(g); e_ = hc / 2 + 0.08; nd = f.node(xA, zdeck)
    f.load_node('D', nd, fz=-RD, my=-RD * e_); f.load_node('L', nd, fz=-RL, my=-RL * e_)
    if gi in (3, 4):
        nm = f.node(xB, 4.06 - 0.2); f.load_node('D', nm, fz=-CM_ON_B[0], my=CM_ON_B[0] * (hc / 2 + 0.08)); f.load_node('L', nm, fz=-CM_ON_B[1], my=CM_ON_B[1] * (hc / 2 + 0.08))
    if gi in (0, 1, 2):          # climbing wall: auto-belay vertical at +13 on an arm 0.75 m off the face, 15 deg lean
        V = CW_V[gi]; n13 = f.node(xB, 13.0); f.load_node('L', n13, fz=-V, fx=-0.26 * V, my=V * (hc / 2 + 0.75))
        for z, H_ in ((4.0, 1.5), (8.5, 1.5), (13.0, 1.5)):          # wall dead-load overturning ties
            f.load_node('D', f.node(xB, z), fx=-H_ * (1 if gi == 1 else 0.5))
    # wind: 4 transverse cases + 1 longitudinal uplift case
    qh = qh_hi if E_ > 10 else qh_lo
    def wind(case, sgn, cpi):
        # sgn +1 wind from street (A windward), -1 from rear
        ww, lw = 0.75, -0.55
        pA = (ww if sgn > 0 else lw) - cpi; pB = (lw if sgn > 0 else ww) - cpi     # + toward building on that face
        for e in cols:
            side = f.El[e]['meta']['side']
            if side == 'A': f.udl(case, e, wx=pA * qh * bw)                       # pressure on A pushes +x
            else: f.udl(case, e, wx=-pB * qh * bw)                                # pressure on B pushes -x
        for e in raf_el:
            k = f.El[e]['meta']['k']; windward = (k < 4) == (sgn > 0)
            cp = (-1.3 if windward else -0.7) - cpi
            f.udl(case, e, wn=-cp * qh * br_)                                    # suction -> +local y (up)
        for e in els_low:
            f.udl(case, e, wn=(1.3 + cpi) * qh * cf['low_b'])
    wind('W1', +1, 0.3); wind('W2', +1, -0.3); wind('W3', -1, 0.3); wind('W4', -1, -0.3)
    for e in cols: f.udl('W5', e, wx=(1.0 if f.El[e]['meta']['side'] == 'B' else -1.0) * (0.7 + 0.3) * qh * bw)
    for e in raf_el + els_low: f.udl('W5', e, wn=(1.3 + 0.3) * qh * br_)
    return f, cols, raf_el, els_low, (nAk, nBk), (xA, xB)

COMBOS = [('1.4D', {'D': 1.4}), ('1.2D+1.6L+0.5Lr', {'D': 1.2, 'L': 1.6, 'Lr': 0.5}), ('1.2D+1.6Lr+0.5L', {'D': 1.2, 'Lr': 1.6, 'L': 0.5})]
for w in ('W1', 'W2', 'W3', 'W4', 'W5'):
    COMBOS.append((f'1.2D+1.6{w}+0.5L+0.5Lr', {'D': 1.2, w: 1.6, 'L': 0.5, 'Lr': 0.5}))
    COMBOS.append((f'0.9D+1.6{w}', {'D': 0.9, w: 1.6}))

def check_frame(key, col, raf, lraf=None, detail=False):
    worst = []; res_all = {}
    for gi in FR[key]['grids']:
        f, cols, rafs, lows, knees, (xA, xB) = build_frame(key, gi, col, raf, lraf)
        pc, pr = LIB[col], LIB[raf]; E_ = FR[key]['E']
        Hcol = tos(xA, E_) - 0.2
        env = {}
        reactions = {}
        for cname, combo in COMBOS:
            # notional loads from a first-order pass
            r0 = f.solve(combo, pdelta=False, red=1.0)
            grav = sum(abs(v) for k, v in combo.items() if k in ('D', 'L', 'Lr'))
            Y = 0.0
            for e in rafs + cols + lows:
                pass
            # total factored vertical load = sum of vertical base reactions
            Ksum = 0.0
            f.nl.pop('N', None)
            Vtot = 0.0
            for nd in list(f.fix):
                pass
            # approximate: vertical load = sum of element loads
            Vtot = sum(abs(fac) * tot for case, fac in combo.items() for tot in [case_total(f, case)] if case in ('D', 'L', 'Lr'))
            c2 = dict(combo)
            if not any(k.startswith('W') for k in combo):
                f.load_node('N', knees[0], fx=0.002 * Vtot / 2); f.load_node('N', knees[1], fx=0.002 * Vtot / 2); c2['N'] = 1.0
            r = f.solve(c2, pdelta=True, red=0.8)
            if detail:
                # base reactions (first-order, full stiffness, unfactored per case are produced separately)
                pass
            for e in cols + rafs + lows:
                tag = f.El[e]['tag']
                for st in f.stations(e, r, c2, 7):
                    k = (tag, e)
                    env.setdefault(k, []).append((st[1], st[2], st[3], cname))
        # member checks
        Fy = FY
        for (tag, e), lst in env.items():
            if tag == 'col':
                p = pc; L = Hcol; Lb = 3.2
                Pc, kl = comp_I(p, Fy, L * 1000, Lb * 1000); Mc = flex_I(p, Fy, Lb * 1000); Vc = shear_I(p, Fy)
            elif tag in ('raf', 'haunch'):
                p = pr if tag == 'raf' else built_I(pr['h'] * (1.75 if f.El[e]['meta']['k'] in (0, 7) else 1.25), pr['b'], pr['tw'], pr['tf'])
                if tag == 'haunch': p['hw_clear'] = p['h'] - 2 * p['tf']
                L = 10.9; Lb = 2.35
                Pc, kl = comp_I(p, Fy, L * 1000, Lb * 1000); Mc = flex_I(p, Fy, Lb * 1000); Vc = shear_I(p, Fy)
            else:
                p = LIB[lraf]; L = 10.9; Lb = 2.35
                Pc, kl = comp_I(p, Fy, L * 1000, Lb * 1000); Mc = flex_I(p, Fy, Lb * 1000); Vc = shear_I(p, Fy)
            for N_, V_, M_, cn in lst:
                ur = interact(-N_ if N_ < 0 else 0.0, Pc, M_, Mc) if N_ < 0 else abs(M_) / Mc + 0 * N_
                worst.append((tag, ur, f'grid {gi+1} {cn}: Nu {-N_:.0f} kN / φPn {Pc:.0f}, Mu {abs(M_):.0f} / φMn {Mc:.0f} kNm', cn))
                worst.append((tag + ' shear', abs(V_) / Vc, f'grid {gi+1} {cn}: Vu {abs(V_):.0f} / φVn {Vc:.0f} kN', cn))
        # serviceability: drift under 1.0W (full EI, 1st order), rafter deflection under Lr
        lim = (Hcol / 200) if E_ > 10 else (Hcol / 150)
        for w in ('W1', 'W2', 'W3', 'W4'):
            r = f.solve({w: 1.0}, pdelta=False, red=1.0)
            d = max(abs(r['U'][3 * knees[0]]), abs(r['U'][3 * knees[1]]))
            worst.append(('drift', d / lim, f'grid {gi+1} {w}: {d*1000:.0f} mm vs H/{200 if E_>10 else 150} = {lim*1000:.0f}', w))
        r = f.solve({'Lr': 1.0}, pdelta=False, red=1.0); nR = f.node(XR, tos(XR, E_) - pr['h'] / 2000)
        dz = abs(r['U'][3 * nR + 1]); limr = 21.4 / 240
        worst.append(('rafter deflection Lr', dz / limr, f'grid {gi+1}: {dz*1000:.0f} mm vs L/240 = {limr*1000:.0f}', 'Lr'))
        if detail:
            reac = {}
            for case in ('D', 'L', 'Lr', 'W1', 'W2', 'W3', 'W4', 'W5'):
                r = f.solve({case: 1.0}, pdelta=False, red=1.0)
                # reactions from element end forces at support nodes
                R = {}
                for nd in f.fix:
                    RR = np.zeros(3)
                    for ei, el in enumerate(f.El):
                        k, T, L_ = f._kl(el, 0, 1.0)
                        if el['i'] == nd or el['j'] == nd:
                            fg = T.T @ r['ends'][ei]
                            RR += fg[:3] if el['i'] == nd else fg[3:]
                    for nd2, v in f.nl.get(case, {}).items():
                        if nd2 == nd: RR -= v
                    R['A' if f.N[nd][0] < 6 else 'B'] = [round(float(RR[0]), 1), round(float(RR[1]), 1), round(float(RR[2]), 1)]
                reac[case] = R
            res_all[GY[gi]] = reac
    return worst, res_all

def case_total(f, case):
    tot = 0.0
    for el in f.El:
        L, c, s = f._geom(el)
        for ld in el['loads']:
            if ld[0] != case: continue
            if ld[1] == 'u': tot += abs(ld[2]) * (L * abs(c) if ld[3] else L)
            else: tot += abs(ld[4])
    for n_, v in f.nl.get(case, {}).items(): tot += abs(v[1])
    return tot

def design_frame(key):
    hi = FR[key]['E'] > 10
    cc = [s for s in H_ALL if (LIB[s]['h'] >= 400 if hi else LIB[s]['h'] >= 250) and LIB[s]['h'] <= 600 and LIB[s]['b'] >= 150]
    rc = [s for s in H_ALL if LIB[s]['h'] >= 250 and LIB[s]['h'] <= 600 and LIB[s]['b'] >= 150]
    lc = [s for s in H_ALL if 250 <= LIB[s]['h'] <= 500] if key == 'STEP' else [None]
    best = None
    pairs = sorted(itertools.product(cc, rc, lc), key=lambda t: 2 * 15 * LIB[t[0]]['kgm'] + 22 * LIB[t[1]]['kgm'] + (22 * LIB[t[2]]['kgm'] if t[2] else 0))
    tried = 0
    for col, raf, lr in pairs:
        tried += 1
        w, _ = check_frame(key, col, raf, lr)
        ur = max(x[1] for x in w)
        if best is None or ur < best[3]: best = (col, raf, lr, ur)
        if ur <= 1.0:
            best = (col, raf, lr, ur); break
        if tried > 400: break
    col, raf, lr, ur = best
    w, reac = check_frame(key, col, raf, lr, detail=True)
    def top(tag):
        xs = [x for x in w if x[0].startswith(tag)]
        return max(xs, key=lambda x: x[1]) if xs else None
    checks = []
    for tag, nm in (('col', 'column N+M (H1-1)'), ('col shear', 'column shear'), ('raf', 'rafter N+M'), ('raf shear', 'rafter shear'),
                    ('haunch', 'haunch N+M'), ('lraf', 'low rafter N+M'), ('drift', 'drift'), ('rafter deflection', 'rafter deflection')):
        t = top(tag)
        if t: checks.append((nm, t[1], t[2]))
    SIZES[f'MF_{key}_COL'] = col; SIZES[f'MF_{key}_RAF'] = raf
    if lr: SIZES['MF_STEP_LRAF'] = lr
    CALC[f'MF_{key}_COL'] = dict(sec=col, ur=round(max(c[1] for c in checks if 'column' in c[0] or c[0] == 'drift'), 3),
                                 checks=[(c[0], round(c[1], 3), c[2]) for c in checks], note=f'frame {key}: grids {[g+1 for g in FR[key]["grids"]]}, base {FR[key]["base"]}',
                                 reactions=reac)
    CALC[f'MF_{key}_RAF'] = dict(sec=raf, ur=round(max(c[1] for c in checks if 'rafter' in c[0] or 'haunch' in c[0]), 3), checks=[], note=f'see MF_{key}_COL')
    if lr: CALC['MF_STEP_LRAF'] = dict(sec=lr, ur=round(max(c[1] for c in checks if 'low rafter' in c[0]), 3), checks=[], note='see MF_STEP_COL')
    print(f'frame {key}: col {col} raf {raf} {lr or ""} UR {ur:.2f} ({tried} tried)')
for k in FR: design_frame(k)

# ================================================================ 5. bracing (longitudinal wind, factored)
A_g1 = 21.7 * (15.0 - 0.2) + 0.5 * 21.7 * 0.95 + 21.7 * 0.9      # gable 1 incl. parapet
A_g8 = 21.7 * (7.0 - 0.2) + 0.5 * 21.7 * 0.95 + 21.7 * 0.9
A_g4 = 21.7 * 8.5
F_hi = 1.6 * (0.75 + 0.55) * qh_hi * max(A_g1, A_g4); F_lo = 1.6 * (0.75 + 0.55) * qh_lo * A_g8
roof_hi, roof_lo = 0.55 * F_hi, 0.55 * F_lo
eave_hi, eave_lo = roof_hi / 2, roof_lo / 2
def rod_pick(grp, T, L, note):
    s, ch = pick(RB_ALL, lambda s: [('tension (threaded)', T / tension(LIB[s], FY_ROD, FU_ROD, True), f'Tu {T:.0f} kN, L {L:.1f} m')])
    record(grp, s, ch, note)
dg_roof = math.hypot(5.42, 6.9)
rod_pick('ROD_ROOF_HI', eave_hi * dg_roof / 6.9, dg_roof, f'high roof X-brace: gable force {F_hi:.0f} kN, 55 % to roof, panel shear {eave_hi:.0f} kN')
rod_pick('ROD_ROOF_LO', eave_lo * math.hypot(5.42, 6.6) / 6.6, math.hypot(5.42, 6.6), f'low roof X-brace: gable 8 force {F_lo:.0f} kN')
dg_w = math.hypot(6.9, 8.0)
# bay 3-4: force too high for a single rod -> CHS X (tension + compression, diagonals connected at the crossing)
Nd = (eave_hi + eave_lo) * dg_w / 6.9 / 2
s, ch = pick(CHS_ALL, lambda s: [('compression diagonal (Lc = L/2)', Nd / comp_simple(LIB[s], FY_STK, dg_w * 500)[0], f'Nu {Nd:.0f} kN, Lc {dg_w/2:.2f} m'),
                                 ('tension diagonal', Nd / tension(LIB[s], FY_STK, FU), f'Tu {Nd:.0f} kN'),
                                 ('KL/r ≤ 200', comp_simple(LIB[s], FY_STK, dg_w * 500)[1] / 200, '')])
record('ROD_WALL_HI', s, ch, f'CHS X-brace bay 3-4 (A and B), tension + compression: eave {eave_hi:.0f} kN + low-zone line A {eave_lo:.0f} kN')
rod_pick('ROD_WALL_LO', eave_lo * math.hypot(6.6, 6.8) / 6.6, math.hypot(6.6, 6.8), 'wall X-brace line B bay 7-8')
def strut(grp, N, L, cands, note):
    s, ch = pick(cands, lambda s: [('compression', N / (comp_simple(LIB[s], FY_STK, L * 1000)[0] if LIB[s]['t'] != 'C' else comp_C(LIB[s], FY_CF, L * 1000, L * 500)[0]), f'Nu {N:.0f} kN, L {L} m'),
                                   ('KL/r ≤ 200', (comp_simple(LIB[s], FY, L * 1000)[1] if LIB[s]['t'] != 'C' else 0) / 200, '')])
    record(grp, s, ch, note)
strut('STRUT_ROOF', eave_hi / 2, 6.9, CHS_ALL, 'roof strut at panel points (gable post reactions)')
strut('STRUT_WALL', eave_hi + eave_lo, 6.9, CHS_ALL + SHS_ALL, 'wall strut at +7.0 / +7.6 tiers')
strut('EAVE_HI', eave_hi, 6.9, CHS_ALL + SHS_ALL, 'eave strut grid 1 -> bay 3-4 (compression from roof bracing)')
strut('EAVE_LO', eave_lo, 9.0, CHS_ALL + SHS_ALL, 'low eave strut line A, 4 bays (9.0 m lobby bay governs) into node A/4')

# ================================================================ output
json.dump(SIZES, open(os.path.join(D, 'sizes.json'), 'w'), indent=1)
json.dump(dict(basis=BASIS, q=q, qh_hi=qh_hi, qh_lo=qh_lo, calc=CALC), open(os.path.join(D, 'calc.json'), 'w'), indent=1, ensure_ascii=False)
if __name__ == '__main__':
    print(f'q {q:.3f} kPa, qh_hi {qh_hi:.3f}, qh_lo {qh_lo:.3f}')
    for k, v in CALC.items(): print(f"{k:16s} {v['sec']:20s} UR {v['ur']:.2f}  {v['note'][:70]}")
