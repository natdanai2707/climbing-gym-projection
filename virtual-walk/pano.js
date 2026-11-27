/* 360° render viewer for the Active Space walk. Panoramas are Cycles renders (equirectangular, 2:1), camera at eye height 1.6 m. */
(()=>{
const SPOTS=[{"id": "p01_street", "th": "หน้าอาคาร", "x": -12, "y": 93.2, "z": 0.2}, {"id": "p02_deck", "th": "ชานหน้าประตู", "x": -3.3, "y": 96.6, "z": 1.0}, {"id": "p03_lobby", "th": "โถงทางเข้า", "x": 2.9, "y": 90.4, "z": 1.0}, {"id": "p04_gates", "th": "ทางเดินห้องน้ำ · gate", "x": 9.7, "y": 91.5, "z": 1.0}, {"id": "p05_climb", "th": "โซนปีนผา", "x": 5.0, "y": 75.5, "z": 1.0}, {"id": "p06_training", "th": "มุมเทรนนิ่ง", "x": 13.2, "y": 80.5, "z": 1.0}, {"id": "p07_l2boulder", "th": "โบลเดอริ่งชั้น 2", "x": 3.0, "y": 74.0, "z": 6.3}, {"id": "p08_bridge", "th": "ทางเชื่อม co-working ชั้น 2", "x": 2.6, "y": 96.9, "z": 4.2}, {"id": "p09_cowork", "th": "Co-working ชั้น 2", "x": 8.0, "y": 89.0, "z": 4.2}, {"id": "p10_cowork_ext", "th": "ส่วนขยาย co-working", "x": 11.8, "y": 96.4, "z": 4.2}, {"id": "p11_edge", "th": "Edge · Hyrox", "x": 8.0, "y": 108.0, "z": 1.0}];
const V='?v=1';
let T=null,ren=null,scn=null,cam=null,sph=null,mat=null,cur=null,yaw=0,pitch=0,fov=75,open=false,raf=0,markers=[];
const css=document.createElement('style');css.textContent=`
#pano{position:fixed;inset:0;z-index:20;background:#0b0b0c;display:none;touch-action:none}
#pano canvas{display:block;width:100%;height:100%}
#pano .top{position:absolute;top:max(12px,env(safe-area-inset-top));left:12px;right:12px;display:flex;gap:8px;align-items:center;pointer-events:none}
#pano .top>*{pointer-events:auto}
#pano button{font:inherit;font-size:12px;letter-spacing:.04em;background:rgba(10,10,10,.78);color:#f0ede8;border:1px solid rgba(240,237,232,.35);padding:10px 14px;cursor:pointer}
#pano .ttl{font-size:13px;background:rgba(10,10,10,.6);color:#f0ede8;padding:9px 12px;border-left:2px solid #f0ede8}
#pano .chips{position:absolute;left:0;right:0;bottom:max(12px,env(safe-area-inset-bottom));display:flex;gap:6px;overflow-x:auto;padding:0 12px;scroll-snap-type:x mandatory}
#pano .chips button{flex:none;scroll-snap-align:start;font-size:11px;padding:9px 12px}
#pano .chips button.on{background:#f0ede8;color:#111}
#pano .mk{position:absolute;transform:translate(-50%,-50%);width:44px;height:44px;border-radius:50%;border:2px solid #f0ede8;background:rgba(10,10,10,.45);color:#f0ede8;font-size:10px;display:flex;align-items:center;justify-content:center;text-align:center;line-height:1.1;cursor:pointer;padding:0}
#pano .mk span{position:absolute;top:48px;white-space:nowrap;background:rgba(10,10,10,.7);padding:3px 6px;font-size:10px}
#pano .busy{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);color:#f0ede8;font-size:12px;letter-spacing:.1em;display:none}
`;document.head.appendChild(css);
const box=document.createElement('div');box.id='pano';box.innerHTML='<div class="top"><button id="panox">&larr; เดินต่อ</button><div class="ttl" id="panot"></div></div><div class="chips" id="panoc"></div><div class="busy" id="panob2">กำลังโหลดภาพ 360°</div>';
document.body.appendChild(box);
const chips=box.querySelector('#panoc');
SPOTS.forEach(s=>{const b=document.createElement('button');b.textContent=s.th;b.onclick=()=>go(s);s.btn=b;chips.appendChild(b)});
function init(){T=window.__walk.kit.THREE;ren=new T.WebGLRenderer({antialias:true});ren.setPixelRatio(Math.min(2,devicePixelRatio));ren.outputColorSpace=T.SRGBColorSpace;
 box.insertBefore(ren.domElement,box.firstChild);scn=new T.Scene();cam=new T.PerspectiveCamera(fov,1,.1,100);
 // sphere whose UVs are computed from the Blender equirect convention: image centre = +Y (north), right = +X
 const g=new T.SphereGeometry(50,96,64);const p=g.attributes.position,uv=g.attributes.uv;
 for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);const bx=x,by=-z,bz=y;const r=Math.hypot(bx,by,bz);
  let u=0.5+Math.atan2(bx,by)/(2*Math.PI);const v=0.5+Math.asin(bz/r)/Math.PI;uv.setXY(i,u,v)}
 mat=new T.MeshBasicMaterial({side:T.BackSide});sph=new T.Mesh(g,mat);scn.add(sph);
 const dn=(e)=>{const P=e.touches?e.touches[0]:e;let lx=P.clientX,ly=P.clientY,pd=e.touches&&e.touches.length==2?dist(e):0;
  const mv=(ev)=>{if(ev.touches&&ev.touches.length==2){const d=dist(ev);if(pd){fov=Math.max(35,Math.min(100,fov*pd/d))}pd=d;return}
   const Q=ev.touches?ev.touches[0]:ev;const k=fov/innerHeight*Math.PI/180;yaw+= (Q.clientX-lx)*k;pitch=Math.max(-1.45,Math.min(1.45,pitch+(Q.clientY-ly)*k));lx=Q.clientX;ly=Q.clientY;ev.preventDefault&&ev.preventDefault()};
  const up=()=>{removeEventListener('mousemove',mv);removeEventListener('touchmove',mv);removeEventListener('mouseup',up);removeEventListener('touchend',up)};
  addEventListener('mousemove',mv);addEventListener('touchmove',mv,{passive:false});addEventListener('mouseup',up);addEventListener('touchend',up)};
 const dist=(e)=>Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);
 ren.domElement.addEventListener('mousedown',dn);ren.domElement.addEventListener('touchstart',dn,{passive:true});
 ren.domElement.addEventListener('wheel',e=>{fov=Math.max(35,Math.min(100,fov+e.deltaY*.04));e.preventDefault()},{passive:false});
 box.querySelector('#panox').onclick=close;addEventListener('keydown',e=>{if(open&&e.key==='Escape')close()})}
