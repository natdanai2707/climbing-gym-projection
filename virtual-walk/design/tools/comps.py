import geo,numpy as np,sys
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
m,C=geo.load(sys.argv[1]); B=[float(v) for v in sys.argv[2].split(',')]
keyf=sys.argv[3] if len(sys.argv)>3 else ''
for ci,ch in enumerate(C):
    if ch['inst'] is not None or keyf not in ch['k']: continue
    V=ch['v'];F=ch['f']; c=V[F].mean(1)
    s=(c[:,0]>B[0])&(c[:,0]<B[1])&(c[:,1]>B[2])&(c[:,1]<B[3])&(c[:,2]>B[4])&(c[:,2]<B[5])
    if not s.any(): continue
    Fs=F[s]; Vr=np.round(V,3); u,inv=np.unique(Vr,axis=0,return_inverse=True); inv=inv.ravel(); Fi=inv[Fs]
    r=np.concatenate([Fi[:,0],Fi[:,1]]); cc=np.concatenate([Fi[:,1],Fi[:,2]])
    n=len(u); g=coo_matrix((np.ones(len(r)),(r,cc)),shape=(n,n)); k,lab=connected_components(g,directed=False)
    fl=lab[Fi[:,0]]
    for L in np.unique(fl):
        Q=u[np.unique(Fi[fl==L])]; mn=Q.min(0);mx=Q.max(0)
        print(ci,ch['k'][:44],mn.round(2),mx.round(2))
