# Front ribbon as L2 walkway (v2): keep the original red ribbon form (zig-zag plan, sloped underside, 1.5 m overhang
# past both end walls) but give it a flat, stepped (terraced) top; guardrails both sides; a stair from the L2 bouldering
# deck down onto the ribbon; the central L2 walkway extended west to the ribbon; central spiral rebuilt with 150 deg sweep.
import numpy as np,geo,os,math
SRC=os.environ.get('SRC',os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','base')); OUT=os.environ.get('OUT','out_build')
mats,C=geo.load(SRC)
RED='interior#(0.25, 0.025, 0.025)|0.75|0|0|0'; FLR='interior#(0.275, 0.05, 0.025)|0.5|0|0|0'
WOOD='interior#(0.4, 0.225, 0.1)|0.5|0|0|0'; BLK='interior#(0.025, 0.025, 0.025)|0.5|0|0|0'
STL='structure#(0.1, 0.025, 0.025)|0.75|0|0|0'
GLS='wall#(0.0, 0.0, 0.0)|0.5|0|1|0'; GRY='interior#(0.275, 0.275, 0.25)|1.0|0|0|0'
for k in (RED,FLR,WOOD,BLK,STL,GLS,GRY): assert k in mats,k
SC=(2.0,95.6)   # old spiral centre
def all_in(P,box): return ((P[...,0]>=box[0])&(P[...,0]<=box[1])&(P[...,1]>=box[2])&(P[...,1]<=box[3])&(P[...,2]>=box[4])&(P[...,2]<=box[5])).all(1)
removed={}
for ch in C:
    if ch['inst'] is not None: continue
    P=ch['v'][ch['f']]
    if ch['k']==RED:
        kill=all_in(P,(-5.1,0.0,66.0,119.5,2.4,4.25))            # the old ribbon (rebuilt below)
        kill|=all_in(P,(1.9,2.05,95.4,97.7,3.95,5.1))             # guard at the west end of the central walkway
        kill|=all_in(P,(-1.85,1.25,74.05,76.85,1.1,7.35))         # old climbing-zone spiral (ground -> L2 bouldering)
        kill|=all_in(P,(-1.85,1.25,74.2,76.85,0.9,7.35))          # its leftover post standing on the floor
        kill|=all_in(P,(-1.5,-0.45,75.25,75.75,6.25,7.6))          # deck north-edge guard where the new stair lands
        kill|=all_in(P,(-1.5,-0.45,74.05,74.2,6.25,7.6))           # original deck-edge guard where the stair arrives
    elif ch['k'].startswith('wall#(0.875, 0.875, 0.85)'):
        Pt=P; ok_y=(Pt[...,1].max(1)<=88.39)|(Pt[...,1].min(1)>=97.61)
        kill=all_in(P,(-5.1,0.5,66.0,119.5,3.3,4.25))&ok_y
        kill|=all_in(P,(-5.0,-1.88,88.37,97.63,4.19,4.26))       # white floor patches beside the courtyard -> red floor
    elif ch['k']==STL:
        r=np.hypot(P[...,0]-SC[0],P[...,1]-SC[1])
        kill=((r<=2.02).all(1))&((P[...,2]>=1.0)&(P[...,2]<=5.3)).all(1)&((P[...,0]<=2.07)).all(1)   # old spiral
        kill|=all_in(P,(-0.13,0.23,69.55,74.13,0.99,6.01))         # L2 bouldering column + beam in front of the stairs (moved to the corner)
    elif ch['k']=='wall#(0.875, 0.875, 0.85)|0.75|0|0|0' and False: pass
    elif ch['k']==GLS:
        kill=all_in(P,(-1.96,-0.08,97.5,97.62,4.19,6.31))          # glass between central and Edge-side front L2 (rebuilt with a door)
    elif ch['k'].startswith('outside#'):
        kill=all_in(P,(-3.2,-2.4,66.0,119.5,2.6,3.6))             # old soffit downlights (the closed soffit is gone; new lights under the deck)
    else: continue
    removed[ch['k'][:30]]=removed.get(ch['k'][:30],0)+int(kill.sum()); ch['f']=ch['f'][~kill]
print('removed',removed)
for ch in C:
    if ch['k']!='interior#(0.275, 0.275, 0.25)|1.0|0|0|0' or ch['inst'] is not None: continue
    V=ch['v']; sel=(V[:,0]>14.79)&(V[:,0]<16.83)&(V[:,1]>101.88)&(V[:,1]<106.02)&(V[:,2]>3.6)
    ch['v']=V.copy(); ch['v'][sel,2]=3.6; print('room verts lowered',int(sel.sum()))
add={}
def put(k,v,f): add.setdefault(k,[]).append((np.asarray(v,float),np.asarray(f)))
HEX=np.array([[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]])
def box(k,x0,x1,y0,y1,z0,z1):
    put(k,[[x,y,z] for z in (z0,z1) for y in (y0,y1) for x in (x0,x1)],HEX)
def hexa(k,b,t):
    """b,t: 4 corners each (bottom/top) ordered [y0x0,y0x1,y1x0,y1x1]"""
    put(k,list(b)+list(t),HEX)
def bar(k,a,b,w,h):
    a=np.array(a,float); b=np.array(b,float); d=b-a; L=max(np.linalg.norm(d[:2]),1e-9)
    u=np.array([d[0],d[1],0])/L; s=np.array([-u[1],u[0],0]); pts=[]
    for p in (a,b):
        for dz in (-h/2,h/2):
            for ds in (-w/2,w/2): pts.append(p+s*ds+np.array([0,0,dz]))
    put(k,pts,np.array([[0,1,2],[1,3,2],[4,6,5],[5,6,7],[0,4,1],[1,4,5],[2,3,6],[3,7,6],[0,2,4],[2,6,4],[1,5,3],[3,5,7]]))
def guard(p0,p1,z0,z1=None,h=1.1,h1=None):
    """red steel guard (posts, top + bottom rail, 20 mm balusters @120); z1 for a sloped (stair) guard"""
    z1=z0 if z1 is None else z1; p0=np.array(p0,float); p1=np.array(p1,float); L=np.hypot(*(p1-p0))
    if L<0.05: return
    zz=lambda t:z0+(z1-z0)*t
    h1=h if h1 is None else h1; hh=lambda t:h+(h1-h)*t
    bar(RED,[*p0,zz(0)+h],[*p1,zz(1)+h1],0.05,0.05); bar(RED,[*p0,zz(0)+0.1],[*p1,zz(1)+0.1],0.04,0.04)
    n=max(1,int(L/1.5))
    for i in range(n+1):
        t=i/n; p=p0+(p1-p0)*t; box(RED,p[0]-.025,p[0]+.025,p[1]-.025,p[1]+.025,zz(t),zz(t)+hh(t))
    m=int(L/0.12)
    for i in range(1,m):
        t=i/m; p=p0+(p1-p0)*t; box(RED,p[0]-.01,p[0]+.01,p[1]-.01,p[1]+.01,zz(t)+0.12,zz(t)+hh(t)-0.03)
# ---------------- 1. ribbon: original plan + underside, terraced top
# plan breakpoints (y, x_west, x_east) and underside z(y), from the original geometry
PLAN=[(66.1,-3.99,-1.99),(74.9,-3.99,-1.99),(80.9,-3.24,-1.24),(82.4,-3.24,-1.24),(88.4,-2.09,-0.09),(97.62,-2.09,-0.09),
      (103.62,-3.24,-1.24),(105.12,-3.24,-1.24),(111.12,-3.99,-1.99),(119.1,-3.99,-1.99)]
UND=[(66.1,2.8),(74.9,2.8),(80.9,3.2),(82.4,3.2),(88.4,3.6),(97.62,3.6),(103.62,3.2),(105.12,3.2),(111.12,2.8),(119.1,2.8)]
ys=[p[0] for p in PLAN]
xw=lambda y:np.interp(y,ys,[p[1] for p in PLAN]); xe=lambda y:np.interp(y,ys,[p[2] for p in PLAN])
und=lambda y:np.interp(y,[u[0] for u in UND],[u[1] for u in UND])
# terraces: (y0,y1,top) - 0.2 m steps that stay on or above the original sloped top (underside + 0.6)
TER=[(66.1,74.9,3.4),(74.9,77.9,3.6),(77.9,80.9,3.8),(80.9,82.4,3.8),(82.4,85.4,4.0),(85.4,88.4,4.2),(88.4,97.62,4.2),
     (97.62,100.62,4.2),(100.62,103.62,4.0),(103.62,105.12,3.8),(105.12,108.12,3.8),(108.12,111.12,3.6),(111.12,119.1,3.4)]
lvl=lambda y:[t for a,b,t in TER if a<=y<b or (y==119.1 and b==119.1)][0]
# floor finder (original geometry, before additions): highest up-facing surface below z at (x,y)
_T=[]
for ch in C:
    if ch['inst'] is not None or len(ch['f'])==0 or ch['k'].startswith(('roof','ceiling','duct','services')): continue
    T=ch['v'][ch['f']]; n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); l=np.linalg.norm(n,axis=1)
    _T.append(T[(n[:,2]/np.maximum(l,1e-12))>0.9])
