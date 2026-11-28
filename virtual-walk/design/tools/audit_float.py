# floating-item audit: components of interior/services/outside layers with no contact (<4 cm) to any other geometry
import geo,numpy as np,sys,json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
mats,C=geo.load(sys.argv[1]); SP=0.1
BX=(-6,18,64,122,0.1,9.5)
pts=[];lab=[];comps=[]
def sample(T):
    out=[T.reshape(-1,3),T.mean(1)]
    e=np.maximum.reduce([np.linalg.norm(T[:,1]-T[:,0],axis=1),np.linalg.norm(T[:,2]-T[:,1],axis=1),np.linalg.norm(T[:,0]-T[:,2],axis=1)])
    k=np.minimum(np.ceil(e/SP).astype(int),400)
    for kk in np.unique(k):
        if kk<2: continue
        S=T[k==kk]; i,j=np.mgrid[0:kk+1,0:kk+1]; m=(i+j)<=kk; W=np.stack([1-(i[m]+j[m])/kk,i[m]/kk,j[m]/kk],1)
        for s0 in range(0,len(S),max(1,200000//len(W))): out.append(np.einsum('qk,tkd->tqd',W,S[s0:s0+max(1,200000//len(W))]).reshape(-1,3))
    return np.concatenate(out)
cid=0
for ci,ch in enumerate(C):
    if ch['inst'] is not None or len(ch['f'])==0: continue
    L=ch['k'].split('#')[0]
    if L in ('site','roof'): continue
    V=ch['v'];F=ch['f']; Vr=np.round(V,3); u,inv=np.unique(Vr,axis=0,return_inverse=True); inv=inv.ravel(); Fi=inv[F]
    r=np.concatenate([Fi[:,0],Fi[:,1]]); c=np.concatenate([Fi[:,1],Fi[:,2]])
    k,lb=connected_components(coo_matrix((np.ones(len(r)),(r,c)),shape=(len(u),len(u))),directed=False)
    fl=lb[Fi[:,0]]
    for Lb in np.unique(fl):
        T=u[Fi[fl==Lb]]
        cmn=T.reshape(-1,3).min(0); cmx=T.reshape(-1,3).max(0)
        if cmx[0]<BX[0] or cmn[0]>BX[1] or cmx[1]<BX[2] or cmn[1]>BX[3] or cmn[2]>BX[5]: continue
        P=sample(T); P=P[(P[:,0]>BX[0])&(P[:,0]<BX[1])&(P[:,1]>BX[2])&(P[:,1]<BX[3])]
        if len(P)==0: continue
        P=P.astype(np.float32)
        pts.append(P); lab.append(np.full(len(P),cid))
        comps.append((ci,ch['k'],T.reshape(-1,3).min(0),T.reshape(-1,3).max(0),L)); cid+=1
P=np.concatenate(pts); Lb=np.concatenate(lab); print('points',len(P),'comps',cid)
tree=cKDTree(P)
float_=[]
starts=np.cumsum([0]+[len(p) for p in pts])
for i,(ci,k,mn,mx,L) in enumerate(comps):
    if L not in ('interior','services','outside','climb'): continue
    if (mx-mn).max()>8: continue
    Q=pts[i]
    if len(Q)>3000: Q=Q[np.random.default_rng(0).choice(len(Q),3000,replace=False)]
    nb=tree.query_ball_point(Q,0.04)
    ok=any(any(Lb[j]!=i for j in lst) for lst in nb)
    if not ok: float_.append((L,k,mn.round(2).tolist(),mx.round(2).tolist()))
print('floating',len(float_))
json.dump(float_,open('/tmp/float.json','w'))
for f in float_[:200]: print(f)
