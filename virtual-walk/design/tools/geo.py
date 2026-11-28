import json,numpy as np
def load(dirp):
    d=json.load(open(dirp+'/geo.json')); buf=open(dirp+'/geo.bin','rb').read()
    out=[]
    for ch in d['chunks']:
        q=np.frombuffer(buf,np.uint16,ch['n']*3,ch['p']).reshape(-1,3).astype(np.float64)
        v=np.array(ch['mn'])+q/65535*np.array(ch['ex'])
        idx=np.frombuffer(buf,np.uint32 if ch['b'] else np.uint16,ch['c'],ch['i']).astype(np.int64).reshape(-1,3)
        inst=None
        if ch.get('t') is not None: inst=np.frombuffer(buf,np.float32,ch['tn']*3,ch['t']).reshape(-1,3).astype(np.float64)
        out.append(dict(k=ch['k'],v=v,f=idx,inst=inst))
    return d['mats'],out
def save(dirp,mats,chunks):
    buf=bytearray(); js=[]
    def pad():
        while len(buf)%4: buf.append(0)
    for c in chunks:
        v,f=c['v'],c['f']
        if len(f)==0: continue
        used=np.unique(f); remap=-np.ones(len(v),np.int64); remap[used]=np.arange(len(used)); v=v[used]; f=remap[f]
        # split if >65535 verts
        mn=v.min(0); ex=np.maximum(v.max(0)-mn,1e-5)
        q=np.round((v-mn)/ex*65535).astype(np.uint16)
        e=dict(k=c['k'],p=len(buf),n=len(v)); buf+=q.tobytes(); pad()
        b=len(v)>65535; e['i']=len(buf); e['c']=f.size; e['b']=1 if b else 0
        buf+=f.astype(np.uint32 if b else np.uint16).tobytes(); pad()
        e['mn']=[round(float(x),5) for x in mn]; e['ex']=[float(x) for x in ex]
        if c['inst'] is not None:
            e['t']=len(buf); e['tn']=len(c['inst']); buf+=c['inst'].astype(np.float32).tobytes(); pad()
        js.append(e)
    open(dirp+'/geo.bin','wb').write(buf); json.dump(dict(mats=mats,chunks=js),open(dirp+'/geo.json','w'),separators=(',',':'))