_T=np.concatenate(_T)
def floor_at(x,y,zmax):
    a,b,c=_T[:,0,:2],_T[:,1,:2],_T[:,2,:2]; p=np.array([x,y])
    s_=lambda u,v:(u[:,0]-p[0])*(v[:,1]-p[1])-(v[:,0]-p[0])*(u[:,1]-p[1])
    d1,d2,d3=s_(a,b),s_(b,c),s_(c,a); ins=~(((d1<0)|(d2<0)|(d3<0))&((d1>0)|(d2>0)|(d3>0)))
    z=_T[:,:,2].mean(1); m=ins&(z<zmax)
    return float(z[m].max()) if m.any() else 0.2
# steel mezzanine: per terrace a deck (finish + 10 mm plate), edge beams 100x200, joists 80x150 @ <=1.2 m, riser plates
PL=0.012; EB=0.2; JB=0.15
for i,(y0,y1,top) in enumerate(TER):
    q=lambda z:[[xw(y0),y0,z],[xe(y0),y0,z],[xw(y1),y1,z],[xe(y1),y1,z]]
    hexa(FLR,q(top-0.02),q(top)); hexa(STL,q(top-0.02-PL),q(top-0.02))
    zb=top-0.02-PL-EB/2
    for f,off in ((xw,0.05),(xe,-0.05)): bar(STL,[f(y0)+off,y0,zb],[f(y1)+off,y1,zb],0.1,EB)
    n=max(1,math.ceil((y1-y0)/1.2))
    for j in range(n+1):
        yy=y0+(y1-y0)*j/n; yy=min(max(yy,y0+0.04),y1-0.04)
        bar(STL,[xw(yy)+0.1,yy,top-0.02-PL-JB/2],[xe(yy)-0.1,yy,top-0.02-PL-JB/2],0.08,JB)
    if i+1<len(TER):                    # riser plate at a step change
        t2=TER[i+1][2]; lo,hi=sorted((top,t2))
        if hi-lo>0.01: put(STL,[[xw(y1),y1-0.006,lo-0.03],[xe(y1),y1-0.006,lo-0.03],[xw(y1),y1+0.006,lo-0.03],[xe(y1),y1+0.006,lo-0.03],
                                [xw(y1),y1-0.006,hi],[xe(y1),y1-0.006,hi],[xw(y1),y1+0.006,hi],[xe(y1),y1+0.006,hi]],HEX)
