# Section library (TIS/JIS sizes on the Thai market) + AISC 360-16 LRFD member checks + AISI-style checks for cold-formed C.
# Units: N, mm, MPa internally; helpers return kN, kNm.
import math

E = 200000.0
G = 77200.0

# ---------------------------------------------------------------- catalogue
# H: (h, b, tw, tf, r)  JIS G3192 / TIS 1227
H_CAT = [
    (100, 100, 6, 8, 10), (125, 125, 6.5, 9, 10), (148, 100, 6, 9, 11), (150, 75, 5, 7, 8), (150, 150, 7, 10, 11),
    (175, 175, 7.5, 11, 12), (194, 150, 6, 9, 13), (200, 100, 5.5, 8, 11), (200, 200, 8, 12, 13), (244, 175, 7, 11, 16),
    (250, 125, 6, 9, 12), (250, 250, 9, 14, 16), (294, 200, 8, 12, 18), (300, 150, 6.5, 9, 13), (300, 300, 10, 15, 18),
    (340, 250, 9, 14, 20), (350, 175, 7, 11, 14), (350, 350, 12, 19, 20), (390, 300, 10, 16, 22), (400, 200, 8, 13, 16),
    (400, 400, 13, 21, 22), (440, 300, 11, 18, 24), (450, 200, 9, 14, 18), (488, 300, 11, 18, 26), (500, 200, 10, 16, 20),
    (588, 300, 12, 20, 28), (600, 200, 11, 17, 22), (700, 300, 13, 24, 28), (800, 300, 14, 26, 28), (900, 300, 16, 28, 28),
]
# lipped C (h, b, c, t)  TIS 1228
C_CAT = [(100, 50, 20, 2.3), (100, 50, 20, 3.2), (125, 50, 20, 2.3), (125, 50, 20, 3.2), (150, 50, 20, 2.3), (150, 50, 20, 3.2),
         (150, 65, 20, 2.3), (150, 65, 20, 3.2), (150, 75, 20, 3.2), (200, 75, 20, 3.2), (200, 75, 25, 4.5), (250, 75, 25, 4.5)]
SHS_CAT = [(50, 50, 2.3), (50, 50, 3.2), (75, 75, 3.2), (100, 100, 3.2), (100, 100, 4.5), (125, 125, 4.5), (125, 125, 6.0),
           (150, 150, 4.5), (150, 150, 6.0), (150, 150, 9.0), (200, 200, 6.0), (200, 200, 9.0), (250, 250, 9.0),
           (100, 50, 3.2), (150, 100, 4.5), (200, 100, 6.0)]
CHS_CAT = [(48.6, 3.2), (60.5, 3.2), (76.3, 3.2), (89.1, 3.2), (101.6, 4.0), (114.3, 4.5), (139.8, 4.5), (139.8, 6.0),
           (165.2, 5.0), (165.2, 7.1), (216.3, 8.2), (267.4, 9.3)]
RB_CAT = [12, 16, 20, 24, 27, 30, 33, 36]

GRADE = {'SS400': (245, 400), 'SM520': (355, 520), 'SSC400': (245, 400), 'STKR400': (245, 400), 'STK400': (235, 400), 'SR24': (235, 380)}

def name_H(h, b, tw, tf, r=None): return f'H{h:g}x{b:g}x{tw:g}x{tf:g}'
def name_C(h, b, c, t): return f'C{h:g}x{b:g}x{c:g}x{t:g}'
def name_SHS(h, b, t): return f'SHS{h:g}x{b:g}x{t:g}' if h == b else f'RHS{h:g}x{b:g}x{t:g}'
def name_CHS(d, t): return f'CHS{d:g}x{t:g}'
def name_RB(d): return f'RB{d}'

def props_H(h, b, tw, tf, r):
    hw = h - 2 * tf
    Af = (4 - math.pi) * r * r                       # 4 fillets
    yf = h / 2 - tf - 0.2234 * r; zf = tw / 2 + 0.2234 * r
    A = 2 * b * tf + hw * tw + Af
    Ix = 2 * (b * tf ** 3 / 12 + b * tf * (h / 2 - tf / 2) ** 2) + tw * hw ** 3 / 12 + Af * yf ** 2
    Iy = 2 * tf * b ** 3 / 12 + hw * tw ** 3 / 12 + Af * zf ** 2
    Zx = 2 * b * tf * (h / 2 - tf / 2) + tw * (hw / 2) ** 2 + Af * yf
    Zy = tf * b ** 2 / 2 + hw * tw ** 2 / 4 + Af * zf
    J = (2 * b * tf ** 3 + (h - tf) * tw ** 3) / 3
    ho = h - tf; Cw = Iy * ho ** 2 / 4
    Sx = Ix / (h / 2); Sy = Iy / (b / 2)
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    return dict(t='H', h=h, b=b, tw=tw, tf=tf, r=r, A=A, Ix=Ix, Iy=Iy, Zx=Zx, Zy=Zy, Sx=Sx, Sy=Sy, J=J, Cw=Cw, ho=ho, rts=rts,
                rx=math.sqrt(Ix / A), ry=math.sqrt(Iy / A), hw_clear=h - 2 * tf - 2 * r, kgm=A * 7.85e-3)

