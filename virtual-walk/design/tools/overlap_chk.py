# clash check: new members (present in NEW, not in OLD) vs surviving original geometry; box shrunk 2 cm
import geo,numpy as np,sys,collections
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
_,O=geo.load(sys.argv[1]); _,N=geo.load(sys.argv[2])
def comps(C):
    out=[]
    for ch in C:
        if ch['inst'] is not None or len(ch['f'])==0 or ch['k'].startswith('site'): continue
        V=ch['v'];F=ch['f']; Vr=np.round(V,3); u,inv=np.unique(Vr,axis=0,return_inverse=True); inv=inv.ravel(); Fi=inv[F]
        r=np.concatenate([Fi[:,0],Fi[:,1]]); c=np.concatenate([Fi[:,1],Fi[:,2]])
        k,lb=connected_components(coo_matrix((np.ones(len(r)),(r,c)),shape=(len(u),len(u))),directed=False)
        fl=lb[Fi[:,0]]
        for L in np.unique(fl):
            T=u[Fi[fl==L]]; out.append((ch['k'],T))
    return out
co=comps(O); cn=comps(N)
sig=lambda k,T:(k,tuple(np.round(T.reshape(-1,3).min(0),2)),tuple(np.round(T.reshape(-1,3).max(0),2)),len(T))
so=set(sig(k,T) for k,T in co)
new=[(k,T) for k,T in cn if sig(k,T) not in so]; old=[(k,T) for k,T in cn if sig(k,T) in so]
print('new comps',len(new),'old comps',len(old))
OT=np.concatenate([T for k,T in old]); OK=np.concatenate([[i]*len(T) for i,(k,T) in enumerate(old)])
OMN=OT.min(1); OMX=OT.max(1)
hits=collections.Counter(); ex={}
for k,T in new:
    mn=T.reshape(-1,3).min(0)+0.02; mx=T.reshape(-1,3).max(0)-0.02
    if (mx<mn).any(): continue
    m=np.all(OMN<mx,1)&np.all(OMX>mn,1)
    if not m.any(): continue
    # keep triangles that really cross the box: some vertex strictly inside, or the triangle spans through
    T2=OT[m]; ins=np.all((T2>mn)&(T2<mx),2).any(1)
    span=((T2.min(1)<mn)&(T2.max(1)>mx)).sum(1)>=2
    real=ins|span
    if not real.any(): continue
    for oi in np.unique(OK[m][real]):
        key=(k.split('#')[0]+':'+k[k.index('('):k.index(')')+1],old[oi][0].split('#')[0]+':'+old[oi][0][old[oi][0].index('('):old[oi][0].index(')')+1])
        loc=tuple(np.round((mn+mx)/2,1))
        hits[key]+=1; ex.setdefault(key,[]).append(loc)
for key,n in hits.most_common(60): print(n,key,ex[key][:4])