# columns: outer row = the building's own facade columns (x -4.84); no middle row; inner row under the ribbon east edge beam
#          on the building grid; at the wide entrance span two extra columns stand on the glass line (x -1.85), clear of the doors
DOORS=[(88.55,90.2),(95.85,97.5)]
GRID=[67.75,74.65,81.55,88.45,97.45,104.05,110.65,117.25]
cols=[]
def column(x,yy,top):
    base=floor_at(x,yy,top-0.3)
    box(STL,x-0.075,x+0.075,yy-0.075,yy+0.075,base,top); box(STL,x-0.15,x+0.15,yy-0.15,yy+0.15,base,base+0.02)
    cols.append((round(x,2),yy,round(base,2),round(top,2)))
for yy in GRID:                      # (inner columns at y 91.0 / 95.0 removed)
    x=xe(yy)-0.1
    if abs(x+1.97)<0.12: x=-1.97+(0.13 if x>-1.97 else -0.13)
    column(x,yy,lvl(yy)-0.02-PL-EB)
for yy in (91.0,95.0): column(-1.85,yy,lvl(yy)-0.02-PL-EB)
# primary cross beams 150x300 on the grid: building column -> inner column, under the joists
for yy in GRID:
    tz=lvl(yy)-0.02-PL-JB
    bar(STL,[-4.99,yy,tz-0.15],[xe(yy)-0.02,yy,tz-0.15],0.15,0.3)
print('columns',len(cols)); print(cols)
# glass head along the interior glass line x = -1.965 (from the original geometry)
_G=np.concatenate([c['v'][c['f']] for c in C if c['k']==GLS and c['inst'] is None])
_G=_G[(np.abs(_G[...,0].mean(1)+1.965)<0.03)]
def glass_top(y):
    segs=[]
    for T in _G:
        zs=[]
        for i,j in ((0,1),(1,2),(2,0)):
            A,B=T[i],T[j]; dy=B[1]-A[1]
            if abs(dy)<1e-9:
                if abs(A[1]-y)<1e-6: zs+= [A[2],B[2]]
                continue
            t=(y-A[1])/dy
            if 0<=t<=1: zs.append(A[2]+t*(B[2]-A[2]))
        if len(zs)>=2: segs.append((min(zs),max(zs)))
    if not segs: return 1.0
    segs.sort(); top=None
    for lo,hi in segs:
        if top is None:
            if lo>1.2: break
            top=hi
        elif lo<=top+0.02: top=max(top,hi)
        else: break
    return top if top is not None else 1.0
# ---------------- 2. air-tight closure: the front L2 floor spans facade wall -> glass line (infill beside the red ribbon),
#                     glass extended from its 3.6 m head up to the deck plate wherever the deck is higher
XF=-4.99; XG=-1.96
INSIDE=[(67.58,88.38),(97.62,117.63)]          # inside the end walls, outside the entrance recess zone
def clip(y0,y1):
    out=[]
    for a_,b_ in INSIDE:
        lo,hi=max(y0,a_),min(y1,b_)
        if hi-lo>1e-6: out.append((lo,hi))
    return out
