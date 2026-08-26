import fs from 'fs';
const html=fs.readFileSync('/tmp/published.html','utf8');
const nodes={};
const mk=id=>nodes[id]||(nodes[id]={id,_h:'',_t:'',className:'',dataset:{},style:{},
  set innerHTML(v){this._h=v}, get innerHTML(){return this._h},
  set textContent(v){this._t=v}, get textContent(){return this._t},
  appendChild(){}, addEventListener(){}, focus(){}, blur(){}, remove(){}, insertAdjacentHTML(){},
  closest:()=>null, contains:()=>false, scrollIntoView(){}, click(){},
  querySelectorAll:()=>[], querySelector:()=>null,
  parentElement:{className:''}, getBoundingClientRect:()=>({height:86})});
global.document={getElementById:mk,querySelector:s=>mk(s.replace(/^#/,'')),querySelectorAll:()=>[],
  addEventListener(){},documentElement:{style:{setProperty(){}},dataset:{}},
  body:{classList:{toggle(){}}},createElement:()=>mk('tmp')};
global.window={addEventListener(){},matchMedia:()=>({matches:false,addEventListener(){}}),
  localStorage:{getItem:()=>null,setItem(){},removeItem(){}}};
global.localStorage=global.window.localStorage;
global.addEventListener=()=>{}; global.removeEventListener=()=>{};
global.matchMedia=()=>({matches:false,addEventListener(){},addListener(){}});
global.getComputedStyle=()=>({getPropertyValue:()=>''});
global.requestAnimationFrame=f=>f(); global.innerWidth=1280; global.innerHeight=900;
global.ResizeObserver=class{observe(){}disconnect(){}};
const raw=html.match(/<script>([\s\S]*)<\/script>/)[1];
const cut=raw.lastIndexOf('})();');
fs.writeFileSync('/tmp/pub.mjs', raw.slice(0,cut)
  +';globalThis.__T={S,P,SLOTS,CORES,KATBR,DECISION,openRows,planSlack,effCeil,'
  +'renderDecide,renderCore,renderAlerts,renderPivot,renderBar,activeCore};\n'+raw.slice(cut));
await import('/tmp/pub.mjs');
const T=globalThis.__T,{S,P}=T;
const id=n=>P.findIndex(x=>x.n===n);
const reset=c=>{S.mine.length=0;S.gone.length=0;for(const k in S.actual)delete S.actual[k];S.core=c;};
const sold=(n,pr)=>{S.actual[id(n)]=pr; if(!S.gone.includes(id(n)))S.gone.push(id(n));};
const buy=(n,pr,sl)=>S.mine.push({id:id(n),price:pr,slotIdx:T.SLOTS.indexOf(sl),slot:sl});
const txt=h=>String(h).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const R=()=>{T.renderBar();T.renderDecide();T.renderCore();T.renderAlerts();T.renderPivot();};
const kat=()=>{const t=txt(nodes['decide'].innerHTML); const i=t.indexOf('KAT 가격 분기');
  return i<0?'🔴 KAT 분기 구간이 없다':t.slice(i,i+300);};
const c2row=()=>{const t=txt(nodes['decide'].innerHTML); const i=t.indexOf('조건부');
  return i<0?'🔴 c2 행 없음':t.slice(i,i+90);};
console.log('① Jokić $99 타팀 낙찰 · KAT $45');
reset('c6'); sold('Nikola Jokić',99); sold('Karl-Anthony Towns',45); R();
console.log('   c2행: '+c2row()+'\n   '+kat());
console.log('\n② 내가 Jokić $95 낙찰 (게이트 열림)');
reset('c6'); buy('Nikola Jokić',95,'C'); R();
console.log('   c2행: '+c2row());
console.log('\n③ KAT $55  · ④ KAT $62 & 내 Jokić $95  · ⑤ KAT $62 & Jokić $101 타팀');
reset('c6'); sold('Karl-Anthony Towns',55); R(); console.log('   [$55] '+kat());
reset('c6'); buy('Nikola Jokić',95,'C'); sold('Karl-Anthony Towns',62); R(); console.log('   [$62/Jokić95] '+kat());
reset('c6'); sold('Nikola Jokić',101); sold('Karl-Anthony Towns',62); R(); console.log('   [$62/Jokić101] '+kat());
const all=Object.values(nodes).map(n=>txt(n.innerHTML||n.textContent)).join(' ');
const bad=[...new Set((all.match(/\d+차(?!원|선)/g)||[]))].filter(x=>!['1차','2차'].includes(x));
console.log('\n▸ 전체 렌더 텍스트의 차수(1차·2차 지표 제외): '+(bad.length?'🔴 '+bad.join(','):'✅ 없음'));