def props_C(h, b, c, t):
    # centreline thin-walled model, web on y axis
    hc, bc, cc = h - t, b - t, c - t / 2
    parts = [(t, hc, 0, 0), (bc, t, bc / 2, hc / 2), (bc, t, bc / 2, -hc / 2), (t, cc, bc, hc / 2 - cc / 2), (t, cc, bc, -hc / 2 + cc / 2)]
    A = sum(w * d for w, d, _, _ in parts)
    xc = sum(w * d * x for w, d, x, _ in parts) / A
    Ix = sum(w * d ** 3 / 12 + w * d * y ** 2 for w, d, _, y in parts)
    Iy = sum(d * w ** 3 / 12 + w * d * (x - xc) ** 2 for w, d, x, _ in parts)
    Sx = Ix / (h / 2)
    J = (hc + 2 * bc + 2 * cc) * t ** 3 / 3
    rho = 0.92 if t >= 3.2 else 0.85                 # effective section modulus factor (local buckling), conservative
    return dict(t='C', h=h, b=b, c=c, tw=t, tf=t, A=A, Ix=Ix, Iy=Iy, Sx=Sx, Se=rho * Sx, Sy=Iy / (b - xc), J=J, xc=xc,
                rx=math.sqrt(Ix / A), ry=math.sqrt(Iy / A), kgm=A * 7.85e-3)

def props_SHS(h, b, t):
    ro = 2 * t
    A = 2 * t * (h + b - 2 * t) - (4 - math.pi) * (ro ** 2 - (ro - t) ** 2)
    Ix = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12
    Iy = (h * b ** 3 - (h - 2 * t) * (b - 2 * t) ** 3) / 12
    Zx = (b * h ** 2 - (b - 2 * t) * (h - 2 * t) ** 2) / 4
    Zy = (h * b ** 2 - (h - 2 * t) * (b - 2 * t) ** 2) / 4
    J = 2 * t ** 2 * (h - t) ** 2 * (b - t) ** 2 / ((h + b - 2 * t) * t)
    return dict(t='SHS', h=h, b=b, tw=t, A=A, Ix=Ix, Iy=Iy, Zx=Zx, Zy=Zy, Sx=Ix / (h / 2), Sy=Iy / (b / 2), J=J,
                rx=math.sqrt(Ix / A), ry=math.sqrt(Iy / A), kgm=A * 7.85e-3)

def props_CHS(d, t):
    A = math.pi / 4 * (d ** 2 - (d - 2 * t) ** 2); I = math.pi / 64 * (d ** 4 - (d - 2 * t) ** 4)
    Z = (d ** 3 - (d - 2 * t) ** 3) / 6
    return dict(t='CHS', h=d, b=d, tw=t, A=A, Ix=I, Iy=I, Zx=Z, Zy=Z, Sx=I / (d / 2), Sy=I / (d / 2), J=2 * I, rx=math.sqrt(I / A), ry=math.sqrt(I / A), kgm=A * 7.85e-3)

def props_RB(d):
    A = math.pi * d * d / 4; I = math.pi * d ** 4 / 64
    return dict(t='RB', h=d, b=d, tw=d / 2, A=A, Ix=I, Iy=I, Zx=d ** 3 / 6, Zy=d ** 3 / 6, Sx=I / (d / 2), Sy=I / (d / 2), J=2 * I, rx=d / 4, ry=d / 4, kgm=A * 7.85e-3)

def lib():
    L = {}
    for s in H_CAT: L[name_H(*s)] = props_H(*s)
    for s in C_CAT: L[name_C(*s)] = props_C(*s)
    for s in SHS_CAT: L[name_SHS(*s)] = props_SHS(*s)
    for s in CHS_CAT: L[name_CHS(*s)] = props_CHS(*s)
    for d in RB_CAT: L[name_RB(d)] = props_RB(d)
    return L
LIB = lib()

def built_I(h, b, tw, tf):
    """welded I (haunch depth) without fillets"""
    return props_H(h, b, tw, tf, 0.0)

