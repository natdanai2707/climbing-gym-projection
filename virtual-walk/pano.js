/* 360° render viewer for the Active Space walk.
   Each spot is a Cycles render as a cube map: 6 faces x 1280 px, camera at eye height 1.6 m.
   Faces px..nz use three.js axes (x = east, y = up, z = -north). */
(()=>{
const SPOTS=[{"id": "p01_street", "th": "หน้าอาคาร", "x": -12, "y": 93.2, "z": 0.2}, {"id": "p02_deck", "th": "ชานหน้าประตู", "x": -3.3, "y": 96.6, "z": 1.0}, {"id": "p03_lobby", "th": "โถงทางเข้า", "x": 2.9, "y": 90.4, "z": 1.0}, {"id": "p04_gates", "th": "ทางเดินห้องน้ำ · gate", "x": 9.7, "y": 91.5, "z": 1.0}, {"id": "p05_climb", "th": "โซนปีนผา", "x": 5.0, "y": 75.5, "z": 1.0}, {"id": "p06_training", "th": "มุมเทรนนิ่ง", "x": 13.2, "y": 80.5, "z": 1.0}, {"id": "p07_l2boulder", "th": "โบลเดอริ่งชั้น 2", "x": 3.0, "y": 74.0, "z": 6.3}, {"id": "p08_bridge", "th": "ทางเชื่อม co-working ชั้น 2", "x": 2.6, "y": 96.9, "z": 4.2}, {"id": "p09_cowork", "th": "Co-working ชั้น 2", "x": 8.0, "y": 89.0, "z": 4.2}, {"id": "p10_cowork_ext", "th": "ส่วนขยาย co-working", "x": 11.8, "y": 96.4, "z": 4.2}, {"id": "p11_edge", "th": "Edge · Hyrox", "x": 8.0, "y": 108.0, "z": 1.0}];
const V='?v=2';
const FACES={px:[[1,0,0],[0,1,0]],nx:[[-1,0,0],[0,1,0]],py:[[0,1,0],[0,0,1]],ny:[[0,-1,0],[0,0,-1]],pz:[[0,0,1],[0,1,0]],nz:[[0,0,-1],[0,1,0]]};
let T=null,ren=null,scn=null,cam=null,box=null,mats={},cur=null,yaw=0,pitch=0,fov=75,open=false,raf=0,markers=[],loadTok=0;
const css=document.createElement('style');css.textContent=`
#pano{position:fixed;inset:0;z-index:20;background:#0b0b0c;display:none;touch-action:none}
#pano canvas{display:block;width:100%;height:100%}
#pano .top{position:absolute;top:max(12px,env(safe-area-inset-top));left:12px;right:12px;display:flex;gap:8px;align-items:center;pointer-events:none}
#pano .top>*{pointer-events:auto}
#pano button{font:inherit;font-size:12px;letter-spacing:.04em;background:rgba(10,10,10,.78);color:#f0ede8;border:1px solid rgba(240,237,232,.35);padding:10px 14px;cursor:pointer}
#pano .ttl{font-size:13px;background:rgba(10,10,10,.6);color:#f0ede8;padding:9px 12px;border-left:2px solid #f0ede8}
#pano .chips{position:absolute;left:0;right:0;bottom:max(12px,env(safe-area-inset-bottom));display:flex;gap:6px;overflow-x:auto;padding:0 12px}
#pano .chips button{flex:none;font-size:11px;padding:9px 12px}
#pano .chips button.on{background:#f0ede8;color:#111}
#pano .mk{position:absolute;transform:translate(-50%,-50%);width:44px;height:44px;border-radius:50%;border:2px solid #f0ede8;background:rgba(10,10,10,.45);color:#f0ede8;font-size:10px;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
#pano .mk span{position:absolute;top:48px;white-space:nowrap;background:rgba(10,10,10,.7);padding:3px 6px;font-size:10px}
#pano .ld{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:min(320px,70vw);display:none;background:rgba(10,10,10,.72);padding:14px 16px 16px;border:1px solid rgba(240,237,232,.25)}
#pano .ld .t{display:flex;justify-content:space-between;color:#f0ede8;font-size:12px;letter-spacing:.06em;margin-bottom:10px}
#pano .ld .bar{height:4px;background:rgba(240,237,232,.18);overflow:hidden}
#pano .ld .bar i{display:block;height:100%;width:0;background:#f0ede8;transition:width .15s linear}
`;document.head.appendChild(css);
const el=document.createElement('div');el.id='pano';el.innerHTML='<div class="top"><button id="panox">&larr; เดินต่อ</button><div class="ttl" id="panot"></div></div><div class="chips" id="panoc"></div><div class="ld" id="panold"><div class="t"><span>กำลังโหลดภาพ 360°</span><span id="panopc">0%</span></div><div class="bar"><i id="panobar"></i></div></div>';
document.body.appendChild(el);
const chips=el.querySelector('#panoc'),ld=el.querySelector('#panold'),bar=el.querySelector('#panobar'),pc=el.querySelector('#panopc');
SPOTS.forEach(s=>{const b=document.createElement('button');b.textContent=s.th;b.onclick=()=>go(s);s.btn=b;chips.appendChild(b)});
function init(){T=window.__walk.kit.THREE;ren=new T.WebGLRenderer({antialias:true});ren.setPixelRatio(Math.min(2,devicePixelRatio));ren.outputColorSpace=T.SRGBColorSpace;
 el.insertBefore(ren.domElement,el.firstChild);scn=new T.Scene();cam=new T.PerspectiveCamera(fov,1,.05,10);
 box=new T.Group();scn.add(box);
 for(const f in FACES){const [F,U]=FACES[f].map(a=>new T.Vector3(...a));const R=new T.Vector3().crossVectors(F,U);
  const m=new T.MeshBasicMaterial({color:0x111111,depthWrite:false});mats[f]=m;
  const p=new T.Mesh(new T.PlaneGeometry(2,2),m);const M=new T.Matrix4().makeBasis(R,U,F.clone().negate());M.setPosition(F);p.matrixAutoUpdate=false;p.matrix.copy(M);box.add(p)}
 const dist=(e)=>Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);
 const dn=(e)=>{const P=e.touches?e.touches[0]:e;let lx=P.clientX,ly=P.clientY,pd=e.touches&&e.touches.length==2?dist(e):0;
  const mv=(ev)=>{if(ev.touches&&ev.touches.length==2){const d=dist(ev);if(pd)fov=Math.max(30,Math.min(100,fov*pd/d));pd=d;ev.preventDefault();return}
   const Q=ev.touches?ev.touches[0]:ev;const k=fov/innerHeight*Math.PI/180;yaw+=(Q.clientX-lx)*k;pitch=Math.max(-1.5,Math.min(1.5,pitch+(Q.clientY-ly)*k));lx=Q.clientX;ly=Q.clientY;ev.preventDefault&&ev.preventDefault()};
  const up=()=>{removeEventListener('mousemove',mv);removeEventListener('touchmove',mv);removeEventListener('mouseup',up);removeEventListener('touchend',up)};
  addEventListener('mousemove',mv);addEventListener('touchmove',mv,{passive:false});addEventListener('mouseup',up);addEventListener('touchend',up)};
 ren.domElement.addEventListener('mousedown',dn);ren.domElement.addEventListener('touchstart',dn,{passive:true});
 ren.domElement.addEventListener('wheel',e=>{fov=Math.max(30,Math.min(100,fov+e.deltaY*.04));e.preventDefault()},{passive:false});
 el.querySelector('#panox').onclick=close;addEventListener('keydown',e=>{if(open&&e.key==='Escape')close()})}
const cache={};
async function fetchFace(url,onp){const r=await fetch(url);const total=+r.headers.get('content-length')||0;
 if(!r.body||!r.body.getReader){const b=await r.blob();onp(b.size,b.size);return b}
 const rd=r.body.getReader();const parts=[];let got=0;for(;;){const {done,value}=await rd.read();if(done)break;parts.push(value);got+=value.length;onp(got,total)}
 return new Blob(parts,{type:'image/jpeg'})}
function setProg(p){bar.style.width=(p*100).toFixed(0)+'%';pc.textContent=Math.round(p*100)+'%'}
async function load(s){const tok=++loadTok;const keys=Object.keys(FACES);const got={},tot={};
 const upd=()=>{let g=0,t=0;for(const k of keys){const tt=tot[k]||180000;t+=tt;g+=Math.min(got[k]||0,tt)}setProg(t?g/t:0)};
 const tex=await Promise.all(keys.map(async k=>{const b=await fetchFace('pano/'+s.id+'/'+k+'.jpg'+V,(g,t)=>{got[k]=g;if(t)tot[k]=t;upd()});
  const im=new Image();const u=URL.createObjectURL(b);im.src=u;await im.decode();URL.revokeObjectURL(u);const tx=new T.Texture(im);tx.colorSpace=T.SRGBColorSpace;
  tx.anisotropy=Math.min(8,ren.capabilities.getMaxAnisotropy());tx.wrapS=tx.wrapT=T.ClampToEdgeWrapping;tx.needsUpdate=true;return [k,tx]}));
 return Object.fromEntries(tex)}
async function go(s){cur=s;el.querySelector('#panot').textContent='360° · '+s.th;SPOTS.forEach(q=>q.btn.classList.toggle('on',q===s));
 const mine=s;let tx=cache[s.id];
 if(!tx){setProg(0);ld.style.display='block';try{tx=await load(s);cache[s.id]=tx}catch(e){pc.textContent='โหลดไม่สำเร็จ';return}}
 if(cur!==mine)return;ld.style.display='none';for(const k in mats){mats[k].map=tx[k];mats[k].color.set(0xffffff);mats[k].needsUpdate=true}buildMarkers()}
function buildMarkers(){markers.forEach(m=>m.el.remove());markers=[];
 SPOTS.forEach(s=>{if(s===cur)return;const dx=s.x-cur.x,dy=s.y-cur.y,dz=s.z-cur.z;const d=Math.hypot(dx,dy);if(d>16||Math.abs(dz)>2.5)return;
  const b=document.createElement('button');b.className='mk';b.innerHTML='&#9679;<span>'+s.th+'</span>';b.onclick=()=>go(s);el.appendChild(b);
  markers.push({el:b,dir:new T.Vector3(dx,dz-1.4,-dy).normalize()})})}
function frame(){if(!open)return;raf=requestAnimationFrame(frame);const w=innerWidth,h=innerHeight;ren.setSize(w,h,false);cam.aspect=w/h;cam.fov=fov;cam.updateProjectionMatrix();
 cam.rotation.order='YXZ';cam.rotation.set(pitch,yaw,0);ren.render(scn,cam);
 for(const m of markers){const v=m.dir.clone().project(cam);const vis=v.z<1&&Math.abs(v.x)<1.1&&Math.abs(v.y)<1.1;m.el.style.display=vis?'flex':'none';
  if(vis){m.el.style.left=((v.x+1)/2*w)+'px';m.el.style.top=((1-v.y)/2*h)+'px'}}}
function nearest(){const P=window.__walk.player;const bx=P.x,by=-P.z,bz=P.y;let best=SPOTS[0],bd=1e9;
 for(const s of SPOTS){const d=Math.hypot(s.x-bx,s.y-by)+Math.abs(s.z-bz)*4;if(d<bd){bd=d;best=s}}return best}
function openPano(){if(!window.__walk)return;if(!T)init();open=true;el.style.display='block';
 const P=window.__walk.player;yaw=P.yaw||0;pitch=0;go(nearest());cancelAnimationFrame(raf);frame()}
function close(){open=false;el.style.display='none';cancelAnimationFrame(raf);
 if(cur&&window.__walk){Object.assign(window.__walk.player,{x:cur.x,z:-cur.y,y:cur.z,yaw:yaw,pitch:0});window.__walk.sim&&window.__walk.sim(2)}}
function addBtn(){const tb=document.getElementById('tb');if(!tb||document.getElementById('panob'))return;const b=document.createElement('button');b.id='panob';b.textContent='360°';b.onclick=openPano;tb.appendChild(b)}
const iv=setInterval(()=>{if(document.getElementById('tb')){addBtn();if(window.__walk)clearInterval(iv)}},300);
window.__pano={open:openPano,go:id=>go(SPOTS.find(s=>s.id===id)),set:(y,p,f)=>{yaw=y;pitch=p;if(f)fov=f}};
})();