for (t0,t1,top) in TER:
    for y0,y1 in clip(t0,t1):
        # west infill: facade wall -> ribbon west edge
        q=lambda z:[[XF,y0,z],[xw(y0),y0,z],[XF,y1,z],[xw(y1),y1,z]]
        hexa(FLR,q(top-0.02),q(top)); hexa(STL,q(top-0.02-PL),q(top-0.02))
        bar(STL,[XF+0.05,y0,top-0.032-EB/2],[XF+0.05,y1,top-0.032-EB/2],0.1,EB)
        n=max(1,math.ceil((y1-y0)/1.2))
        for j in range(n+1):
            yy=min(max(y0+(y1-y0)*j/n,y0+0.04),y1-0.04); bar(STL,[XF+0.1,yy,top-0.032-JB/2],[xw(yy)-0.05,yy,top-0.032-JB/2],0.08,JB)
        # east sliver: ribbon east edge -> glass line, where the ribbon stays outside the glass
        if min(xe(y0),xe(y1))<XG-0.005:
            ea,eb=min(xe(y0),XG),min(xe(y1),XG)
            put(FLR,[[ea,y0,top-0.02],[XG,y0,top-0.02],[eb,y1,top-0.02],[XG,y1,top-0.02],[ea,y0,top],[XG,y0,top],[eb,y1,top],[XG,y1,top]],HEX)
            put(STL,[[ea,y0,top-0.032],[XG,y0,top-0.032],[eb,y1,top-0.032],[XG,y1,top-0.032],[ea,y0,top-0.02],[XG,y0,top-0.02],[eb,y1,top-0.02],[XG,y1,top-0.02]],HEX)
    # glass up to the deck plate wherever the plate is above the existing glass head (+3.6)
    zt=top-0.032
    y0,y1=max(t0,67.58),min(t1,117.63)
    if y1>y0:
        ys_=np.arange(y0,y1,0.25).tolist()+[y1]
        for a_,b_ in zip(ys_[:-1],ys_[1:]):
            g=min(glass_top(a_+0.01),glass_top(b_-0.01),glass_top((a_+b_)/2))
            if zt>g+0.005: box(GLS,-1.985,-1.955,a_,b_,g,zt)
def edge_guard(side,y0,y1,skip=()):
    cuts=sorted(set([y0,y1]+[a for a,b,t in TER if y0<a<y1]+[v for sk in skip for v in sk if y0<v<y1]+([75.14,110.88] if side>0 else [])))
    for a,b in zip(cuts[:-1],cuts[1:]):
        for s0,s1 in skip:            # leave openings
            if a>=s0 and b<=s1: break
        else:
            f=xw if side<0 else (lambda y:max(xe(y),-1.96) if any(p<=y<=q for p,q in ((67.58,88.38),(97.62,117.63))) else xe(y)); off=0.04*(1 if side<0 else -1)
            guard((f(a)+off,a),(f(b)+off,b),lvl(a))
# west guards are no longer needed (floor runs to the facade wall); east edge keeps its guard
YS,YN=67.58,117.6
# ---------------- 3. climbing-zone access, all inside the glass line
def spiral2(CX,CY,R,Z0,Z1,N,A0,SW,ccw=True,RP=0.09):
    d=SW/N*(1 if ccw else -1)
    for i in range(N):
        a1=A0+i*d; a2=a1+d*1.08; z=Z0+(i+1)*(Z1-Z0)/N
        pts=[[CX+r*math.cos(a),CY+r*math.sin(a)] for a in (a1,a2) for r in (RP,R)]
        put(STL,[[p[0],p[1],z-0.05] for p in pts]+[[p[0],p[1],z] for p in pts],HEX)
        ac=(a1+a2)/2; px,py=CX+(R-0.05)*math.cos(ac),CY+(R-0.05)*math.sin(ac)
        box(STL,px-.012,px+.012,py-.012,py+.012,z,z+0.95)
        bar(STL,[CX+(R-0.05)*math.cos(a1),CY+(R-0.05)*math.sin(a1),z+0.95],[CX+(R-0.05)*math.cos(a1+d),CY+(R-0.05)*math.sin(a1+d),z+0.95+(Z1-Z0)/N],0.04,0.04)
    for j in range(12):
        a=2*math.pi*j/12; b2=2*math.pi*(j+1)/12
        put(STL,[[CX+RP*math.cos(a),CY+RP*math.sin(a),Z0],[CX+RP*math.cos(b2),CY+RP*math.sin(b2),Z0],
                 [CX+RP*math.cos(a),CY+RP*math.sin(a),Z1+1.0],[CX+RP*math.cos(b2),CY+RP*math.sin(b2),Z1+1.0]],np.array([[0,1,2],[1,3,2]]))
SPIRAL_OPEN=(0,0)
# 3b. straight stair inside the glass line: front L2 (+3.8 terrace) -> L2 bouldering steel floor edge (+6.3)
ZT=6.3; ZB=3.8; NR=14; RISE=(ZT-ZB)/NR; GO=0.27; SX0,SX1=-1.45,-0.5
YT=74.15; YB=YT+(NR-1)*GO                                    # 77.61: stair top bears on the deck edge beam (y 74.05), deck notched
for i in range(1,NR):
    z=ZT-i*RISE; y0=YT+(i-1)*GO; y1=y0+GO
    box(FLR,SX0+.05,SX1-.05,y0,y1,z-0.04,z)
for x in (SX0+.03,SX1-.03): bar(STL,[x,YT,ZT-0.2],[x,YB+0.2,ZB-0.2],0.06,0.28)
FX0=xe(YB+0.45)-0.02
# 3a. second straight stair beside it (scissor): climbing floor -> the same landing (+3.8), descending south
NX0,NX1=-0.45,0.5; ZF=floor_at(0.0,YB-4.0,3.0); NR2=16; RISE2=(ZB-ZF)/NR2
for i in range(1,NR2):
    z=ZB-i*RISE2; y1=YB-(i-1)*GO; y0=y1-GO
    box(FLR,NX0+.05,NX1-.05,y0,y1,z-0.04,z)
