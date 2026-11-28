# Phase 3 outputs: frame moment envelopes (PNG), per-member UR table, base reactions, tonnage by group.
import json, os, csv, math, collections
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import sizing as S
from steel import LIB
D = S.D; P = os.path.join(D, 'p3'); os.makedirs(P, exist_ok=True)
L = json.load(open(os.path.join(D, 'layout.json')))
CALC = S.CALC

# ---------------------------------------------------------------- frame moment envelopes
plt.rcParams.update({'font.size': 8, 'font.family': 'DejaVu Sans'})
FIGS = []
for key, cf in S.FR.items():
    col, raf = S.SIZES[f'MF_{key}_COL'], S.SIZES[f'MF_{key}_RAF']; lr = S.SIZES.get('MF_STEP_LRAF') if key == 'STEP' else None
    gi = cf['grids'][0]
    f, cols, rafs, lows, knees, _ = S.build_frame(key, gi, col, raf, lr)
    env = collections.defaultdict(lambda: [None, None])
    for cname, combo in S.COMBOS:
        r = f.solve(combo, pdelta=True, red=0.8)
        for e in cols + rafs + lows:
            for k, st in enumerate(f.stations(e, r, combo, 9)):
                M = st[3]; a = env[(e, k)]
                a[0] = M if a[0] is None else max(a[0], M); a[1] = M if a[1] is None else min(a[1], M)
    fig, ax = plt.subplots(figsize=(11, 7.5))
    mmax = max(max(abs(v[0]), abs(v[1])) for v in env.values())
    sc = 2.2 / mmax
    for e in cols + rafs + lows:
        el = f.El[e]; (x1, z1), (x2, z2) = f.N[el['i']], f.N[el['j']]
        ax.plot([x1, x2], [z1, z2], color='#333', lw=2.2 if el['tag'] != 'haunch' else 3.5)
        Lx, c, s = f._geom(el); nx, nz = -s, c
        for idx, clr in ((0, '#c0392b'), (1, '#2e86c1')):
            pts = []
            for k in range(9):
                t = k / 8; M = env[(e, k)][idx]
                px, pz = x1 + (x2 - x1) * t, z1 + (z2 - z1) * t
                pts.append((px - nx * M * sc, pz - nz * M * sc))
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=clr, lw=0.9)
        for k in (0, 8):
            for idx in (0, 1):
                M = env[(e, k)][idx]
                if abs(M) > 0.25 * mmax:
                    t = k / 8; px, pz = x1 + (x2 - x1) * t, z1 + (z2 - z1) * t
                    ax.text(px - nx * M * sc, pz - nz * M * sc, f'{M:.0f}', fontsize=6.5, color='#c0392b' if idx == 0 else '#2e86c1')
    ax.set_aspect('equal'); ax.set_title(f'Frame {key} (grid {", ".join(str(g+1) for g in cf["grids"])}): {col} / {raf}{" / low " + lr if lr else ""}  '
                                         f'M envelope kNm (red max, blue min), 2nd-order DAM, {len(S.COMBOS)} combos', loc='left', fontsize=9)
    ax.axhline(0.2, color='#999', lw=.5); ax.set_xlabel('x (m)'); ax.set_ylabel('z (m)')
    fn = f'P3-F_{key}.png'; fig.savefig(os.path.join(P, fn), dpi=120, bbox_inches='tight'); plt.close(fig); FIGS.append(fn)

# ---------------------------------------------------------------- per-member UR table
rows = []
for m in L['members']:
    g = m['grp']; c = CALC.get(g)
    if g.startswith('MF_') and g.endswith('_RAF'): c = dict(CALC[g]); c['checks'] = CALC[g.replace('_RAF', '_COL')]['checks']
    ur = c['ur'] if c else None
    gov = max(c['checks'], key=lambda x: x[1]) if c and c.get('checks') else None
    rows.append(dict(mark=m['id'], group=g, section=m['sec'], grade=m['grade'], length_m=m['L'], kg=m['kg'], role=m['role'],
                     UR=ur if ur is not None else '', governing=(gov[0] + ': ' + gov[2]) if gov else ('detailing / nominal' if not c else c['note'])))
with open(os.path.join(D, 'members_ur.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ur_json = {g: dict(sec=v['sec'], ur=v['ur'], note=v['note'], checks=v['checks']) for g, v in CALC.items()}
json.dump(ur_json, open(os.path.join(D, 'ur.json'), 'w'), ensure_ascii=False)

# ---------------------------------------------------------------- base reactions (unfactored, per case) for foundations
reac = []
for key in S.FR:
    for gy, cases in CALC[f'MF_{key}_COL'].get('reactions', {}).items():
        for side in ('A', 'B'):
            row = dict(support=f'{side}/{S.GY.index(float(gy)) + 1}', type='portal ' + S.FR[key]['base'])
            for case, R in cases.items():
                if side in R: row[f'{case}_H'], row[f'{case}_V'], row[f'{case}_M'] = R[side]
            reac.append(row)
with open(os.path.join(D, 'reactions.csv'), 'w', newline='') as fh:
    keys = sorted({k for r in reac for k in r}, key=lambda k: (k not in ('support', 'type'), k))
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(reac)

# ---------------------------------------------------------------- tonnage by group
ton = collections.defaultdict(lambda: [0, 0.0, ''])
for m in L['members']: t = ton[m['grp']]; t[0] += 1; t[1] += m['kg']; t[2] = m['sec']
json.dump(dict(figs=FIGS, tonnage={k: [v[0], round(v[1], 1), v[2]] for k, v in ton.items()}, reactions=reac,
               total=round(sum(m['kg'] for m in L['members']) / 1000, 2)), open(os.path.join(D, 'p3_summary.json'), 'w'), ensure_ascii=False)
print('figs', FIGS, 'members', len(rows), 'total t', round(sum(m['kg'] for m in L['members']) / 1000, 1))
