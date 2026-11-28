// First-person walk mode for the 3D model page + orbit-below helper
(function(){
const EYE=1.6, STEP=0.45, RAD=0.22, SPD=1.6, RUN=3.4, CELL=1;
const SPOTS=[['หน้าอาคาร',-12,93.2,0.2,-90],['โถงทางเข้า',2.9,90.4,1.0,180],['โซนปีนผา',5.0,77.5,1.0,180],
 ['บันไดขึ้นชั้น 2 แนวหน้า',0.02,72.9,1.0,0],['ชั้น 2 แนวหน้า (ฝั่งผา)',-3.0,72.0,3.4,0],['โบลเดอริ่งชั้น 2',3.0,73.6,6.3,90],
 ['ชั้น 2 แนวหน้า (ส่วนกลาง)',-1.0,93.0,4.2,180],['Co-working ชั้น 2',8.0,89.0,4.2,0],['Edge · Hyrox',8.0,108.0,1.0,0],
 ['ชั้น 2 แนวหน้า (ฝั่ง Edge)',-3.0,114.0,3.4,180]];
let W=null, fl=new Map(), cl=new Map();
const key=(i,j)=>i*100000+j;
function index(list,map){
  list.forEach((r,n)=>{const i0=Math.floor(r[0]/CELL),i1=Math.floor(r[1]/CELL),j0=Math.floor(r[2]/CELL),j1=Math.floor(r[3]/CELL);
    for(let i=i0;i<=i1;i++)for(let j=j0;j<=j1;j++){const k=key(i,j);let a=map.get(k);if(!a)map.set(k,a=[]);a.push(r)}});
}
function floorAt(x,z,top){ // highest floor <= top
  let best=-1e9;const a=fl.get(key(Math.floor(x/CELL),Math.floor(z/CELL)));
  if(a)for(const r of a){if(x>=r[0]&&x<=r[1]&&z>=r[2]&&z<=r[3]&&r[4]<=top&&r[4]>best)best=r[4]}
  return best;
}
function blocked(x,z,feet){
  const lo=feet+STEP-0.02, hi=feet+1.75;
  for(let i=Math.floor((x-RAD)/CELL);i<=Math.floor((x+RAD)/CELL);i++)for(let j=Math.floor((z-RAD)/CELL);j<=Math.floor((z+RAD)/CELL);j++){
    const a=cl.get(key(i,j));if(!a)continue;
    for(const r of a){if(x+RAD>r[0]&&x-RAD<r[1]&&z+RAD>r[2]&&z-RAD<r[3]&&r[5]>lo&&r[4]<hi)return true}
  }
  return false;
}
// ---------- UI
const css=document.createElement('style');css.textContent=`
#wbtn.on{background:#e8b04a;color:#111;border-color:#e8b04a}
#wui{position:fixed;inset:0;z-index:3;display:none;pointer-events:none}
#wui .top{position:fixed;top:10px;right:10px;display:flex;gap:4px;pointer-events:auto}
#wui select{font:inherit;font-size:13px;color:#f2f0ea;background:rgba(30,31,34,.9);border:1px solid #3a3b40;padding:6px 8px;max-width:52vw}
#wui .help{position:fixed;left:10px;bottom:10px;font-size:12px;color:#ccc;background:rgba(17,18,20,.6);padding:5px 9px}
#wui .info{position:fixed;left:50%;top:10px;transform:translateX(-50%);font-size:12px;background:rgba(17,18,20,.6);padding:4px 10px}
#joy{position:fixed;left:22px;bottom:40px;width:120px;height:120px;border-radius:50%;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.25);pointer-events:auto;display:none;touch-action:none}
#joy i{position:absolute;left:40px;top:40px;width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.45)}
#cross{position:fixed;left:50%;top:50%;width:6px;height:6px;margin:-3px;border-radius:50%;background:rgba(255,255,255,.6)}
body.walking #layers,body.walking #cutbox,body.walking #views>button:not(#wbtn){display:none}`;
document.head.appendChild(css);
const ui=document.createElement('div');ui.id='wui';ui.innerHTML=`<div class="top"><select id="wspot"></select><button id="wexit">ออกจากโหมดเดิน</button></div>
<div class="info" id="winfo"></div><div id="cross"></div><div id="joy"><i></i></div>
<div class="help" id="whelp">W A S D / ลูกศร เดิน · Shift วิ่ง · ลากเมาส์ หมุนมอง · ขึ้นลงบันไดได้</div>`;
document.body.appendChild(ui);
const sel=ui.querySelector('#wspot');sel.innerHTML='<option value="">ไปที่…</option>'+SPOTS.map((s,i)=>`<option value="${i}">${s[0]}</option>`).join('');
const touch=matchMedia('(pointer:coarse)').matches;
if(touch){ui.querySelector('#joy').style.display='block';ui.querySelector('#whelp').textContent='จอยซ้าย เดิน · ลากจอ หมุนมอง'}
let pos={x:0,z:0,feet:0},yaw=0,pitch=0,vy=0,keys={},joy={x:0,y:0},saved=null;
function spot(i){const s=SPOTS[i];pos.x=s[1];pos.z=-s[2];const f=floorAt(pos.x,pos.z,s[3]+0.3);pos.feet=f>-1e8?f:s[3];yaw=s[4]*Math.PI/180;pitch=0;vy=0}
async function enter(){
  if(!W){ui.querySelector('#winfo').textContent='กำลังโหลด…';W=await fetch('walk.json?v=mz15').then(r=>r.json());index(W.walk,fl);index(W.col,cl)}
  const V=window.V,c=V.cam;
  saved={fov:c.fov,near:c.near,pos:c.position.clone(),q:c.quaternion.clone(),cam:V.getCam(),L:{...V.L}};
  V.walking=true;document.body.classList.add('walking');ui.style.display='block';btn.classList.add('on');
  ['roof','wall','ceiling','structure','upper','climb','interior','services','outside','site','duct'].forEach(k=>{if(k in V.L&&!V.L[k])V.layer(k,true)});
  V.cutReset();c.fov=72;c.near=0.05;c.updateProjectionMatrix();c.rotation.order='YXZ';V.setCam(c);spot(0);
}
function exit(){
  const V=window.V,c=V.cam;V.walking=false;document.body.classList.remove('walking');ui.style.display='none';btn.classList.remove('on');
  for(const k in saved.L)if(V.L[k]!==saved.L[k])V.layer(k,saved.L[k]);
  c.fov=saved.fov;c.near=saved.near;c.position.copy(saved.pos);c.quaternion.copy(saved.q);c.updateProjectionMatrix();V.setCam(saved.cam);V.ctl.update();
}
sel.onchange=()=>{if(sel.value!=='')spot(+sel.value);sel.value=''};
ui.querySelector('#wexit').onclick=exit;
addEventListener('keydown',e=>{if(!window.V||!V.walking)return;keys[e.code]=true;if(e.code==='Escape')exit();if(e.code.startsWith('Arrow'))e.preventDefault()});
addEventListener('keyup',e=>{keys[e.code]=false});
// look drag (mouse + touch, excluding joystick)
const app=document.getElementById('app');let drag=null;
app.addEventListener('pointerdown',e=>{if(!V.walking)return;drag={id:e.pointerId,x:e.clientX,y:e.clientY};e.stopImmediatePropagation()},true);
addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.id)return;const k=touch?0.005:0.0035;
  yaw-=(e.clientX-drag.x)*k;pitch=Math.max(-1.45,Math.min(1.45,pitch-(e.clientY-drag.y)*k));drag.x=e.clientX;drag.y=e.clientY},true);
