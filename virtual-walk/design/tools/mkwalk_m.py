import json,numpy as np,collections,sys,os
from scipy import ndimage
import walkgen as W, geo
SRC=sys.argv[1]; OUT=sys.argv[2]
mats,C=geo.load(SRC)
F,V=W.gen(C)
def rects(m):
    out=[]; m=m.copy()
    for i,j in np.argwhere(m):
        if not m[i,j]: continue
        j2=j
        while j2+1<m.shape[1] and m[i,j2+1]: j2+=1
        i2=i
        while i2+1<m.shape[0] and m[i2+1,j:j2+1].all(): i2+=1
        m[i:i2+1,j:j2+1]=False; out.append((i,i2+1,j,j2+1))
    return out
def boxes(groups,minc=1,label=False):
    res=[]
    for key,cells in groups.items():
        if len(cells)<minc: continue
        i0=min(c[0] for c in cells); j0=min(c[1] for c in cells); i1=max(c[0] for c in cells); j1=max(c[1] for c in cells)
        m=np.zeros((i1-i0+1,j1-j0+1),bool)
        for i,j in cells: m[i-i0,j-j0]=True
        if label:
            lab,n=ndimage.label(m); s=ndimage.sum(m,lab,range(1,n+1)); m=np.isin(lab,np.where(s>=minc)[0]+1)
        for a,b,c,d in rects(m):
            x0=W.X0+(i0+a)*W.RES; x1=W.X0+(i0+b)*W.RES; y0=W.Y0+(j0+c)*W.RES; y1=W.Y0+(j0+d)*W.RES
            res.append([round(x0,2),round(x1,2),round(-y1,2),round(-y0,2)]+list(key))
    return res
byh=collections.defaultdict(list)
for k,hs in F.items():
    for h in hs:
        if h<=8.0: byh[(round(h/0.02)*0.02,)].append((k//W.NY,k%W.NY))
walk=boxes(byh,6,True)
byiv=collections.defaultdict(list)
for k,ivs in V.items():
    for a,b in ivs:
        if a<=8.6: byiv[(round(a/0.05)*0.05,round(b/0.05)*0.05)].append((k//W.NY,k%W.NY))
col=boxes(byiv)
DOORS=[(-2.4,-1.5,88.62,90.08,0.5,3.0),(-2.4,-1.5,95.92,97.38,0.5,3.0),(-2.1,-1.8,110.8,111.85,1.0,2.82),(-2.8,-1.24,97.35,97.78,4.25,6.4)]
for x,y in [(6.25,94.63),(8.55,88.85),(8.55,90.15),(8.55,91.15),(10.66,92.45),(10.66,96.65)]:
    DOORS.append((x-0.35,x+0.35,y-0.55,y+0.55,1.05,3.0))
DOORS.append((15.48-0.55,15.48+0.55,84.45-0.35,84.45+0.35,1.05,3.0))
for yl in (88.45,97.5):
    for xa,xb in ((8.84,9.48),(9.74,10.38)): DOORS.append((xa,xb,yl-0.2,yl+0.2,-0.5,2.05))
def door_clip(r):
    x0,x1,z0,z1,a,b=r; y0,y1=-z1,-z0
    for dx0,dx1,dy0,dy1,za,zb in DOORS:
        if x0<dx1 and x1>dx0 and y0<dy1 and y1>dy0 and a<zb and b>za:
            out=[]
            for c0,c1,e0,e1 in ((x0,dx0,y0,y1),(dx1,x1,y0,y1),(max(x0,dx0),min(x1,dx1),y0,dy0),(max(x0,dx0),min(x1,dx1),dy1,y1)):
                if c1-c0>1e-3 and e1-e0>1e-3: out.append([round(c0,3),round(c1,3),round(-e1,3),round(-e0,3),a,b])
            return [q for o in out for q in door_clip(o)]
    return [r]
col=[q for r in col for q in door_clip(r)]
json.dump(dict(walk=walk,col=col),open(OUT,'w'),separators=(',',':'))
print('walk',len(walk),'col',len(col),os.path.getsize(OUT))
