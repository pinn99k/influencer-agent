/* config.js — MVC layer (auto-split from app.js, behavior preserved)
   constants (FIELDS/AGENT_META/...) + DOM helpers h/$/clear/avatar/pill + renderMd */

// ─── Constants ──────────────────────────────────────
const FIELDS = [
  { key: '이름',       desc: '크리에이터 이름 (가명 가능)',     ph: '예: 이서연' },
  { key: '직업',       desc: '현재 직업 또는 전문 분야',        ph: '예: 미용사 수습' },
  { key: '특기',       desc: '잘하는 것 / 두드러지는 능력',     ph: '예: 헤어·네일·메이크업', long: true },
  { key: '성격',       desc: '외향/내향, 말하기 스타일 등',     ph: '예: 차분 · 설명 잘함',  long: true },
  { key: '타겟연령대', desc: '주로 어필하고 싶은 연령대',       ph: '예: 20-30대 여성' },
  { key: 'SNS경험',    desc: '현재 운영 중인 채널/계정 현황',   ph: '예: 인스타 팔로워 500명' },
  { key: '목표',       desc: '6개월~1년 내 달성하고 싶은 것',   ph: '예: 6개월 내 팔로워 3만', long: true, required: true, minLen: 10 },
];

const AGENT_META = {
  pingoo:   { name: '핑구',     initial: '핑', accent: 'oklch(66% 0.16 5)' },
  ceo:      { name: 'CEO',     initial: 'C',  accent: 'oklch(56% 0.18 295)' },
  target:   { name: '대상분석', initial: '대', accent: 'oklch(60% 0.13 35)' },
  comp:     { name: '경쟁분석', initial: '경', accent: 'oklch(60% 0.13 200)' },
  platform: { name: '플랫폼추천', initial: '플', accent: 'oklch(56% 0.12 165)' },
  concept:  { name: '컨셉기획', initial: '컨', accent: 'oklch(60% 0.13 320)' },
};

// Backend agent key → frontend key
const BACKEND_AGENT = {
  '대상분석': 'target',
  '경쟁분석': 'comp',
  '플랫폼추천': 'platform',
  '컨셉기획': 'concept',
};

// Backend event type → frontend display label
const TYPE_LABEL = {
  job_started:        '시작',
  plan_created:       '계획',
  pipeline_started:   '파이프라인',
  agent_start:        '시작',
  agent_done:         '완료',
  validation_fail:    '재시도',
  pipeline_completed: '완료',
  pipeline_failed:    '실패',
  finalize_started:   '마무리',
  briefing_pending:   '결재',
  decision_received:  '결재',
  rerun_decided:      '재분석 결정',
  judgment_fallback:  '판단 폴백',
  reanalyze_skipped:  '재분석 생략',
  job_completed:      '완료',
  job_failed:         '실패',
};

// ─── Sample data — 백엔드 미연결 시 데모 ──────────────
const SAMPLE = {
  persona: {
    '이름': '이서연', '직업': '미용사 수습',
    '특기': '헤어·네일·메이크업 3종 멀티 스킬',
    '성격': '차분 · 설명 잘함 · 카메라 어색',
    '타겟연령대': '20-30대 여성', 'SNS경험': '인스타 팔로워 300명',
    '목표': '6개월 내 인스타 팔로워 3만',
  },
  metrics: {
    followers: { v: '—', delta: '—' },
    engagement: { v: '—', delta: '—' },
    reels: { v: '—', delta: '—' },
    reach: { v: '—', delta: '—' },
  },
  reports: [],
  approvals: [],
  activity: [],
};

// ─── DOM helpers ────────────────────────────────────
function h(tag, props, ...children) {
  const el = document.createElement(tag);
  if (props) {
    for (const k in props) {
      if (k === 'class') el.className = props[k];
      else if (k === 'style' && typeof props[k] === 'object') Object.assign(el.style, props[k]);
      else if (k.startsWith('on') && typeof props[k] === 'function') el.addEventListener(k.slice(2).toLowerCase(), props[k]);
      else if (k === 'html') el.innerHTML = props[k];
      else if (props[k] != null && props[k] !== false) el.setAttribute(k, props[k]);
    }
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(c) : c);
  }
  return el;
}
function $(sel, root = document) { return root.querySelector(sel); }
function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }
function avatar(agent, size = 28) {
  const m = AGENT_META[agent] || AGENT_META.ceo;
  return h('span', { class: `avatar ${agent} size-${size}` }, m.initial);
}
function pill(text, kind = '') {
  return h('span', { class: `pill ${kind}` }, h('span', { class: 'dot' }), text);
}

// ─── Markdown ──────────────────────────────────────
function renderMd(md) {
  if (window.marked && window.DOMPurify) {
    return window.DOMPurify.sanitize(window.marked.parse(md, { gfm: true, breaks: false }));
  }
  return md.replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

