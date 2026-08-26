// ═══════════════════════════════════════════════════════════════════════════
//  드래프트 리허설 — 발행 아티팩트의 JS를 최소 DOM 스텁으로 실행한다
//  (39차 · 평가 세션 승인. 원래는 반대 의견이었고 결함 2건을 잡은 뒤 번복됐다)
//
//  🔴 이 파일의 조건 셋 — 지우지 말 것
//
//  ① `validate.py` · `negative_tests.py` 는 **절대 이 파일을 부르지 않는다.**
//     자동 판정 게이트가 아니다. 게이트에 넣는 순간 "스텁 자체가 틀렸는데
//     아무도 검사하지 않는다"는 원래의 반대 근거가 되살아난다.
//
//  ② **자동 실행하지 않는다.** 사람이 시나리오를 정해서 돌리고 출력을 읽는다.
//     실제로 39차에 시나리오 ②가 틀렸는데(툴이 맞았다) 사람이 출력을 읽었기
//     때문에 발견됐다 — 자동 판정이었다면 "실패"로 잘못 보고했을 것이다.
//
//  ③ **이것은 스텁이며 실제 브라우저와 동작이 다를 수 있다.**
//     여기서 통과했다고 화면이 맞다는 뜻이 **아니다.**
//     발행본을 사람이 직접 열어보는 것을 대체하지 않는다.
//
//  실행:  node tests/rehearse.mjs
//         (먼저 /tmp/published.html 에 발행본 본문을 두거나 아래 SRC 를 고칠 것)
// ═══════════════════════════════════════════════════════════════════════════

import fs from 'fs';
const SRC='/tmp/published.html';   // 발행본 본문(없으면 로컬 툴에서 추출)
let html;
try { html=fs.readFileSync(SRC,'utf8'); }
catch { const raw0=fs.readFileSync('tool/auction-console.html','utf8');
        html=raw0.slice(raw0.indexOf('<title>13캣')); 
        console.log('⚠ 발행본이 없어 **로컬 파일**로 돌립니다 — 발행본과 다를 수 있습니다.\n'); }
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

// ── ⑥ 조건부 코어가 동시에 열리는 경우 ─────────────────────────────────────
console.log('\n⑥ Jokić ≤ $97 (c2 열림) **와** SGA ≤ $85 (c3 열림) 동시 충족');
reset('c6'); buy('Nikola Jokić',95,'C'); buy('Shai Gilgeous-Alexander',80,'PG'); R();
{
  const t=txt(nodes['decide'].innerHTML);
  const rows=[...t.matchAll(/(조건부[^C]*?)?C(\d)\s*·\s*(충족|불가|미정)/g)].map(m=>'C'+m[2]+':'+m[3]);
  console.log('   행 상태: '+rows.join(' | '));
  const i2=t.indexOf('현재 권장'); console.log('   '+(i2<0?'🔴 현재 권장 없음':t.slice(i2,i2+140)));
}
// ── ⑦ 게이트가 닫힌 뒤 되살아나지 않는가 ────────────────────────────────────
console.log('\n⑦ Jokić 가 타팀에 $95 → c2 는 영구히 「불가」여야 한다');
reset('c6'); sold('Nikola Jokić',95); R();
const c2a=c2row();
sold('Karl-Anthony Towns',62); R();              // 이후 다른 입력을 넣어본다
const c2b=c2row();
buy('Donovan Clingan',12,'C'); R();
const c2c=c2row();
const st=s=>((s.match(/C2\s*·\s*(충족|불가|미정)/)||[])[1]||'?');
console.log('   직후: '+st(c2a)+' → KAT 기록 후: '+st(c2b)+' → 내가 센터 구매 후: '+st(c2c));
console.log('   '+(st(c2a)==='불가'&&st(c2b)==='불가'&&st(c2c)==='불가'
  ? '✅ 「불가」로 고정 — 되살아나지 않는다' : '🔴 게이트가 되살아났다'));

// ── c1 · c4 · c7 도 같은 흐름으로 밟는다 ────────────────────────────────────
for(const core of ['c1','c4','c7']){
  console.log('\n════ '+core.toUpperCase()+' — 계획 소진 · 상한 · 경고');
  reset(core);
  const co=T.activeCore();
  const rows0=T.openRows();
  // 앵커(첫 행)를 슬롯 상한까지, 다음 두 행을 계획가 +$6 로 산다
  rows0.slice(0,3).forEach((o,k)=>{
    const pay = k===0 ? o.ceil : o.plan+6;
    buy(o.name, pay, o.slot);
  });
  R();
  const sk=T.planSlack();
  console.log('   계획여유 '+(sk<0?'-$'+(-sk):'$'+sk)+' · 잔액 $'+ (200-S.mine.reduce((a,m)=>a+m.price,0)));
  const al=txt(nodes['alerts'].innerHTML);
  const cut=al.indexOf('깎을 후보');
  console.log('   경고: '+(cut<0?'(계획 초과 경고 없음)':al.slice(Math.max(0,cut-40),cut+150)));
  const ci=txt(nodes['coreinfo'].innerHTML);
  const badc=[...new Set((ci.match(/undefined|NaN|\[object|\d+차(?!원|선)/g)||[]))].filter(x=>!['1차','2차'].includes(x));
  console.log('   코어 카드: '+(badc.length?'🔴 '+badc.join(','):'✅ 이상 없음'));
}

// ── ⑥b 🔴 hot_bigs 는 내 보유와 무관하다 — 충족 2건이 예산을 안 깨고 도달 가능하다 ──
//    이 조합이 39차에 실제 결함을 드러냈다: 표 순서상 첫 행(c7)을 자동으로 권했는데
//    c7 은 계획여유 -$34 로 조립 불가였고, 옆의 c2 는 +$10 이었다.
{
  const block=()=>{const t=txt(nodes['decide'].innerHTML); const i=t.indexOf('현재 권장');
    const j=t.indexOf('한 줄 요약');
    return i<0?'(권장 없음)':t.slice(i, j>i?j:i+400);};
  const cases=[
    ['A 충족 2건 (저가센터 2명 과열 + 내 Jokić $95)', ()=>{
      reset('c6'); sold('Donovan Clingan',25); sold('Rudy Gobert',20); buy('Nikola Jokić',95,'C');}],
    ['B 충족 1건 (내 Jokić $95 만)', ()=>{reset('c6'); buy('Nikola Jokić',95,'C');}],
    ['C 충족 0건 (정상 시장)', ()=>{reset('c6');}],
    ['D 앵커 2개 보유(깨진 상태)', ()=>{
      reset('c6'); buy('Nikola Jokić',95,'C'); buy('Shai Gilgeous-Alexander',80,'PG');}],
  ];
  console.log('\n════ ⑥b 충족 행이 2개일 때 — 자동 선택하지 않는가');
  for(const [lbl,setup] of cases){ setup(); R();
    console.log('   ['+lbl+']\n      '+block().trim()); }
}