const cache={};
function go(s){cur=s;box.querySelector('#panot').textContent='360° · '+s.th;SPOTS.forEach(q=>q.btn.classList.toggle('on',q===s));
 const busy=box.querySelector('#panob2');busy.style.display='block';
 const done=(tx)=>{busy.style.display='none';mat.map=tx;mat.needsUpdate=true;buildMarkers()};
 if(cache[s.id])return done(cache[s.id]);
 new T.TextureLoader().load('pano/'+s.id+'.jpg'+V,tx=>{tx.colorSpace=T.SRGBColorSpace;tx.anisotropy=4;cache[s.id]=tx;if(cur===s)done(tx)})}
function buildMarkers(){markers.forEach(m=>m.el.remove());markers=[];
 SPOTS.forEach(s=>{if(s===cur)return;const dx=s.x-cur.x,dy=s.y-cur.y,dz=s.z-cur.z;const d=Math.hypot(dx,dy);if(d>16||Math.abs(dz)>2.5)return;
  const el=document.createElement('button');el.className='mk';el.innerHTML='&#9679;<span>'+s.th+'</span>';el.onclick=()=>go(s);box.appendChild(el);
  markers.push({el,dir:new T.Vector3(dx,dz-1.6+0.2,-dy).normalize()})})}
function frame(){if(!open)return;raf=requestAnimationFrame(frame);const w=innerWidth,h=innerHeight;ren.setSize(w,h,false);cam.aspect=w/h;cam.fov=fov;cam.updateProjectionMatrix();
 cam.rotation.set(0,0,0);cam.rotation.order='YXZ';cam.rotation.y=yaw;cam.rotation.x=pitch;ren.render(scn,cam);
 for(const m of markers){const v=m.dir.clone().multiplyScalar(10).project(cam);const vis=v.z<1&&Math.abs(v.x)<1.1&&Math.abs(v.y)<1.1;m.el.style.display=vis?'flex':'none';
  if(vis){m.el.style.left=((v.x+1)/2*w)+'px';m.el.style.top=((1-v.y)/2*h)+'px'}}}
function nearest(){const P=window.__walk.player;const bx=P.x,by=-P.z,bz=P.y;let best=SPOTS[0],bd=1e9;
 for(const s of SPOTS){const d=Math.hypot(s.x-bx,s.y-by)+Math.abs(s.z-bz)*4;if(d<bd){bd=d;best=s}}return best}
function openPano(){if(!window.__walk)return;if(!T)init();open=true;box.style.display='block';
 const P=window.__walk.player;yaw=P.yaw||0;pitch=0;go(nearest());cancelAnimationFrame(raf);frame()}
function close(){open=false;box.style.display='none';cancelAnimationFrame(raf);
 if(cur&&window.__walk){Object.assign(window.__walk.player,{x:cur.x,z:-cur.y,y:cur.z,yaw:yaw,pitch:0});window.__walk.sim&&window.__walk.sim(2)}}
function addBtn(){const tb=document.getElementById('tb');if(!tb||document.getElementById('panob'))return;const b=document.createElement('button');b.id='panob';b.textContent='360°';b.onclick=openPano;tb.appendChild(b)}
const iv=setInterval(()=>{if(document.getElementById('tb')){addBtn();if(window.__walk)clearInterval(iv)}},300);
window.__pano={open:openPano,go:id=>go(SPOTS.find(s=>s.id===id)),set:(y,p,f)=>{yaw=y;pitch=p;if(f)fov=f}};
})();
