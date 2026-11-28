# Clash check: steel members (oriented section boxes) vs mz19 architecture geometry.
# Architecture placeholder steel (structure layer, red interior steel, floor build-ups) is excluded: it is what we replace.
# Usage: python3 clash.py [layout.json] -> out/clash_<version>.json + .csv
import json, os, sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'design', 'tools')); import geo
D = os.path.join(os.path.dirname(__file__), '..', 'out')
L = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, 'layout.json')))
SEC = L['sections']
_, C = geo.load(os.path.join(os.path.dirname(__file__), '..', '..', 'model'))
SKIP = ('structure#', 'interior#(0.25, 0.025, 0.025)', 'interior#(0.275, 0.05, 0.025)', 'roof#', 'site#', 'outside#', 'ceiling#')
CAT = lambda k: ('climbing wall' if k.startswith('climb') else 'glass' if '|1|0' in k[-6:] or k.endswith('|0|1|0') else
                 'duct' if k.startswith('duct') else 'wall/cladding' if k.startswith('wall') else
                 'services' if k.startswith('services') else 'interior')
P, K = [], []
for ch in C:
    if ch['inst'] is not None or ch['k'].startswith(SKIP): continue
    T = ch['v'][ch['f']]
    pts = np.concatenate([T.mean(1), (T[:, 0] + T[:, 1]) / 2, (T[:, 1] + T[:, 2]) / 2, (T[:, 2] + T[:, 0]) / 2])
    P.append(pts); K += [CAT(ch['k'])] * len(pts)
P = np.concatenate(P); K = np.array(K)
TOL = 0.005
out = []
for m in L['members']:
    p0, p1 = np.array(m['p0']), np.array(m['p1']); ax = p1 - p0; Lm = np.linalg.norm(ax)
    if Lm < 1e-6: continue
    ax /= Lm; w = np.array(m['web']); w = w - ax * (w @ ax)
    if np.linalg.norm(w) < 1e-6: w = np.cross(ax, [0, 0, 1]) if abs(ax[2]) < .9 else np.cross(ax, [1, 0, 0])
    w /= np.linalg.norm(w); f = np.cross(ax, w)
    s = SEC[m['sec']]; hh = s['h'] / 2000 - TOL; hb = s['b'] / 2000 - TOL
    lo = np.minimum(p0, p1) - .6; hi = np.maximum(p0, p1) + .6
    sel = np.all((P > lo) & (P < hi), 1)
    if not sel.any(): continue
    Q = P[sel] - p0; t = Q @ ax; a = Q @ w; b = Q @ f
    hit = (t > 0.03) & (t < Lm - 0.03) & (np.abs(a) < hh) & (np.abs(b) < hb)
    if hit.any():
        H = P[sel][hit]; cats = K[sel][hit]
        for c in sorted(set(cats)):
            hc = H[cats == c]
            out.append(dict(member=m['id'], sec=m['sec'], role=m['role'], hits=int(len(hc)), category=c,
                            at=[round(float(v), 2) for v in hc.mean(0)], min=hc.min(0).round(2).tolist(), max=hc.max(0).round(2).tolist()))
out.sort(key=lambda r: (-r['hits']))
v = L.get('version', 'x')
json.dump(out, open(os.path.join(D, f'clash_{v}.json'), 'w'), indent=1)
with open(os.path.join(D, f'clash_{v}.csv'), 'w') as fh:
    fh.write('member,section,role,category,hits,x,y,z,xmin,ymin,zmin,xmax,ymax,zmax\n')
    for r in out: fh.write(','.join(map(str, [r['member'], r['sec'], r['role'], r['category'], r['hits'], *r['at'], *r['min'], *r['max']])) + '\n')
if __name__ == '__main__':
    import collections
    print(len(out), 'clash groups;', collections.Counter(r['category'] for r in out))
    for r in out[:60]: print(f"{r['member']:6s} {r['role'][:44]:44s} {r['category']:13s} n={r['hits']:4d} at {r['at']}")
