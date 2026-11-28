# Phase 2 review drawings: member layout over the mz19 architecture (plan per level, frame elevations, long elevations)
import json, os, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from archview import tris, view
D = os.path.join(os.path.dirname(__file__), '..', 'out'); P = os.path.join(D, 'p2'); os.makedirs(P, exist_ok=True)
L = json.load(open(os.path.join(D, 'layout.json'))); M = L['members']
GY = list(L['grids']['y'].values()); GN = list(L['grids']['y'].keys())
COL = dict(MAIN='#c0392b', ROOF='#2e86c1', BRACE='#16a085', WALL='#7f8c8d', FL2='#d35400', BD='#8e44ad', CM='#b7950b', BR='#b7950b', STAIR='#1e8449', MISC='#5d6d7e')
plt.rcParams.update({'font.size': 8, 'font.family': 'DejaVu Sans'})

def grid(ax, plan=True, zmax=16):
    for g, n in zip(GY, GN):
        ax.axvline(g, color='k', lw=.4, ls=(0, (8, 3, 2, 3)), zorder=1)
        ax.text(g, ax.get_ylim()[1], n, ha='center', va='bottom', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='circle', fc='w', ec='k', lw=.6))
    if plan:
        for x, n in ((-4.84, 'A'), (16.86, 'B')):
            ax.axhline(x, color='k', lw=.4, ls=(0, (8, 3, 2, 3)), zorder=1)
            ax.text(ax.get_xlim()[0], x, n + ' ', ha='right', va='center', fontsize=10, fontweight='bold')
    for a, b in zip(GY[:-1], GY[1:]):
        ax.annotate('', (a, ax.get_ylim()[0]), (b, ax.get_ylim()[0]), arrowprops=dict(arrowstyle='<->', lw=.5))
        ax.text((a + b) / 2, ax.get_ylim()[0], f'{(b-a)*1000:.0f}', ha='center', va='bottom', fontsize=7)

def lines(ax, sel, ax_i, lw=1.2, label=True, labsel=None):
    seen = set()
    for m in M:
        if not sel(m): continue
        p, q = np.array(m['p0']), np.array(m['p1'])
        c = COL[m['sys']]
        w = lw * (1.8 if m['pre'] in ('C', 'R', 'B', 'WP') and m['sys'] in ('MAIN', 'FL2', 'BD', 'CM') else 1)
        if np.linalg.norm((q - p)[ax_i]) < 1e-3:
            ax.plot(p[ax_i[0]], p[ax_i[1]], 's', color=c, ms=5 if m['pre'] in ('C', 'WP') else 3, zorder=5)
        else:
            ax.plot([p[ax_i[0]], q[ax_i[0]]], [p[ax_i[1]], q[ax_i[1]]], color=c, lw=w, zorder=4,
                    ls='--' if m['pre'] in ('RB', 'VB', 'SR') else '-')
        if label and (labsel is None or labsel(m)):
            key = (m['sec'], m['pre'], round(p[ax_i[0]], 0), round(p[ax_i[1]], 0))
            if key in seen: continue
            seen.add(key)
            mid = (p + q) / 2
            ax.text(mid[ax_i[0]], mid[ax_i[1]], m['sec'], fontsize=5.5, color=c, rotation=0, ha='center', va='bottom', zorder=6,
                    bbox=dict(fc='w', ec='none', alpha=.7, pad=.3))

def plan(name, z0, z1, sel, title, arch=True, labsel=None):
    f, ax = plt.subplots(figsize=(24, 7.5))
    if arch:
        T, cl = tris(box=(np.array([-5.5, 65.5, z0 - 0.3]), np.array([17.5, 119.5, z1])))
        cl = 1 - (1 - np.clip(cl * 1.6, 0, 1)) * 0.55
        view(ax, T, cl, [1, 0], 2, alpha=.9)
    ax.set_xlim(64.5, 120.5); ax.set_ylim(-6.5, 18.5); ax.set_aspect('equal')
    grid(ax)
    lines(ax, sel, [1, 0], labsel=labsel)
    ax.set_title(title, fontsize=12, loc='left'); ax.set_xlabel('y (m)'); ax.set_ylabel('x (m)')
    f.savefig(os.path.join(P, name), dpi=130, bbox_inches='tight'); plt.close(f)

