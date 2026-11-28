import numpy as np,geo,sys
from collections import deque
D=sys.argv[1]; VX=float(sys.argv[2]) if len(sys.argv)>2 else 0.12
mats,C=geo.load(D)
X0,Y0,Z0=-18.0,46.0,-1.0; NX,NY,NZ=int(40/VX),int(94/VX),int(19/VX)
S=np.zeros((NX,NY,NZ),bool)
def vi_(p): return tuple(np.floor((np.array(p)-[X0,Y0,Z0])/VX).astype(int))
skip=('site#',)   # keep everything (ground included)
for ch in C:
    if len(ch['f'])==0: continue
    V=ch['v'] if ch['inst'] is None else None
    insts=[np.zeros(3)] if ch['inst'] is None else list(ch['inst'])
    T0=ch['v'][ch['f']]
    for off in insts:
        T=T0+off
        e=np.maximum(np.linalg.norm(T[:,1]-T[:,0],axis=1),np.linalg.norm(T[:,2]-T[:,0],axis=1))
        e=np.maximum(e,np.linalg.norm(T[:,2]-T[:,1],axis=1))
        n=np.clip(np.ceil(e/(VX*0.45)).astype(int),1,4000)
        for k in np.unique(n):
            Tk=T[n==k]
            u,v=np.meshgrid(np.arange(k+1),np.arange(k+1)); m=(u+v)<=k; u=u[m]/k; v=v[m]/k
            P=Tk[:,None,0]+u[None,:,None]*(Tk[:,None,1]-Tk[:,None,0])+v[None,:,None]*(Tk[:,None,2]-Tk[:,None,0])
            P=P.reshape(-1,3); I=np.floor((P-[X0,Y0,Z0])/VX).astype(int)
            ok=(I[:,0]>=0)&(I[:,0]<NX)&(I[:,1]>=0)&(I[:,1]<NY)&(I[:,2]>=0)&(I[:,2]<NZ); I=I[ok]
            S[I[:,0],I[:,1],I[:,2]]=True
import json,os
VP=json.load(open('virtual_doors.json')) if os.path.exists('virtual_doors.json') else []
for b in VP:   # closed-door panels used only for the test: [x0,x1,y0,y1,z0,z1]
    i0=vi_((b[0],b[2],b[4])); i1=vi_((b[1],b[3],b[5]))
    S[i0[0]:i1[0]+1,i0[1]:i1[1]+1,i0[2]:i1[2]+1]=True
print('solid voxels',S.sum(),'virtual doors',len(VP))
def vi(p): return tuple(np.floor((np.array(p)-[X0,Y0,Z0])/VX).astype(int))
seed=vi((8.0,108.0,2.5)); assert not S[seed]
par=np.full(S.shape,-1,np.int8); par[seed]=6
dirs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
front=[seed]; hit=None; it=0
F=np.array([seed])
while len(F) and hit is None:
    nxt=[]
    for di,(dx,dy,dz) in enumerate(dirs):
        G=F+[dx,dy,dz]
        ok=(G[:,0]>=0)&(G[:,0]<NX)&(G[:,1]>=0)&(G[:,1]<NY)&(G[:,2]>=0)&(G[:,2]<NZ)
        if (~ok).any(): hit=F[~ok][0]; break
        G=G[ok]; m=(~S[G[:,0],G[:,1],G[:,2]])&(par[G[:,0],G[:,1],G[:,2]]==-1)
        G=np.unique(G[m],axis=0)
        par[G[:,0],G[:,1],G[:,2]]=di; nxt.append(G)
    if hit is None: F=np.concatenate(nxt) if nxt else np.zeros((0,3),int); it+=1
reached=(par>=0).sum()
if hit is None:
    print('SEALED reached',reached)
    for nm,pt in [('front L2 above deck, Edge part',(-3.5,105,4.6)),('front L2 above deck, climbing part',(-3.2,80,4.8)),('front L2 above bridge',(-1.0,92,5.0)),
                  ('gallery below deck (outdoor)',(-3.5,105,2.0)),('gallery below deck climbing (outdoor)',(-3.2,80,2.0)),('entrance recess (outdoor)',(-3.5,93,2.0)),
                  ('lobby',(3,91,2)),('climbing floor',(6,84,2)),('L2 bouldering',(4,74.5,7.2)),('co-working',(10,92,5))]:
        print('  %-40s %s'%(nm,'INSIDE' if par[vi(pt)]>=0 else 'outside'))
    sys.exit(0)
# trace path back
p=np.array(hit); path=[p.copy()]
while par[tuple(p)]!=6:
    d=dirs[par[tuple(p)]]; p=p-d; path.append(p.copy())
path=np.array(path[::-1])*VX+[X0,Y0,Z0]+VX/2
print('LEAK path length',len(path))
# report where the path leaves the building box
i=np.where((path[:,0]<-1.0)|(path[:,1]<68.0)|(path[:,1]>117.2)|(path[:,2]>7.6))[0]
print('first exit-ish points'); print(np.round(path[max(0,i[0]-6):i[0]+10:2],2) if len(i) else '')
inb=(path[:,0]>-5.0)&(path[:,0]<17.0)&(path[:,1]>67.6)&(path[:,1]<117.6)&(path[:,2]<16.4)
k=np.where(~inb)[0][0] if (~inb).any() else len(path)-1
print('last inside-building points:'); print(np.round(path[max(0,k-12):k+3:2],2))
np.save('/tmp/leakpath.npy',path)