addEventListener('pointerup',e=>{if(drag&&e.pointerId===drag.id)drag=null},true);
app.addEventListener('wheel',e=>{if(V.walking)e.stopImmediatePropagation()},true);
const jo=ui.querySelector('#joy'),jk=jo.querySelector('i');let jid=null;
jo.addEventListener('pointerdown',e=>{jid=e.pointerId;jo.setPointerCapture(jid);jmove(e)});
jo.addEventListener('pointermove',e=>{if(e.pointerId===jid)jmove(e)});
jo.addEventListener('pointerup',()=>{jid=null;joy.x=joy.y=0;jk.style.left=jk.style.top='40px'});
function jmove(e){const r=jo.getBoundingClientRect();let dx=e.clientX-r.left-60,dy=e.clientY-r.top-60;const l=Math.hypot(dx,dy);if(l>50){dx*=50/l;dy*=50/l}
  joy.x=dx/50;joy.y=dy/50;jk.style.left=(40+dx)+'px';jk.style.top=(40+dy)+'px'}
// ---------- per frame
let last=performance.now(),autoSite=false;
function pre(){
  const V=window.V,now=performance.now(),dt=Math.min(0.05,(now-last)/1000);last=now;
  if(!V.walking){ // orbit below ground: hide the site ground so the underside reads
    const c=V.getCam(),below=c.position.y<V.ctl.target.y-0.5;
    if(below&&V.L.site){V.layer('site',false);autoSite=true}else if(!below&&autoSite){V.layer('site',true);autoSite=false}
    return;
  }
  let f=(keys.KeyW||keys.ArrowUp?1:0)-(keys.KeyS||keys.ArrowDown?1:0)-joy.y, s=(keys.KeyD?1:0)-(keys.KeyA?1:0)+joy.x;
  if(keys.ArrowLeft)yaw+=1.8*dt; if(keys.ArrowRight)yaw-=1.8*dt;
  const l=Math.hypot(f,s); if(l>1){f/=l;s/=l}
  const sp=(keys.ShiftLeft||keys.ShiftRight||Math.hypot(joy.x,joy.y)>0.95?RUN:SPD)*dt;
  const fx=-Math.sin(yaw),fz=-Math.cos(yaw),rx=Math.cos(yaw),rz=-Math.sin(yaw);
  const dx=(fx*f+rx*s)*sp,dz=(fz*f+rz*s)*sp;
  const tryMove=(nx,nz)=>{if(blocked(nx,nz,pos.feet))return false;pos.x=nx;pos.z=nz;return true};
  if(dx||dz){const n=Math.ceil(Math.hypot(dx,dz)/0.08);for(let i=0;i<n;i++){if(!tryMove(pos.x+dx/n,pos.z+dz/n)){tryMove(pos.x+dx/n,pos.z)||tryMove(pos.x,pos.z+dz/n)}}}
  const g=floorAt(pos.x,pos.z,pos.feet+STEP);
  if(g>-1e8){
    if(g>=pos.feet-0.01){pos.feet+=(g-pos.feet)*Math.min(1,dt*14);vy=0}
    else{vy-=9.8*dt;pos.feet=Math.max(g,pos.feet+vy*dt);if(pos.feet<=g+1e-3)vy=0}
  }
  const c=V.cam;c.position.set(pos.x,pos.feet+EYE,pos.z);c.rotation.set(pitch,yaw,0);
  ui.querySelector('#winfo').textContent='ระดับ +'+pos.feet.toFixed(2)+' ม.';
}
// ---------- button
let btn;
(function wait(){
  if(!window.V||!window.V.setCam){return setTimeout(wait,200)}
  window.V.pre=pre;
  window.V.wsim=(n,k,turn)=>{keys={...k};for(let i=0;i<n;i++){if(turn)yaw+=turn;last=performance.now()-33;pre()}keys={};return [pos.x.toFixed(2),(-pos.z).toFixed(2),pos.feet.toFixed(2)].join(' ')};
  btn=document.createElement('button');btn.id='wbtn';btn.textContent='โหมดเดิน';btn.onclick=()=>V.walking?exit():enter();
  document.getElementById('views').appendChild(btn);
})();
})();
