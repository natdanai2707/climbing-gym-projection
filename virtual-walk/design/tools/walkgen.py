import numpy as np,collections
X0,Y0,RES=-16.5,51.5,0.1; NX,NY=380,950
SKIP=('roof','duct','services','ceiling')
def tris(C):
    out=[]
    for ch in C:
        L=ch['k'].split('#')[0]
        if L in SKIP: continue
        V=ch['v']
        if ch['inst'] is None: out.append(V[ch['f']])
        else:
            P=V[ch['f']]
            for t in ch['inst']: out.append(P+t)
    return np.concatenate(out)
def sample_keys(P,zscale,step=0.07):
    """returns unique (cellkey, round(z*zscale)) pairs, computed in small batches"""
    e=np.stack([np.linalg.norm(P[:,1]-P[:,0],axis=1),np.linalg.norm(P[:,2]-P[:,1],axis=1),np.linalg.norm(P[:,0]-P[:,2],axis=1)],1).max(1)
    k=np.maximum(1,np.ceil(e/step)).astype(int); k=np.minimum(k,2500)
    acc=[]
    for kk in np.unique(k):
        S=P[k==kk]
        i,j=np.mgrid[0:kk+1,0:kk+1]; m=(i+j)<=kk; W=np.stack([1-(i[m]+j[m])/kk,i[m]/kk,j[m]/kk],1)
        bs=max(1,400000//len(W))
        for s0 in range(0,len(S),bs):
            Wc=W
            for w0 in range(0,len(W),400000):
                Wp=W[w0:w0+400000]
                Q=np.einsum('qk,tkd->tqd',Wp,S[s0:s0+bs]).reshape(-1,3)
                ix=((Q[:,0]-X0)/RES).astype(np.int64); iy=((Q[:,1]-Y0)/RES).astype(np.int64)
                mm=(ix>=0)&(ix<NX)&(iy>=0)&(iy<NY)
                pr=(ix[mm]*NY+iy[mm])*100000+np.round(Q[mm,2]*zscale).astype(np.int64)+50000
                acc.append(np.unique(pr))
        if len(acc)>50: acc=[np.unique(np.concatenate(acc))]
    u=np.unique(np.concatenate(acc)) if acc else np.zeros(0,np.int64)
    return u//100000,(u%100000)-50000
def gen(C):
    P=tris(C)
    c=P.mean(1); keep=(c[:,2]<9.5)&(c[:,0]>X0)&(c[:,0]<X0+NX*RES)&(c[:,1]>Y0)&(c[:,1]<Y0+NY*RES); P=P[keep]
    n=np.cross(P[:,1]-P[:,0],P[:,2]-P[:,0]); l=np.linalg.norm(n,axis=1); ok=l>1e-9; P=P[ok]; nz=n[ok,2]/l[ok]
    up=P[nz>0.7]; down=P[nz<-0.7]; vert=P[np.abs(nz)<=0.7]
    fl=collections.defaultdict(set); vz=collections.defaultdict(list)
    K,Z=sample_keys(up,100)
    for k_,zz in zip(K.tolist(),Z.tolist()): fl[k_].add(zz/100)
    # faces modelled upside-down (flipped normals) still read as floors, unless an upward face sits just above them (slab undersides)
    K,Z=sample_keys(down,100); dn=collections.defaultdict(set)
    for k_,zz in zip(K.tolist(),Z.tolist()): dn[k_].add(zz/100)
    for k_,hs in dn.items():
        ups=fl.get(k_,set())
        for h in hs:
            if not any(h<u<=h+0.6 for u in ups): fl[k_].add(h)
    K,Z=sample_keys(vert,20)
    for k_,zz in zip(K.tolist(),Z.tolist()): vz[k_].append(zz/20)
    # merge floors closer than 3cm
    F={}
    for k_,s in fl.items():
        s=sorted(s); r=[s[0]]
        for h in s[1:]:
            if h-r[-1]>0.03: r.append(h)
            else: r[-1]=h
        F[k_]=r
    V={}
    for k_,zs in vz.items():
        iv=[[zs[0],zs[0]]]
        for z_ in zs[1:]:
            if z_-iv[-1][1]<=0.26: iv[-1][1]=z_
            else: iv.append([z_,z_])
        fls=F.get(k_,[])
        res=[]
        for a,b in iv:
            if b-a<0.46 and any(abs(h-b)<0.08 for h in fls): continue   # step / riser / platform edge
            # deck edge beside a stair: a tread inside the lower part of the face makes the top reachable
            if any(abs(h-b)<0.08 for h in fls) and any(0.05<b-h<0.46 and h-a<1.0 for h in fls): continue
            if b-a<0.1 and not any(abs(h-b)<0.08 for h in fls) and b<0.3: continue
            res.append((round(a,2),round(b,2)))
        if res: V[k_]=res
    return F,V
