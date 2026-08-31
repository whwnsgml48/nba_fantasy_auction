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
// 🔴 40차에 여기서 당했다: 이전 회차의 /tmp/published.html 이 남아 있어서, 툴을 고치고
//    리허설을 돌렸는데 **옛 발행본이 실행됐다.** 출력은 멀쩡해 보였고 어느 파일을 읽었는지
//    화면에 없었다. 그래서 "고친 게 통과했다"고 잘못 읽었다.
//    → 항상 출처를 찍고, 발행본과 로컬이 다르면 눈에 띄게 경고한다.
const LOCAL=fs.readFileSync('tool/auction-console.html','utf8');
const localBody=LOCAL.slice(LOCAL.indexOf('<title>13캣'));
let html, srcLabel;
try {
  html=fs.readFileSync(SRC,'utf8'); srcLabel=SRC+' (발행본)';
  if(html.trim()!==localBody.trim()){
    console.log('🔴 발행본과 로컬 툴이 **다릅니다.** 지금 돌리는 것은 발행본입니다.');
    console.log('   로컬 수정을 확인하려면:  rm '+SRC+'  후 다시 실행하십시오.');
    console.log('   (발행 직전 대조 목적이면 이대로 두는 것이 맞습니다.)\n');
  }
} catch {
  html=localBody; srcLabel='tool/auction-console.html (로컬)';
  console.log('⚠ 발행본이 없어 **로컬 파일**로 돌립니다 — 발행본과 다를 수 있습니다.\n');
}
console.log('▸ 실행 대상: '+srcLabel+'\n');
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
  +';globalThis.__T={S,P,SLOTS,CORES,KATBR,DECISION,OVERHEAT,openRows,planSlack,effCeil,'
  +'renderDecide,renderCore,renderAlerts,renderPivot,renderBar,renderTrig,activeCore};\n'+raw.slice(cut));
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

// ── ⑧ 계획 슬롯 — 자격상 합법이지만 계획과 **다른 슬롯**에 넣으면 계획 여유가 틀린다 ──
//    계획 여유는 슬롯 이름으로 계획 행과 짝을 짓기 때문이다. 39차에 드롭다운이
//    계획 슬롯을 「· 계획」으로 표시하고 기본 선택하도록 고쳤다.
{
  console.log('\n════ ⑧ 계획 슬롯 짝짓기');
  for(const [core,who] of [['c3','Shai Gilgeous-Alexander'],['c2','Nikola Jokić'],
                            ['c6','Karl-Anthony Towns'],['c4','Trae Young']]){
    reset(core);
    const c=T.activeCore();
    const ps=c.plan?(c.plan.find(r=>r[2].some(x=>x[0]===who))||[])[0]:null;
    console.log('   '+core+'  '+who.padEnd(26)+' 계획 슬롯: '+ps);
  }
  for(const sl of ['SG','PG']){
    reset('c3'); buy('Shai Gilgeous-Alexander',80,sl); R();
    const k=T.planSlack();
    console.log('   c3 · SGA $80 을 '+sl+' 에 → 계획 여유 '
      +(k<0?'-$'+(-k):'$'+k)+(sl==='SG'?'  ← 계획 슬롯':'  ← 계획과 다름(드롭다운이 막는다)'));
  }
}