# ---------------------------------------------------------------- AISC 360-16 LRFD, doubly symmetric I
def comp_I(p, Fy, Lcx, Lcy):
    lam_r = 1.49 * math.sqrt(E / Fy)
    KLr = max(Lcx / p['rx'], Lcy / p['ry'], 1e-6)
    Fe = math.pi ** 2 * E / KLr ** 2
    Fcr = (0.658 ** (Fy / Fe)) * Fy if Fy / Fe <= 2.25 else 0.877 * Fe
    Ae = p['A']
    hw = p['hw_clear']; lam = hw / p['tw']
    if lam > lam_r * math.sqrt(Fy / Fcr):              # E7 slender web
        Fel = (1.31 * lam_r / lam) ** 2 * Fy
        be = hw * (1 - 0.18 * math.sqrt(Fel / Fcr)) * math.sqrt(Fel / Fcr)
        Ae -= (hw - min(be, hw)) * p['tw']
    bf = p['b'] / 2 / p['tf']; lam_rf = 0.56 * math.sqrt(E / Fy)
    if bf > lam_rf * math.sqrt(Fy / Fcr):
        Fel = (1.49 * lam_rf / bf) ** 2 * Fy; bfe = p['b'] / 2 * (1 - 0.22 * math.sqrt(Fel / Fcr)) * math.sqrt(Fel / Fcr)
        Ae -= 4 * (p['b'] / 2 - bfe) * p['tf']
    return 0.9 * Fcr * Ae / 1e3, KLr                    # kN

def flex_I(p, Fy, Lb, Cb=1.0):
    Mp = Fy * p['Zx']
    lpf, lrf = 0.38 * math.sqrt(E / Fy), 1.0 * math.sqrt(E / Fy)
    lf = p['b'] / 2 / p['tf']
    Mn_flb = Mp if lf <= lpf else Mp - (Mp - 0.7 * Fy * p['Sx']) * (lf - lpf) / (lrf - lpf)
    Lp = 1.76 * p['ry'] * math.sqrt(E / Fy)
    rts, J, Sx, ho = p['rts'], p['J'], p['Sx'], p['ho']
    Lr = 1.95 * rts * E / (0.7 * Fy) * math.sqrt(J / (Sx * ho) + math.sqrt((J / (Sx * ho)) ** 2 + 6.76 * (0.7 * Fy / E) ** 2))
    if Lb <= Lp: Mn = Mp
    elif Lb <= Lr: Mn = min(Mp, Cb * (Mp - (Mp - 0.7 * Fy * Sx) * (Lb - Lp) / (Lr - Lp)))
    else:
        Fcr = Cb * math.pi ** 2 * E / (Lb / rts) ** 2 * math.sqrt(1 + 0.078 * J / (Sx * ho) * (Lb / rts) ** 2)
        Mn = min(Mp, Fcr * Sx)
    return 0.9 * min(Mn, Mn_flb) / 1e6                   # kNm

def flex_I_minor(p, Fy):
    return 0.9 * min(Fy * p['Zy'], 1.6 * Fy * p['Sy']) / 1e6

def shear_I(p, Fy):
    hw = p['h'] - 2 * p['tf']; Aw = p['h'] * p['tw']
    phi = 1.0 if hw / p['tw'] <= 2.24 * math.sqrt(E / Fy) else 0.9
    return phi * 0.6 * Fy * Aw / 1e3

def interact(Pu, Pc, Mux, Mcx, Muy=0.0, Mcy=1e9):
    r = abs(Pu) / Pc
    if r >= 0.2: return r + 8 / 9 * (abs(Mux) / Mcx + abs(Muy) / Mcy)
    return r / 2 + abs(Mux) / Mcx + abs(Muy) / Mcy

def tension(p, Fy, Fu, threaded=False):
    if threaded: return 0.75 * 0.75 * Fu * p['A'] / 1e3
    return 0.9 * Fy * p['A'] / 1e3

# ---------------------------------------------------------------- HSS / round bar
def comp_simple(p, Fy, Lc):
    KLr = max(Lc / min(p['rx'], p['ry']), 1e-6)
    Fe = math.pi ** 2 * E / KLr ** 2
    Fcr = (0.658 ** (Fy / Fe)) * Fy if Fy / Fe <= 2.25 else 0.877 * Fe
    return 0.9 * Fcr * p['A'] / 1e3, KLr

def flex_hss(p, Fy):
    return 0.9 * Fy * p['Zx'] / 1e6

# ---------------------------------------------------------------- cold-formed lipped C (AISI S100 simplified)
def flex_C(p, Fy, braced=True, R=None):
    """braced: compression flange restrained by sheeting (gravity). Uplift: R-factor method (AISI I6.2.1)."""
    Mn = Fy * p['Se']
    if not braced:
        if R is None:
            d = p['h']
            R = 0.70 if d <= 165 else (0.65 if d <= 216 else 0.50)
        Mn *= R
    return 0.9 * Mn / 1e6

def comp_C(p, Fy, Lcx, Lcy):
    KLr = max(Lcx / p['rx'], Lcy / p['ry'])
    Fe = math.pi ** 2 * E / KLr ** 2
    Fn = (0.658 ** (Fy / Fe)) * Fy if Fy / Fe <= 2.25 else 0.877 * Fe
    Ae = p['A'] * (0.85 if p['tw'] >= 3.2 else 0.75)   # effective area, conservative
    return 0.85 * Fn * Ae / 1e3, KLr