YF=YB-(NR2-1)*GO
for x in (NX0+.03,NX1-.03): bar(STL,[x,YB+0.2,ZB-0.2],[x,YF-0.2,ZF+0.05],0.06,0.28)
box(FLR,FX0,NX1,YB,YB+0.9,ZB-0.02,ZB); box(RED,FX0,NX1,YB,YB+0.9,ZB-0.25,ZB-0.02)          # shared landing on the ribbon
guard((SX0,YT),(SX0,YB),ZT,ZB+RISE,h=0.84,h1=1.1); guard((SX1,YT),(SX1,YB),ZT,ZB+RISE,h=0.84,h1=1.1)   # meets the 0.84 deck guard at the top
guard((NX0,YB),(NX0,YF),ZB,ZF+RISE2); guard((NX1,YB),(NX1,YF),ZB,ZF+RISE2)
guard((FX0,YB+0.9),(NX1,YB+0.9),ZB); guard((NX1,YB),(NX1,YB+0.9),ZB)
# landing carried by the stringers and the ribbon edge beam (no post)
box(STL,-1.375,-1.225,YB+0.75,YB+0.9,floor_at(-1.3,YB+0.82,3.0),ZB-0.25)                  # post under the foot plate
STAIR_OPEN=(max(YB,77.9),YB+0.9)
# 3c. fill the old spiral hole in the L2 bouldering steel floor (+6.3)
edge_guard(+1,YS,YN,skip=[(95.5,97.62),SPIRAL_OPEN,STAIR_OPEN])   # east edge (over the interior); openings at the links
# 3d. full-height barrier: central front L2 cannot walk onto the climbing-side front L2 (gate bypass)
guard((-4.66,88.4),(xe(88.4)-0.02,88.4),4.2,h=2.3)      # starts clear of the building column
# ---------------- 4. central walkway extended west to the ribbon (+4.2)
box(FLR,-0.09,2.09,95.5,97.53,4.18,4.2); box(RED,-0.09,2.09,95.5,97.53,3.9,4.18)   # stops at the glass
# north edge: the glass partition is the barrier (no rail overlapping it)
# ---------------- 5. central spiral rebuilt: 150 deg sweep, clockwise, arriving northward at the walkway's south side
CX,CY=1.31,95.38; R=1.4; RP=0.09; Z0,Z1=1.0,4.2; N=18; SW=math.radians(220); A_END=math.pi  # smaller spiral pulled west: 1.0 m clear in front of the counter
A0=A_END+SW                                                                                  # start (cw sweep)
d=SW/N
for i in range(N):
    a1=A0-i*d; a2=a1-d*1.08; z=Z0+(i+1)*(Z1-Z0)/N
    pts=[]
    for a in (a1,a2):
        for r in (RP,R): pts.append([CX+r*math.cos(a),CY+r*math.sin(a)])
    b=[[p[0],p[1],z-0.05] for p in pts]; t=[[p[0],p[1],z] for p in pts]
    put(STL,b+t,np.array([[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]]))
    ac=(a1+a2)/2; px,py=CX+(R-0.05)*math.cos(ac),CY+(R-0.05)*math.sin(ac)
    for fa in (0.17,0.5,0.83):                                                                # 3 balusters per tread
        aa=a1-d*fa; px,py=CX+(R-0.05)*math.cos(aa),CY+(R-0.05)*math.sin(aa)
        box(STL,px-.012,px+.012,py-.012,py+.012,z,z+0.95)
for i in range(N):                                                                          # helical handrail
    a1=A0-i*d; a2=a1-d; za=Z0+(i+1)*(Z1-Z0)/N+0.95; zb=za+(Z1-Z0)/N
    bar(STL,[CX+(R-0.05)*math.cos(a1),CY+(R-0.05)*math.sin(a1),za],[CX+(R-0.05)*math.cos(a2),CY+(R-0.05)*math.sin(a2),zb],0.04,0.04)
k=12
for j in range(k):                                                                          # centre pole
    a=2*math.pi*j/k; b2=2*math.pi*(j+1)/k
    put(STL,[[CX+RP*math.cos(a),CY+RP*math.sin(a),Z0],[CX+RP*math.cos(b2),CY+RP*math.sin(b2),Z0],
             [CX+RP*math.cos(a),CY+RP*math.sin(a),Z1+1.0],[CX+RP*math.cos(b2),CY+RP*math.sin(b2),Z1+1.0]],np.array([[0,1,2],[1,3,2]]))
# guard on the walkway's south edge west of the spiral arrival, and the ribbon/bridge east edge over the lobby void
guard((CX-0.04,95.5),(2.09,95.5),4.2)     # walkway south edge east of the spiral arrival
# ---------------- 6. co-working desks on the long flat terraces (desk along the east rail, chair facing it)
def desk(x0,x1,y0,y1,z,top=0.75):
    box(WOOD,x0,x1,y0,y1,z+top-0.03,z+top)
    for x in (x0+.03,x1-.07):
        for y in (y0+.03,y1-.07): box(BLK,x,x+.04,y,y+.04,z,z+top-0.03)
