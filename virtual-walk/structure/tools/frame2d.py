# 2D frame (x, z) stiffness solver with P-Delta (geometric stiffness iteration). Units kN, m.
# Elements: Euler-Bernoulli, optional moment releases at ends. Loads: nodal, element UDL global-z (per member length or
# per horizontal projection), element UDL normal to member (local), element point loads (global).
import numpy as np

class Frame:
    def __init__(self):
        self.N = []; self.El = []; self.fix = {}; self.nl = {}
    def node(self, x, z):
        for i, (a, b) in enumerate(self.N):
            if abs(a - x) < 1e-6 and abs(b - z) < 1e-6: return i
        self.N.append((x, z)); return len(self.N) - 1
    def support(self, n, ux=True, uz=True, ry=True): self.fix[n] = (ux, uz, ry)
    def elem(self, i, j, E, A, I, tag='', rel=(False, False), meta=None):
        self.El.append(dict(i=i, j=j, E=E, A=A, I=I, tag=tag, rel=rel, meta=meta or {}, loads=[])); return len(self.El) - 1
    def load_node(self, case, n, fx=0, fz=0, my=0):
        d = self.nl.setdefault(case, {}); a = d.get(n, np.zeros(3)); d[n] = a + [fx, fz, my]
    def udl(self, case, e, wz=0.0, proj=False, wn=0.0, wx=0.0):
        self.El[e]['loads'].append((case, 'u', wz, proj, wn, wx))
    def pload(self, case, e, a, fx=0.0, fz=0.0):   # a: fraction along member
        self.El[e]['loads'].append((case, 'p', a, fx, fz))

    def _geom(self, el):
        (x1, z1), (x2, z2) = self.N[el['i']], self.N[el['j']]
        L = np.hypot(x2 - x1, z2 - z1); c, s = (x2 - x1) / L, (z2 - z1) / L
        return L, c, s

    def _kl(self, el, N=0.0, red=1.0):
        L, c, s = self._geom(el); E, A, I = el['E'] * red, el['A'], el['I']
        EA, EI = E * A / L, E * I
        k = np.array([[EA, 0, 0, -EA, 0, 0],
                      [0, 12 * EI / L ** 3, 6 * EI / L ** 2, 0, -12 * EI / L ** 3, 6 * EI / L ** 2],
                      [0, 6 * EI / L ** 2, 4 * EI / L, 0, -6 * EI / L ** 2, 2 * EI / L],
                      [-EA, 0, 0, EA, 0, 0],
                      [0, -12 * EI / L ** 3, -6 * EI / L ** 2, 0, 12 * EI / L ** 3, -6 * EI / L ** 2],
                      [0, 6 * EI / L ** 2, 2 * EI / L, 0, -6 * EI / L ** 2, 4 * EI / L]])
        if N != 0.0:   # geometric stiffness (N tension +)
            g = N / L * np.array([[0, 0, 0, 0, 0, 0], [0, 6 / 5, L / 10, 0, -6 / 5, L / 10], [0, L / 10, 2 * L * L / 15, 0, -L / 10, -L * L / 30],
                                  [0, 0, 0, 0, 0, 0], [0, -6 / 5, -L / 10, 0, 6 / 5, -L / 10], [0, L / 10, -L * L / 30, 0, -L / 10, 2 * L * L / 15]])
            k = k + g
        T = np.zeros((6, 6)); R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]); T[:3, :3] = R; T[3:, 3:] = R
        return k, T, L

    def _fef(self, el, case):
        """fixed-end forces in local coords for loads of this case; returns (f_local[6], list of point loads local)"""
        L, c, s = self._geom(el); f = np.zeros(6); pts = []
        for ld in el['loads']:
            if ld[0] != case: continue
            if ld[1] == 'u':
                _, _, wz, proj, wn, wx = ld
                # global z load per unit length (or projection) -> local components per member length
                wzl = wz * (abs(c) if proj else 1.0)
                qx = wzl * s + wx * c            # axial (local x)
                qy = wzl * c - wx * s + wn       # transverse (local y, +y = rotate x by +90)
                f += [-qx * L / 2, -qy * L / 2, -qy * L * L / 12, -qx * L / 2, -qy * L / 2, qy * L * L / 12]
                pts.append(('u', qx, qy))
            else:
                _, _, a, fx, fz = ld
                Px = fx * c + fz * s; Py = -fx * s + fz * c
                aa, bb = a * L, (1 - a) * L
                f += [-Px * bb / L, -Py * bb ** 2 * (3 * aa + bb) / L ** 3, -Py * aa * bb ** 2 / L ** 2,
                      -Px * aa / L, -Py * aa ** 2 * (aa + 3 * bb) / L ** 3, Py * aa ** 2 * bb / L ** 2]
                pts.append(('p', aa, Px, Py))
        return f, pts

    def solve(self, combo, pdelta=True, red=0.8, iters=6):
        """combo: {case: factor}. Returns dict with displacements and element end forces (local, kN/kNm) and stations."""
        n = len(self.N); ndof = 3 * n
        Naxial = np.zeros(len(self.El))
        for it in range(iters if pdelta else 1):
            K = np.zeros((ndof, ndof)); F = np.zeros(ndof); store = []
            for case, fac in combo.items():
                for nd, v in self.nl.get(case, {}).items(): F[3 * nd:3 * nd + 3] += fac * v
            for ei, el in enumerate(self.El):
                k, T, L = self._kl(el, Naxial[ei] if pdelta and it > 0 else 0.0, red)
                fef = np.zeros(6)
                for case, fac in combo.items():
                    fe, _ = self._fef(el, case); fef += fac * fe
                # static condensation for releases
                rel = [2] * el['rel'][0] + [5] * el['rel'][1]
                if rel:
                    keep = [d for d in range(6) if d not in rel]
                    kcc = k[np.ix_(rel, rel)]; kkc = k[np.ix_(keep, rel)]
                    kr = np.zeros((6, 6)); kr[np.ix_(keep, keep)] = k[np.ix_(keep, keep)] - kkc @ np.linalg.solve(kcc, kkc.T)
                    fr = np.zeros(6); fr[keep] = fef[keep] - kkc @ np.linalg.solve(kcc, fef[rel]); k, fef = kr, fr
                kg = T.T @ k @ T; fg = T.T @ fef
                dofs = [3 * el['i'], 3 * el['i'] + 1, 3 * el['i'] + 2, 3 * el['j'], 3 * el['j'] + 1, 3 * el['j'] + 2]
                K[np.ix_(dofs, dofs)] += kg; F[dofs] -= fg
                store.append((k, T, fef, dofs))
            fixed = []
            for nd, f3 in self.fix.items():
                for d in range(3):
                    if f3[d]: fixed.append(3 * nd + d)
            # free rotational dofs with no stiffness (all-released joints) get a tiny spring
            for d in range(2, ndof, 3):
                if K[d, d] == 0: K[d, d] = 1e-6
            free = [d for d in range(ndof) if d not in fixed]
            U = np.zeros(ndof); U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
            ends = []
            for ei, (k, T, fef, dofs) in enumerate(store):
                ul = T @ U[dofs]; f = k @ ul + fef; ends.append(f); Naxial[ei] = (f[3] - f[0]) / 2   # tension +
        R = K @ U + F * 0  # not used
        return dict(U=U, ends=ends, N=Naxial)

    def stations(self, ei, res, combo, n=11):
        """internal forces along element: list of (s, N(tension+), V, M) in local coords, M sagging +"""
        el = self.El[ei]; L, c, s = self._geom(el); f = res['ends'][ei]
        out = []
        loads = []
        for case, fac in combo.items():
            _, pts = self._fef(el, case)
            for p in pts: loads.append((fac, p))
        for k in range(n):
            x = L * k / (n - 1)
            Nn = -f[0]; V = f[1]; M = -f[2] + f[1] * x
            for fac, p in loads:
                if p[0] == 'u':
                    _, qx, qy = p; Nn -= fac * qx * x; V += fac * qy * x; M += fac * qy * x * x / 2
                else:
                    _, aa, Px, Py = p
                    if x > aa: Nn -= fac * Px; V += fac * Py; M += fac * Py * (x - aa)
            out.append((x, Nn, V, M))
        return out