// ── ⑨ 미측정(null) 모양 — 「값이 있는 세계」만 밟던 것을 고친다 ──────────────
//  🔴 왜 있는가 (40차 · 2026-08-31)
//    시나리오 ①~⑧ 이 전부 **값이 채워진** 세계만 밟았다. 그래서 철수가가 `null` 인
//    감시 항목이 생겼을 때 아무도 못 잡았고, 발행본에서 이런 것들이 나왔다:
//      · JS 에서 `a > null` 은 `a > 0` 이라 **$1 낙찰만으로 철수 경보**가 떴다
//      · 계층 목록에 **`철수 >$null`** 이 그대로 찍혔다
//      · 「철수가 $null는 **발동 확률 0**」 — 재지 않은 것을 단정했다
//        (측정했는데 안 걸리는 Gobert 용 문장이 미측정 5명에게 복사됐다)
//    셋 다 데이터만 보는 validate 로는 안 잡힌다. **화면을 그려 봐야** 나온다.
//
//  일반화: 리허설이 `null`·빈 배열·필드 부재를 한 번도 안 밟으면, 다음에 누가
//  새 필드를 새 모양으로 넣을 때 똑같이 뚫린다. 아래 ⑩ 이 어떤 모양을 밟았는지 찍는다.
{
  console.log('\n════ ⑨ 철수가 미측정(null) 항목');
  const na=T.OVERHEAT.filter(o=>o.walk==null&&o.oh!=null);
  const measured=T.OVERHEAT.filter(o=>o.walk!=null);
  console.log('   미측정 '+na.length+'명: '+na.map(o=>o.n).join(' · '));
  if(!na.length){ console.log('   ⚠ 미측정 항목이 없다 — 이 시나리오가 아무것도 검사하지 않는다'); }

  // ⑨-1 계층 목록에 $null 이 찍히는가
  reset('c6'); R(); T.renderTrig();
  const t=txt(nodes['trig'].innerHTML);
  console.log('   ⑨-1 계층 목록 $null: '+(t.includes('$null')?'🔴 찍힘':'✅ 없음'));

  // ⑨-2 $1 낙찰에 철수 경보가 뜨는가  ← 실제로 깨졌던 지점
  const one=na[0];
  if(one){
    reset('c6'); sold(one.n,1); R();
    const al=txt(nodes['alerts'].innerHTML);
    const last=one.n.split(' ').pop();
    const cried=al.includes(last)&&al.includes('철수');
    console.log('   ⑨-2 '+one.n+' $1 낙찰 → 철수 경보: '+(cried?'🔴 뜬다(오경보)':'✅ 안 뜬다'));
  }

  // ⑨-3 미측정 항목에 「발동 확률 0」이 붙는가 — 그건 **측정된** 항목에만 해당한다
  reset('c6'); R(); T.renderTrig();
  const t2=txt(nodes['trig'].innerHTML);
  let bad=null;
  for(const o of na){
    const i=t2.indexOf(o.n.split(' ').pop());
    if(i>=0&&t2.slice(i,i+220).includes('발동 확률 0')) { bad=o.n; break; }
  }
  console.log('   ⑨-3 미측정 항목의 「발동 확률 0」: '+(bad?'🔴 '+bad+' 에 붙음':'✅ 없음'));
  console.log('   ⑨-4 미측정 안내 문구: '
    +(t2.includes('철수가 미측정')?'✅ 있음':'🔴 없음'));
  // 대조군 — 측정됐지만 비구속인 항목에는 그 문장이 **있어야** 한다
  const g=measured.find(o=>o.binding===false);
  if(g){
    const i=t2.indexOf(g.n.split(' ').pop());
    console.log('   ⑨-5 대조군 '+g.n+'(측정·비구속)의 「발동 확률 0」: '
      +(i>=0&&t2.slice(i,i+240).includes('발동 확률 0')?'✅ 있음':'🔴 사라졌다'));
  }
}

// ── ⑩ 어떤 모양을 밟았는가 ────────────────────────────────────────────────
//  🔴 이 리허설이 무엇을 **안** 밟았는지 사람이 볼 수 있어야 한다.
//    "검사가 통과했다"는 "무엇을 검사했는가"를 확인한 뒤에만 의미가 있다(docs/11).
{
  console.log('\n════ ⑩ 밟은 모양 (null·빈 배열·필드 부재)');
  const shapes=[
    ['OVERHEAT.walk = null',      T.OVERHEAT.some(o=>o.walk==null)],
    ['OVERHEAT.oh = null',        T.OVERHEAT.some(o=>o.oh==null)],
    ['DECISION.str 부재',          T.DECISION.some(d=>!d.str)],
    ['DECISION.snote 부재',        T.DECISION.some(d=>!d.snote)],
    ['DECISION.tier 부재',         T.DECISION.every(d=>d.tier===undefined)],
    ['KATBR.steps[].str = null',  (T.KATBR&&T.KATBR.steps||[]).some(s=>!s.str)],
    ['KATBR.steps[].br = null',   (T.KATBR&&T.KATBR.steps||[]).some(s=>!s.br)],
    ['CORES 중 plan 부재(c0)',     T.CORES.some(c=>!c.plan)],
  ];
  for(const [k,hit] of shapes) console.log('   '+(hit?'✅ 밟음  ':'⬜ 안 밟음')+'  '+k);
  console.log('   ⬜ 는 그 모양이 데이터에 **아직 없다**는 뜻이다 — 생기면 여기가 먼저 켜진다.');
}