def chair(cx,cy,z,face):
    box(BLK,cx-.21,cx+.21,cy-.21,cy+.21,z+.43,z+.47)
    for dx in (-.18,.16):
        for dy in (-.18,.16): box(BLK,cx+dx,cx+dx+.025,cy+dy,cy+dy+.025,z,z+.43)
    bx=cx-face*.2; box(BLK,bx-.02,bx+.02,cy-.2,cy+.2,z+.47,z+.86)
def run(y0,y1):
    z=lvl(y0); n=int((y1-y0)/1.15)
    for i in range(n):
        yy=y0+i*1.15; x_e=min(xe(yy),xe(yy+1.15))-0.12
        desk(x_e-0.5,x_e,yy+0.05,yy+1.1,z); chair(x_e-0.92,yy+0.575,z,+1)
for y0,y1 in ((111.5,117.3),(105.4,107.9),(88.9,95.2)): run(y0,y1)
# climbing-side front L2: work desks along the east rail on each flat terrace (stair landing kept clear)
for y0,y1 in ((67.8,74.8),(75.0,77.8),(78.7,80.85),(82.5,85.35),(85.5,88.3)): run(y0,y1)

# ---------------- 7. L2 bouldering: column + beam moved to the deck's west corner, guardrails completed
box(STL,-1.45,-1.25,73.85,74.05,floor_at(-1.35,73.95,3.0),5.55); box(STL,-1.52,-1.18,73.78,74.12,floor_at(-1.35,73.95,3.0),floor_at(-1.35,73.95,3.0)+0.02)
box(STL,-1.45,-1.25,69.6,74.05,5.55,5.57); box(STL,-1.45,-1.25,69.6,74.05,5.98,6.0); box(STL,-1.36,-1.34,69.6,74.05,5.57,5.98)
DZ=6.3
DH=0.84   # same height as the original L2 bouldering guard (+7.14)
guard((-1.475,69.56),(-1.475,74.13),DZ,h=DH)            # west edge (drop to the front L2)
guard((-0.48,74.13),(1.32,74.13),DZ,h=DH)            # deck edge guard on the original edge line, beside the stair opening
# ---------------- 8. glass partition with a double glass door: central front L2 <-> Edge-side front L2 (no barrier)
FRM='interior#(0.225, 0.225, 0.225)|0.5|0|0|0'; GZ0,GZ1,GY=4.2,6.3,97.555
DX0,DX1=-2.82,-1.22
for a_,b_ in ((-4.99,DX0),(DX1,-0.09)): box(GLS,a_,b_,GY-0.006,GY+0.006,GZ0,GZ1)
for a_,b_ in ((DX0,(DX0+DX1)/2-0.005),((DX0+DX1)/2+0.005,DX1)): box(GLS,a_+0.04,b_-0.04,GY-0.006,GY+0.006,GZ0+0.04,GZ1-0.08)  # door leaves
for x in (-4.99,-3.95,DX0,(DX0+DX1)/2-0.04,(DX0+DX1)/2,DX1,-0.6,-0.13): box(FRM,x,x+0.04,GY-0.03,GY+0.03,GZ0,GZ1)
box(FRM,-4.99,-0.09,GY-0.03,GY+0.03,GZ1-0.08,GZ1)
for x in ((DX0+DX1)/2-0.12,(DX0+DX1)/2+0.1):
    for sgn in (-1,1):
        box(FRM,x,x+0.02,GY+sgn*0.06-0.01,GY+sgn*0.06+0.01,GZ0+0.8,GZ0+1.6)                   # pull handles
        for zz in (GZ0+0.85,GZ0+1.55): box(FRM,x+0.003,x+0.017,min(GY,GY+sgn*0.06),max(GY,GY+sgn*0.06),zz-0.007,zz+0.007)
# ---------------- 9. gypsum partition above the glass line y 97.6 (head +6.3) up to the roof sheet (gable, ridge x 6.0)
GYP='wall#(0.875, 0.875, 0.85)|0.75|0|0|0'
rz=lambda x:max(6.31,7.53-abs(x-6.0)*0.0888)       # underside of the gable rafter on this line
xs=sorted(set([-4.99,-1.99,6.0,16.94]+list(np.arange(-4.5,16.9,1.0))))
for a_,b_ in zip(xs[:-1],xs[1:]):
    hexa(GYP,[[a_,97.565,6.3],[b_,97.565,6.3],[a_,97.68,6.3],[b_,97.68,6.3]],[[a_,97.565,rz(a_)],[b_,97.565,rz(b_)],[a_,97.68,rz(a_)],[b_,97.68,rz(b_)]])
# ---------------- 10. wall counters + stools on the widened red floor (along the facade wall, inside zones)
def counter(y0,y1,z):
    box(WOOD,XF+0.02,XF+0.47,y0,y1,z+1.02,z+1.05); box(BLK,XF+0.02,XF+0.06,y0,y1,z,z+1.02)
    n=int((y1-y0)/0.7)
    for i in range(n):
        cy=y0+0.35+i*0.7; box(BLK,XF+0.66,XF+0.98,cy-0.16,cy+0.16,z+0.72,z+0.76); box(BLK,XF+0.80,XF+0.84,cy-0.02,cy+0.02,z,z+0.72)
