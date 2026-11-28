# guardrail-gap audit on walkable (reachable) surfaces: edge with a drop > 0.6 m and nothing vertical from h+0.05 to h+1.0
import geo,numpy as np,sys,collections,json
import walkgen as W
mats,C=geo.load(sys.argv[1]); F,V=W.gen(C)
NY=W.NY
def cell(x,y): return int((x-W.X0)/W.RES)*NY+int((y-W.Y0)/W.RES)
def blocked(k,h,lo,hi):
    return any(a<h+hi and b>h+lo for a,b in V.get(k,()))
seeds=[(-12,93.2,0.2),(2.9,90.4,1.0),(5.0,77.5,1.0),(8.0,108.0,1.0)]
seen=set(); Q=collections.deque()
for x,y,z in seeds:
    k=cell(x,y); hs=F.get(k,[])
    if not hs: print('no floor at seed',x,y); continue
    h=min(hs,key=lambda t:abs(t-z)); seen.add((k,h)); Q.append((k,h))
def nbrs(k):
    i,j=divmod(k,NY)
    for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
        ii,jj=i+di,j+dj
        if 0<=ii<W.NX and 0<=jj<NY: yield ii*NY+jj
while Q:
    k,h=Q.popleft()
    for n in nbrs(k):
        for h2 in F.get(n,()):
            if abs(h2-h)<=0.25 and (n,h2) not in seen and not blocked(n,h2,0.45,1.7) and not blocked(n,max(h,h2),0.5,1.6):
                seen.add((n,h2)); Q.append((n,h2))
print('reachable cells',len(seen))
gaps=[]
for k,h in seen:
    if h<0.9: continue
    for n in nbrs(k):
        hs=F.get(n,())
        if any(abs(h2-h)<=0.5 for h2 in hs): continue
        below=[h2 for h2 in hs if h2<h-0.5]
        drop=h-(max(below) if below else 0.0)
        if drop<0.6: continue
        if blocked(k,h,0.05,1.0) or blocked(n,h,0.05,1.0): continue
        gaps.append((k,h,n,round(drop,2)))
print('gap edges',len(gaps))
# cluster
cells=collections.defaultdict(set)
for k,h,n,d in gaps: cells[round(h,1)].add(k)
out=[]
for h,S in cells.items():
    S=set(S); 
    while S:
        st=[S.pop()]; grp=[]
        while st:
            c=st.pop(); grp.append(c)
            i,j=divmod(c,NY)
            for di in (-1,0,1):
                for dj in (-1,0,1):
                    m=(i+di)*NY+(j+dj)
                    if m in S: S.remove(m); st.append(m)
        if len(grp)>=3:
            ii=[g//NY for g in grp]; jj=[g%NY for g in grp]
            out.append(dict(h=h,n=len(grp),x=[round(W.X0+min(ii)*W.RES,2),round(W.X0+(max(ii)+1)*W.RES,2)],y=[round(W.Y0+min(jj)*W.RES,2),round(W.Y0+(max(jj)+1)*W.RES,2)]))
out.sort(key=lambda d:-d['n'])
json.dump(out,open('/tmp/railgaps.json','w'))
for o in out: print(o)