plan('P2-01_roof.png', 7, 17, lambda m: m['sys'] in ('ROOF', 'BRACE') and m['pre'] in ('P', 'SR', 'RB', 'ST', 'ES') and m['p0'][2] > 6.5
     or m['pre'] == 'R', 'P2-01  ROOF FRAMING PLAN  (rafters red, purlins blue @ ~1.17 m, X-bracing green dashed, sag rods dashed)',
     arch=False, labsel=lambda m: m['pre'] in ('R',) or (m['pre'] == 'P' and abs(m['p0'][0] - 0.0) < 0.6))
plan('P2-02_frontL2.png', 2.5, 4.4, lambda m: m['sys'] in ('FL2',) and m['pre'] != 'FP' or (m['sys'] == 'MAIN' and m['pre'] == 'C') or m['sys'] in ('CM', 'BR') or m['ref'] == 'x',
     'P2-02  +3.4..+4.2 FRAMING PLAN  front L2 (orange), co-working mezz + bridge (gold), main columns (red)',
     labsel=lambda m: m['pre'] in ('B', 'C') and m['sys'] != 'MAIN')
plan('P2-03_boulder.png', 4.4, 6.4, lambda m: m['sys'] in ('BD', 'STAIR') or (m['sys'] == 'MAIN' and m['pre'] in ('C', 'WP') and m['p0'][1] < 89),
     'P2-03  +6.3 L2 BOULDERING DECK + STAIRS  (deck purple, stairs green)', labsel=lambda m: m['pre'] in ('B', 'J', 'C', 'SS', 'SC'))

def elev(name, sel, ax_i, xl, title, arch_box=None, depth=None, rev=False, figsize=(14, 8), labsel=None):
    f, ax = plt.subplots(figsize=figsize)
    if arch_box is not None:
        T, cl = tris(box=arch_box)
        cl = 1 - (1 - np.clip(cl * 1.6, 0, 1)) * 0.55
        view(ax, T, cl, ax_i, depth, rev=rev, alpha=.9)
    ax.set_xlim(*xl); ax.set_ylim(-0.5, 17.5); ax.set_aspect('equal')
    lines(ax, sel, ax_i, labsel=labsel)
    for zz, t in ((0.2, '+0.20'), (1.0, 'FFL +1.00'), (7.0, '+7.00'), (15.0, '+15.00')):
        ax.axhline(zz, color='k', lw=.3, ls=':'); ax.text(xl[1], zz, ' ' + t, va='center', fontsize=7)
    ax.set_title(title, fontsize=11, loc='left')
    f.savefig(os.path.join(P, name), dpi=130, bbox_inches='tight'); plt.close(f)

near = lambda y0, tol=0.35: (lambda m: abs(m['p0'][1] - y0) < tol and abs(m['p1'][1] - y0) < tol)
for gi in (0, 1, 3, 5, 7):
    g = GY[gi]
    elev(f'P2-1{gi+1}_grid{gi+1}.png', near(g, 0.4), [0, 2], (-7, 19), f'GRID {gi+1}  (y = {g})  frame elevation, looking north',
         arch_box=(np.array([-5.5, g - 0.6, -1]), np.array([17.5, g + 0.6, 17])), depth=1, rev=False,
         labsel=lambda m: m['pre'] in ('C', 'R', 'WP', 'B', 'HN'))
xa = lambda x0, tol=0.6: (lambda m: abs(m['p0'][0] - x0) < tol and abs(m['p1'][0] - x0) < tol)
elev('P2-21_lineA.png', xa(-4.84), [1, 2], (64.5, 120.5), 'LINE A (front, x = -4.84)  long elevation from the street',
     figsize=(24, 8), labsel=lambda m: m['pre'] in ('C', 'VB', 'ES'))
elev('P2-22_lineB.png', xa(16.86), [1, 2], (64.5, 120.5), 'LINE B (rear, x = 16.86)  long elevation from inside',
     arch_box=(np.array([14.5, 66, -1]), np.array([17.5, 119, 17])), depth=0, rev=False, figsize=(24, 8), labsel=lambda m: m['pre'] in ('C', 'VB', 'ES'))
print('drawings in', P)