for y0,y1 in ((68.2,74.6),(98.2,100.4),(105.4,107.9),(111.5,117.2)): counter(y0,y1,lvl(y0))

# ---------------- 11. white patches beside the tree courtyard become red front L2 floor; glass behind the courtyard slat screens;
#                      Edge partition (glass + gypsum) and the climbing-side barrier carried across to the facade wall
for y0,y1 in ((88.38,90.4),(95.5,97.62)): box(FLR,-4.99,-1.98,y0,y1,4.18,4.2)
box(GLS,-4.99,-1.99,90.36,90.375,4.2,8.4); box(GLS,-4.99,-1.99,95.52,95.535,4.2,8.4)

# ---------------- 12. front fascia: thin steel plate on the outer (facade-side) face only, parallel to the original sloped underside,
#                      so the terrace steps read as one smooth slope from the street (und+0.35 .. und+0.80)
def fascia(x,y0,y1,t=0.006):
    ys_=sorted(set([y0,y1]+[u[0] for u in UND if y0<u[0]<y1]+list(np.arange(np.ceil(y0*2)/2,y1,0.5))))
    for a_,b_ in zip(ys_[:-1],ys_[1:]):
        xa=x(a_) if callable(x) else x; xb=x(b_) if callable(x) else x
        lo_a,hi_a,lo_b,hi_b=und(a_)+0.35,und(a_)+0.80,und(b_)+0.35,und(b_)+0.80
        hexa(RED,[[xa-t,a_,lo_a],[xa,a_,lo_a],[xb-t,b_,lo_b],[xb,b_,lo_b]],[[xa-t,a_,hi_a],[xa,a_,hi_a],[xb-t,b_,hi_b],[xb,b_,hi_b]])
# wings past both end walls widened to the building's front line (x -4.99), same deck build-up as the infill
for y0,y1 in ((66.1,67.58),(117.63,119.1)):
    top=lvl(y0); q=lambda z:[[XF,y0,z],[xw(y0),y0,z],[XF,y1,z],[xw(y1),y1,z]]
    hexa(FLR,q(top-0.02),q(top)); hexa(STL,q(top-0.02-PL),q(top-0.02))
    bar(STL,[XF+0.05,y0,top-0.032-EB/2],[XF+0.05,y1,top-0.032-EB/2],0.1,EB)
    for yy in (y0+0.05,(y0+y1)/2,y1-0.05): bar(STL,[XF+0.1,yy,top-0.032-JB/2],[xw(yy)-0.05,yy,top-0.032-JB/2],0.08,JB)
    put(RED,[[XF,y0,und(y0)+0.35],[xw(y0),y0,und(y0)+0.35],[XF,y0+0.006,und(y0)+0.35],[xw(y0),y0+0.006,und(y0)+0.35],
             [XF,y0,top],[xw(y0),y0,top],[XF,y0+0.006,top],[xw(y0),y0+0.006,top]] if y0<67 else
            [[XF,y1-0.006,und(y1)+0.35],[xw(y1),y1-0.006,und(y1)+0.35],[XF,y1,und(y1)+0.35],[xw(y1),y1,und(y1)+0.35],
             [XF,y1-0.006,top],[xw(y1),y1-0.006,top],[XF,y1,top],[xw(y1),y1,top]],HEX)      # end plate of the wing
fascia(XF,66.1,119.1)

# ---------------- 13. downlights under the front L2 (ribbon + infill + wings) and under the L2 bouldering slab
LIT='interior#(1.0, 0.95, 0.875)|0.5|0|0|1'
def downlight(x,y,z):
    box(BLK,x-0.11,x+0.11,y-0.11,y+0.11,z-0.03,z); box(LIT,x-0.08,x+0.08,y-0.08,y+0.08,z-0.035,z-0.03)
GRIDY=[67.75,74.65,81.55,88.45,97.45,104.05,110.65,117.25]
def clear(y): return all(abs(y-g)>0.35 for g in GRIDY) and all(abs(y-a)>0.25 for a,b,t in TER)
nl=0
for (t0,t1,top) in TER:
    n=max(1,int(round((t1-t0)/2.4))); 
    for j in range(n):
        y=t0+(t1-t0)*(j+0.5)/n
        if not clear(y): y+=0.45 if clear(y+0.45) else -0.45
        zb=top-0.02-PL-JB
        downlight((xw(y)+xe(y))/2,y,zb); nl+=1
        inside=any(a<=y<=b for a,b in INSIDE) or y<67.58 or y>117.63
        if inside: downlight((XF+xw(y))/2,y,zb); nl+=1
for x in np.arange(-0.6,12.0,2.1):
    for y in (70.3,71.9,73.4): downlight(x,y,6.0); nl+=1
