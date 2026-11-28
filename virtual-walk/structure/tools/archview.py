# quick orthographic render of the mz19 architecture model by layer (plan / elevation) for checking
import sys,numpy as np,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
sys.path.insert(0,'../../design/tools'); import geo
M,C=geo.load('../../model')
def tris(layers=None,box=None):
    out=[];cols=[]
    for ch in C:
        if ch['inst'] is not None: continue
        L=ch['k'].split('#')[0]
        if layers and L not in layers: continue
        rgb=eval(ch['k'].split('#')[1].split('|')[0]); T=ch['v'][ch['f']]
        if box is not None:
            c=T.mean(1); s=np.all((c>=box[0])&(c<=box[1]),1); T=T[s]
        out.append(T); cols+= [rgb]*len(T)
    return np.concatenate(out),np.array(cols)
def view(ax,T,cl,axes,depth,rev=False,alpha=1):
    P=T[:,:,axes]; d=T[:,:,depth].mean(1)
    o=np.argsort(-d if rev else d); 
    pc=PolyCollection(P[o],facecolors=np.clip(cl[o]*1.6,0,1),edgecolors='none',alpha=alpha); ax.add_collection(pc); ax.autoscale(); ax.set_aspect('equal')
if __name__=='__main__':
    T,cl=tris(box=(np.array([-8,60,-1]),np.array([20,125,7.0])))
    f,ax=plt.subplots(figsize=(22,7)); view(ax,T,cl,[1,0],2); ax.set_title('plan below z 7'); f.savefig(sys.argv[1]+'/plan_lo.png',dpi=110,bbox_inches='tight')
    T,cl=tris(box=(np.array([-8,60,-1]),np.array([-1.5,125,20])))
    f,ax=plt.subplots(figsize=(22,7)); view(ax,T,cl,[1,2],0,rev=True); ax.set_title('front x<-1.5 from street'); f.savefig(sys.argv[1]+'/elev_front.png',dpi=110,bbox_inches='tight')
    T,cl=tris(box=(np.array([-8,60,-1]),np.array([20,125,20])))
    f,ax=plt.subplots(figsize=(22,7)); view(ax,T,cl,[1,2],0,rev=False); ax.set_title('from rear'); f.savefig(sys.argv[1]+'/elev_rear.png',dpi=110,bbox_inches='tight')
    T,cl=tris(box=(np.array([-8,60,-1]),np.array([20,79,20])))
    f,ax=plt.subplots(figsize=(12,9)); view(ax,T,cl,[0,2],1,rev=True); ax.set_title('section looking south y<79'); f.savefig(sys.argv[1]+'/sec_south.png',dpi=110,bbox_inches='tight')