print('downlights',nl)
# ---------------- 14. Edge: five treadmills facing the front glass (inside the glass line, clear of the inner column at y 104.05)
TM_D='interior#(0.025, 0.025, 0.025)|0.5|0|0|0'; TM_B='interior#(0.075, 0.075, 0.075)|0.75|0|0|0'
for i in range(4):
    cy=109.72-i*1.12; fz=floor_at(-0.2,cy,2.0); x0,x1=-1.15,0.75
    box(TM_D,x0+0.15,x1,cy-0.42,cy+0.42,fz,fz+0.2); box(TM_B,x0+0.25,x1-0.05,cy-0.25,cy+0.25,fz+0.2,fz+0.21)          # deck + belt
    for sy in (-0.38,0.38): box(TM_D,x0+0.15,x0+0.25,cy+sy-0.03,cy+sy+0.03,fz+0.2,fz+1.3)                             # uprights
    for sy in (-0.38,0.38): box(TM_D,x0+0.2,x0+0.75,cy+sy-0.02,cy+sy+0.02,fz+1.0,fz+1.04)                             # handrails
    box(TM_D,x0,x0+0.3,cy-0.36,cy+0.36,fz+1.25,fz+1.45); box(LIT,x0+0.28,x0+0.285,cy-0.2,cy+0.2,fz+1.3,fz+1.42)      # console + screen

# ---------------- 15. floating-item repair (from the audit): items resting a few cm above a surface are set down on it,
#                      items hanging in the air get a 10 mm hanger to the first surface above, the rest a short connector
import json as _j
FL=[f for f in _j.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'float_m16.json'))) if not (f[2][0]<-2.0 and f[2][1]>97.4 and f[2][1]<97.7) and not (f[2][0]>-3.25 and f[3][0]<-2.35 and f[3][2]<3.6)]
TT=[];TK=[]
for ci,ch in enumerate(C):
    if ch['inst'] is not None or len(ch['f'])==0 or ch['k'].startswith('site'): continue
    T=ch['v'][ch['f']]; TT.append(T); TK.append(np.full(len(T),ci))
for kk,parts in add.items():
    for pv,pf in parts: TT.append(pv[pf]); TK.append(np.full(len(pf),-1))
TT=np.concatenate(TT); TK=np.concatenate(TK); TMN=TT.min(1); TMX=TT.max(1)
def ray(o,dvec,ex):
    m=(TMN[:,0]<=o[0]+1e-6)&(TMX[:,0]>=o[0]-1e-6)&(TMN[:,1]<=o[1]+1e-6)&(TMX[:,1]>=o[1]-1e-6) if dvec[0]==0 and dvec[1]==0 else np.ones(len(TT),bool)
    m&=~ex; T=TT[m]
    if len(T)==0: return None
    e1=T[:,1]-T[:,0]; e2=T[:,2]-T[:,0]; p=np.cross(dvec,e2); det=(e1*p).sum(1); ok=np.abs(det)>1e-12
    inv=np.where(ok,1/np.where(ok,det,1),0); s_=o-T[:,0]; u=(s_*p).sum(1)*inv; q=np.cross(s_,e1); v=(dvec*q).sum(1)*inv; t=(e2*q).sum(1)*inv
    hit=ok&(u>=0)&(v>=0)&(u+v<=1)&(t>1e-4)
    return float(t[hit].min()) if hit.any() else None
HANG='structure#(0.1, 0.025, 0.025)|0.75|0|0|0'
nd=nh=nc=0
for L,k,mn,mx in FL:
    mn=np.array(mn); mx=np.array(mx)
    # locate the component's vertices in its chunk
    tgt=None
    for ci,ch in enumerate(C):
        if ch['k']!=k or ch['inst'] is not None: continue
        V=ch['v']; sel=np.all((V>=mn-0.002)&(V<=mx+0.002),1)
        if sel.any(): tgt=(ci,sel); break
    if tgt is None: continue
    ci,sel=tgt
    own=np.all((TMN>=mn-0.003)&(TMX<=mx+0.003),1)
    c=(mn+mx)/2
    gaps=[ray(np.array([x,y,mn[2]+0.001]),np.array([0,0,-1.0]),own) for x in (mn[0],c[0],mx[0]) for y in (mn[1],c[1],mx[1])]
    gaps=[g for g in gaps if g is not None]
    if gaps and min(gaps)<0.30:
        C[ci]['v']=C[ci]['v'].copy(); C[ci]['v'][sel,2]-=min(gaps)-0.001; nd+=1; continue
    up=ray(np.array([c[0],c[1],mx[2]-0.001]),np.array([0,0,1.0]),own)
    if up is not None and up<6.0:
        box(HANG,c[0]-0.005,c[0]+0.005,c[1]-0.005,c[1]+0.005,mx[2]-0.002,mx[2]+up); nh+=1; continue
    best=None
    for dv in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0)):
        t=ray(c,np.array(dv,float),own)
        if t is not None and (best is None or t<best[0]): best=(t,dv)
    if best and best[0]<0.6:
        t,dv=best; e=c+np.array(dv)*t
        box(HANG,min(c[0],e[0])-0.005,max(c[0],e[0])+0.005,min(c[1],e[1])-0.005,max(c[1],e[1])+0.005,c[2]-0.005,c[2]+0.005); nc+=1
print('floating fixed: set down',nd,'hangers',nh,'connectors',nc,'of',len(FL))
for kk,parts in add.items():
    v=[];f=[];o=0
    for pv,pf in parts: v.append(pv); f.append(pf+o); o+=len(pv)
    C.append(dict(k=kk,v=np.concatenate(v),f=np.concatenate(f),inst=None))
os.makedirs(OUT,exist_ok=True); geo.save(OUT,mats,C); print('saved',OUT)
