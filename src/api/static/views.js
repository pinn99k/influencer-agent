/* views.js — MVC View layer (재설계 v3 · 레이아웃 A)
   View: view* render fns. Reads State, calls Actions. Views never fetch directly.
   진입 계약(main.js 가 호출): viewEntry / viewTopBar / viewDashboard /
     viewAgentDetailModal / viewBriefing / viewReport(async)
   ────────────────────────────────────────────────────────────────────── */

// ─── inline icons ───────────────────────────────────
const ICON = {
  chevL: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg>',
  chevR: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>',
  chat:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8A8.5 8.5 0 0 1 21 11.5z"/></svg>',
  clip:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l4.5 4.5L19 7"/></svg>',
  cal:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="16" rx="2.5"/><path d="M3 9h18M8 2.5v4M16 2.5v4"/></svg>',
  route: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5"/></svg>',
  bolt:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4.5 13.5H11l-1 8.5 8.5-11.5H12z"/></svg>',
  layers:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5M3 17l9 5 9-5" opacity=".55"/></svg>',
  doc:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>',
  chevD: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>',
};
function ico(name) { return h('span', { class: 'ic', html: ICON[name] || '' }); }

const CEO_STATE = {
  thinking:  { msg: '다음 액션 판단 중', pill: 'purple', label: '사고중' },
  running:   { msg: '에이전트 실행 중',  pill: 'live',   label: '실행중' },
  waiting:   { msg: '핑구 결재 대기',    pill: 'alert',  label: '대기중' },
  completed: { msg: '경영 루프 가동 중', pill: 'live',   label: '운영중' },
  failed:    { msg: '오류 발생',         pill: 'alert',  label: '실패' },
};
const FRONT_AGENT = { target: '대상분석', comp: '경쟁분석', platform: '플랫폼추천', concept: '컨셉기획' };

// ════════════════════════════════════════════════════
//  TOP BAR
// ════════════════════════════════════════════════════
function viewTopBar() {
  const p = State.persona || SAMPLE.persona;
  const s = CEO_STATE[State.ceoState] || CEO_STATE.thinking;

  return h('header', { class: 'topbar' },
    h('div', { class: 'left' },
      h('div', { class: 'brand' }, h('div', { class: 'brand-mark' }, '기'), 'AI 기획사'),
      h('span', { class: 'divider-v' }),
      h('div', { class: 'subject-chip' }, avatar('target', 20), (p['이름'] || '—') + ' · ' + (p['직업'] || '—')),
      h('span', { class: 'divider-v' }),
      h('div', { class: 'ceo-state' },
        avatar('ceo', 24),
        h('div', null, h('div', { class: 'label' }, 'CEO'), h('div', { class: 'msg' }, s.msg)),
        pill(s.label, s.pill),
        State.reanalyzeMode && h('span', { class: 'reanalyze-badge' }, '재분석')
      )
    ),
    h('div', { class: 'right' },
      h('span', { class: 'goal-mini' }, '목표 · ', h('b', null, p['목표'] || '—')),
      h('span', { class: 'divider-v' }),
      h('button', { class: 'btn subtle sm', title: '새 대상자 임명',
        onclick: () => { Actions.reset(); State.entryTab = 'interview'; State.notify(); } }, '＋ 새 대상자'),
      h('button', { class: 'btn sm', title: '기존 대상자 재분석',
        onclick: () => { Actions.reset(); State.entryTab = 'reanalyze'; State.notify(); Actions.loadSubjects(); } }, '↻ 재분석'),
      h('span', { class: 'divider-v' }),
      avatar('pingoo', 28)
    )
  );
}

// ════════════════════════════════════════════════════
//  DASHBOARD (레이아웃 A — 3분할)
// ════════════════════════════════════════════════════
function viewDashboard() {
  const collapsed = !!State.dockCollapsed;
  return h('div', { class: 'workspace' + (collapsed ? ' dock-collapsed' : '') },
    viewDock(),
    viewWorkZone(),
    viewRightRail()
  );
}

// ─── LEFT dock: CEO 대화 ↔ 매니저 정보, 접기/펼치기 ───
function viewDock() {
  const mode = State.dockMode || 'chat';

  if (State.dockCollapsed) {
    return h('aside', { class: 'dock col' },
      h('div', { class: 'rail' },
        h('button', { class: 'icon-btn', title: '패널 펼치기',
          onclick: () => { State.dockCollapsed = false; State.notify(); } }, ico('chevR')),
        h('div', { class: 'rail-div' }),
        h('button', { class: 'icon-btn' + (mode === 'chat' ? ' active' : ''), title: 'CEO 대화',
          onclick: () => { State.dockCollapsed = false; State.dockMode = 'chat'; State.notify(); } }, ico('chat')),
        h('button', { class: 'icon-btn' + (mode === 'manager' ? ' active' : ''), title: '매니저 정보',
          onclick: () => { State.dockCollapsed = false; State.dockMode = 'manager'; State.notify(); } }, ico('clip'))
      )
    );
  }

  const seg = h('span', { class: 'seg' },
    h('button', { class: mode === 'chat' ? 'active' : '',
      onclick: () => { State.dockMode = 'chat'; State.notify(); } }, ico('chat'), 'CEO 대화'),
    h('button', { class: mode === 'manager' ? 'active' : '',
      onclick: () => { State.dockMode = 'manager'; State.notify(); } }, ico('clip'), '매니저 정보')
  );

  return h('aside', { class: 'dock col' },
    h('div', { class: 'dock-head' },
      seg,
      h('button', { class: 'icon-btn', title: '패널 접기',
        onclick: () => { State.dockCollapsed = true; State.notify(); } }, ico('chevL'))
    ),
    mode === 'manager' ? viewManagerInput() : viewCeoChat()
  );
}

// CEO 완료 메시지 — 백엔드 mode(1차/재분석)와 실제 재실행 결정(rerunDecision)에서 구성.
// 하드코딩 "1차 분석" 제거: 재분석이면 어떤 에이전트를 왜 다시 했는지 반영.
function ceoCompletionMessage(mode) {
  const isReanalyze = mode === 'reanalyze' || State.reanalyzeMode;
  if (!isReanalyze) {
    return '1차 분석을 마쳤어요. 산출물을 확인하고, 매니저 탭에서 성과를 입력하면 다음 전략에 반영할게요.';
  }
  const d = State.rerunDecision;
  if (d && (d.agents || []).length) {
    const names = d.agents.map(a => (AGENT_META[a] || {}).name || a).join(' · ');
    const why = d.reason ? ' (' + d.reason + ')' : '';
    return '재분석을 마쳤어요. 전달해주신 피드백을 반영해 ' + names + '을(를) 다시 작업했어요' + why +
           '. 업데이트된 산출물과 로드맵을 확인해보세요.';
  }
  return '재분석을 마쳤어요. 전달해주신 성과·피드백을 반영해 전략을 갱신했어요. 업데이트된 산출물과 로드맵을 확인해보세요.';
}

// ─── CEO 대화 (분석 완료 후에도 상시 살아있음 · C-2) ───
function viewCeoChat() {
  const chat = h('div', { class: 'chat-scroll' });

  // 1) 인사
  chat.appendChild(h('div', { class: 'msg ceo' },
    h('span', { class: 'who' }, 'CEO'),
    h('div', { class: 'bubble' }, '제가 이 기획사의 CEO예요. 진행 상황은 언제든 여기서 물어보세요.')));

  // 2) 활동을 CEO 내레이션으로 (오래된 → 최신, 핵심 이벤트만)
  const narratable = State.activity
    .filter(it => ['plan_created', 'agent_start', 'agent_done', 'briefing_pending', 'decision_received', 'job_completed', 'job_failed'].includes(it.type))
    .slice(0, 14).reverse();
  narratable.forEach(it => {
    const meta = AGENT_META[it.agent] || AGENT_META.ceo;
    const label = TYPE_LABEL[it.type] || it.type;
    if (it.type === 'briefing_pending') {
      chat.appendChild(h('div', { class: 'bubble note' }, '결재가 필요한 결정이 생겼어요 — 우측 결재 카드를 확인해주세요'));
    } else if (it.type === 'job_completed') {
      chat.appendChild(h('div', { class: 'msg ceo' }, h('span', { class: 'who' }, 'CEO'),
        h('div', { class: 'bubble' }, ceoCompletionMessage(it.mode))));
    } else {
      chat.appendChild(h('div', { class: 'msg ceo' }, h('span', { class: 'who' }, 'CEO'),
        h('div', { class: 'bubble' }, meta.name + ' ' + label + (it.detail ? ' — ' + it.detail : ''))));
    }
  });

  // 3) 사용자/CEO 대화 (NEEDS-ACTION: 백엔드 대화 엔드포인트 연결 전 로컬 표시)
  (State.ceoChat || []).forEach(m => {
    chat.appendChild(h('div', { class: 'msg ' + m.role },
      m.role === 'ceo' && h('span', { class: 'who' }, 'CEO'),
      h('div', { class: 'bubble' }, m.text)));
  });

  setTimeout(() => { chat.scrollTop = chat.scrollHeight; }, 0);

  const input = h('textarea', { class: 'chat-input', rows: 1, placeholder: 'CEO에게 질문하거나 원하는 방향을 말해보세요…' });
  const send = () => { const v = input.value; if (!v.trim()) return; input.value = ''; Actions.sendCeoMessage(v); };
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

  // U6 — 방향이 포착되면 저장/재분석 버튼 노출 (D1: 저장 + 버튼)
  const dirBanner = State.pendingDirection ? h('div', { class: 'dir-capture' },
    h('div', { class: 'dc-body' },
      h('span', { class: 'dc-tag' }, '방향 감지'),
      h('span', { class: 'dc-text' }, State.pendingDirection)),
    h('div', { class: 'dc-actions' },
      h('button', { class: 'btn subtle sm', onclick: () => Actions.applyDirection(false) }, '저장'),
      h('button', { class: 'btn primary sm', onclick: () => Actions.applyDirection(true) }, '저장하고 재분석 →'))
  ) : null;

  return h('div', { class: 'chat' },
    chat,
    h('div', { class: 'chat-foot' },
      dirBanner,
      h('div', { class: 'chat-inputrow' }, input, h('button', { class: 'btn primary', onclick: send }, '전송')),
      h('div', { class: 'chat-note' }, '분석 결과를 바탕으로 대화해요. 원하는 방향을 말하면 전략에 반영할 수 있어요.')
    )
  );
}

// ─── P1-U4: 측정 기록 (주간 KPI + 게시물 변수 태깅) ───
let _measureOpen = false;   // view-local, 접이식

function viewMeasureInput() {
  const num = (ph, w) => h('input', { type: 'number', class: 'm-in', placeholder: ph, style: 'width:' + (w || 64) + 'px' });
  const txt = (ph, w) => h('input', { type: 'text', class: 'm-in', placeholder: ph, style: 'width:' + (w || 90) + 'px' });
  const sel = (opts) => h('select', { class: 'm-in' }, ...opts.map(o => h('option', { value: o }, o)));
  const note = h('div', { class: 'm-note' }, '');
  const say = (t, ok) => { note.textContent = t; note.style.color = ok ? 'var(--ag-platform, #2a9d6e)' : 'var(--danger, #d33)'; };

  // 주간 KPI: week / followers / conversions (나머지는 게시물 로그에서 집계 가능)
  const kWeek = num('주차', 52), kFol = num('팔로워', 76), kConv = num('전환', 56);
  const kpiRow = h('div', { class: 'm-row' },
    h('span', { class: 'm-lab' }, '주간 KPI'), kWeek, kFol, kConv,
    h('button', { class: 'btn subtle sm', onclick: async () => {
      const week = parseInt(kWeek.value, 10);
      if (!week) { say('주차를 입력하세요', false); return; }
      const ok = await Actions.recordKpi({ week, followers: parseInt(kFol.value, 10) || 0,
        conversions: parseInt(kConv.value, 10) || 0 });
      say(ok ? 'Week ' + week + ' KPI 저장됨' : '저장 실패', ok);
    } }, 'KPI 저장'));

  // 게시물 기록: 변수 태깅(주제/형식/길이/시간대) + 성과
  const cTitle = txt('제목', 130), cTopic = txt('주제(예: 컬러)', 95);
  const cFmt = sel(['릴스', '쇼츠', '캐러셀', '스토리']);
  const cLen = sel(['15초', '30초', '60초']);
  const cSlot = sel(['오전', '점심', '저녁', '밤']);
  const cViews = num('조회', 64), cLikes = num('좋아요', 60), cSaves = num('저장', 52),
        cCmts = num('댓글', 52), cWeek = num('주차', 52);
  const contentRows = h('div', null,
    h('div', { class: 'm-row' }, h('span', { class: 'm-lab' }, '게시물'), cTitle, cTopic, cFmt, cLen, cSlot),
    h('div', { class: 'm-row' }, h('span', { class: 'm-lab' }, '성과'), cViews, cLikes, cSaves, cCmts, cWeek,
      h('button', { class: 'btn subtle sm', onclick: async () => {
        if (!cTitle.value.trim()) { say('제목을 입력하세요', false); return; }
        const ok = await Actions.logContent({
          date: new Date().toISOString().slice(0, 10), title: cTitle.value.trim(),
          topic: cTopic.value.trim() || '기타', fmt: cFmt.value, length: cLen.value,
          time_slot: cSlot.value, views: parseInt(cViews.value, 10) || 0,
          likes: parseInt(cLikes.value, 10) || 0, saves: parseInt(cSaves.value, 10) || 0,
          comments: parseInt(cCmts.value, 10) || 0, week: parseInt(cWeek.value, 10) || 0,
        });
        if (ok) { cTitle.value = ''; cViews.value = ''; cLikes.value = ''; cSaves.value = ''; cCmts.value = ''; }
        say(ok ? '게시물 기록됨 (변수 태깅 포함)' : '기록 실패', ok);
      } }, '게시물 기록')));

  return h('div', { class: 'measure' + (_measureOpen ? ' open' : '') },
    h('button', { class: 'm-head', onclick: () => { _measureOpen = !_measureOpen; State.notify(); } },
      h('span', { class: 'm-t' }, '측정 기록'),
      h('span', { class: 'm-s' }, '주간 KPI · 게시물별 변수 태깅(주제/형식/길이/시간대)')),
    _measureOpen && h('div', { class: 'm-body' }, kpiRow, contentRows, note));
}

// ─── 매니저에게 줄 정보 입력 (성과/피드백 → 재분석 반영) ───
function viewManagerInput() {
  const name = State.influencerName || (State.persona && State.persona['이름']);

  const perf = h('textarea', { rows: 5,
    placeholder: '예) 1주차: 팔로워 +320, 릴스 3편, 평균 조회 1.2만\n2주차: 팔로워 +540, 저장수 급증…' });
  perf.value = State.performanceContent || '';
  perf.addEventListener('input', (e) => { State.performanceContent = e.target.value; });

  const fb = h('textarea', { rows: 4,
    placeholder: '예) 컨셉은 A로 확정. 플랫폼은 유튜브 숏폼 비중을 더 높여줘.' });
  fb.value = State.feedbackContent || '';
  fb.addEventListener('input', (e) => { State.feedbackContent = e.target.value; });

  const saveBoth = async () => {
    if (!name) return;
    if (State.performanceContent && State.performanceContent.trim()) {
      try { await API.savePerformance(name, State.performanceContent); } catch (_) {}
    }
    if (State.feedbackContent && State.feedbackContent.trim()) {
      try { await API.saveFeedback(name, State.feedbackContent); } catch (_) {}
    }
  };

  return h('div', { class: 'chat' },
    h('div', { class: 'minput' },
      h('div', { class: 'intro' }, '매니저에게 전달할 정보를 입력하세요. 다음 주간 실행 카드와 재분석 전략에 반영됩니다.'),
      h('div', { class: 'fld' },
        h('div', { class: 'lab' }, '성과 기록', h('span', { class: 'sub' }, '팔로워 · 조회수 · 게시 수')), perf),
      h('div', { class: 'fld' },
        h('div', { class: 'lab' }, '피드백 · 수정 요청', h('span', { class: 'sub' }, '방향 조정')), fb),
      viewMeasureInput()
    ),
    h('div', { class: 'chat-foot' },
      h('div', { class: 'chat-inputrow', style: 'justify-content:flex-end' },
        h('button', { class: 'btn', onclick: saveBoth }, '임시 저장'),
        h('button', { class: 'btn primary', onclick: () => Actions.deliverToManager() }, '전달하고 재분석 →')
      )
    )
  );
}

// ════════════════════════════════════════════════════
//  CENTER — 작업 현황 (실행중) / 실행 관리 (완료)
//  핸드오프 v4: ceoState==='completed' 일 때만 관리 중심 화면으로 교체.
//  그 외(thinking/running/waiting/failed) 는 기존 에이전트 타일 + 타임라인 유지.
// ════════════════════════════════════════════════════

// 관리 중심 화면의 view-local 상태 (핸드오프 8-3 — 영속 불필요, 로컬 표시)
let _planWeek = 1;          // 선택 주차 (1~4)
let _evidenceOpen = false;  // 근거 자료 접힘/펼침
const _taskDone = {};       // 'w1-0' → true. 체크리스트 로컬 표시 전용 (MVP)

// 에이전트 타일 1개 (실행중 화면 · 근거 자료에서 재사용)
function agentTile(agent, grouped) {
  const meta = AGENT_META[agent] || AGENT_META.ceo;
  const events = grouped[agent] || [];
  const hasDone = events.some(ev => ev.type === 'agent_done');
  const doneEv = events.find(ev => ev.type === 'agent_done');
  const unverified = !!(doneEv && doneEv.validated === false);
  const started = events.some(ev => ev.type === 'agent_start');
  const kind = hasDone ? 'done' : (started ? 'live' : 'done');
  const label = hasDone ? '완료' : (started ? '실행중' : '대기');
  const pct = hasDone ? 100 : (started ? 55 : 6);
  const last = events[0];
  const summary = last ? (last.detail || last.text || TYPE_LABEL[last.type] || '진행 중') : '대기 중…';
  const koreanName = FRONT_AGENT[agent];
  // Detail works off a live job id OR the influencer name (disk fallback, Fix B),
  // and stays available once analysis is complete even with no replayed events.
  const ref = State.currentJobId || State.influencerName;
  const canDetail = koreanName && ref && (hasDone || State.ceoState === 'completed');

  return h('div', { class: 'agent-tile' },
    h('div', { class: 'top' },
      avatar(agent, 28),
      h('div', { style: 'flex:1' }, h('div', { class: 'nm' }, meta.name)),
      unverified && h('span', { class: 'pill alert', title: '품질 검증을 통과하지 못한 산출물' }, h('span', { class: 'dot' }), '검증 미통과'),
      pill(label, kind)
    ),
    h('div', { class: 'state' }, summary),
    h('div', { class: 'bar' }, h('i', { style: 'width:' + pct + '%' })),
    canDetail && h('button', { class: 'detail-link',
      onclick: async () => {
        try {
          const data = await API._req('/agent-output/' + encodeURIComponent(ref) + '/' + encodeURIComponent(koreanName));
          State.agentDetail = { agent: meta.name, content: data.content || data.output || '내용 없음' };
        } catch (err) {
          State.agentDetail = { agent: meta.name, content: '# 로딩 실패\n\n' + err.message };
        }
        State.notify();
      } }, '상세 보기 →')
  );
}

function viewWorkZone() {
  if (State.ceoState === 'completed') return viewManageCenter();
  return viewProgressZone();
}

// Fix E — CEO 재분석 결정 배너 + 교정 루프 진입.
// 재분석 시 'rerun_decided' 이벤트로 채워지며, 어떤 에이전트를 왜 다시 하는지 보여주고
// '교정하고 다시' 로 매니저 입력(피드백 수정 → 재전달) 루프를 연다.
function viewRerunBanner() {
  const d = State.rerunDecision;
  if (!d) return null;
  const names = (d.agents || []).map(a => (AGENT_META[a] || {}).name || a);
  const target = names.length ? names.join(' · ') : '재실행 대상 없음';
  return h('div', { class: 'rerun-banner' },
    h('div', { class: 'rb-main' },
      h('span', { class: 'rb-tag' }, 'CEO 재분석 결정'),
      h('div', { class: 'rb-body' },
        h('div', { class: 'rb-agents' }, '재실행: ' + target),
        h('div', { class: 'rb-reason' }, d.reason || '사유 미상'))),
    h('button', { class: 'btn subtle sm', onclick: () => {
      State.dockMode = 'manager'; State.dockCollapsed = false; State.notify();
    } }, '교정하고 다시 →'));
}

// ─── 실행중/사고중/대기/실패 — 기존 작업 현황 (유지) ───
function viewProgressZone() {
  const connected = State.currentJobId && State.ceoState !== 'completed' && State.ceoState !== 'failed';

  const grouped = {};
  State.activity.forEach(it => { (grouped[it.agent] = grouped[it.agent] || []).push(it); });

  const baseAgents = ['target', 'comp', 'platform', 'concept'];
  const agentKeys = baseAgents.concat(Object.keys(grouped).filter(k => !baseAgents.includes(k) && k !== 'ceo'));
  const tiles = agentKeys.map(agent => agentTile(agent, grouped));

  const tl = State.activity.slice(0, 16).map(it => {
    const meta = AGENT_META[it.agent] || AGENT_META.ceo;
    return h('div', { class: 'tl-item ag-' + it.agent },
      h('div', { class: 't' }, (it.t || '').slice(0, 5)),
      h('div', { class: 'tbody' },
        h('span', { class: 'ag' }, meta.name),
        h('span', { class: 'tag' }, TYPE_LABEL[it.type] || it.type),
        h('div', { class: 'tx' }, it.text || ''),
        it.detail && h('div', { class: 'tx-detail' }, it.detail)
      )
    );
  });
  const tlContent = tl.length > 0 ? tl
    : [h('div', { style: 'padding:24px 18px;text-align:center;color:var(--fg-muted);font-size:12.5px' }, 'CEO가 에이전트를 실행하면 활동이 여기에 표시됩니다')];

  // plan 은 아직 null — 분석이 끝나면 관리 화면으로 바뀐다는 안내 (핸드오프 §2 running)
  const ph = h('div', { class: 'plan-hint' },
    h('span', { class: 'ph-ic', html: ICON.cal }),
    h('div', null,
      h('div', { class: 'ph-t' }, '분석이 끝나면 이번 주 할 일이 여기에 표시됩니다'),
      h('div', { class: 'ph-s' }, 'CEO가 4인의 분석을 종합해 4주 로드맵과 다음 액션을 만들어요.')));

  return h('section', { class: 'workzone col' },
    viewRerunBanner(),
    h('div', { class: 'zone-head' },
      h('span', { class: 'zone-title' }, '작업 현황', h('span', { class: 'sub' }, '에이전트 4인 · 실시간')),
      pill(connected ? '연결됨' : '대기', connected ? 'live' : 'done')
    ),
    h('div', { class: 'agent-row' }, ...tiles),
    h('div', { class: 'progress-scroll' },
      ph,
      h('div', { class: 'zone-head', style: 'padding:14px 0 6px' }, h('span', { class: 'eyebrow' }, '실시간 활동')),
      h('div', { class: 'timeline flush' }, ...tlContent)
    )
  );
}

// ════════════════════════════════════════════════════
//  관리 중심 화면 (ceoState === 'completed') — 핸드오프 v4
//  우선순위: 이번 주 할 일 → 4주 로드맵 → 다음 액션 → 전략 브리핑 → 근거 자료
// ════════════════════════════════════════════════════
function mgmtHead(icon, title, sub, right) {
  return h('div', { class: 'mgmt-head' },
    h('span', { class: 'mh-ic', html: ICON[icon] || '' }),
    h('div', { style: 'flex:1;min-width:0' },
      h('div', { class: 'mh-t' }, title),
      sub && h('div', { class: 'mh-s' }, sub)),
    right || null);
}

function viewManageCenter() {
  const plan = State.plan;  // N-1: 항상 null 체크
  const body = h('div', { class: 'mgmt-scroll' });

  if (!plan) {
    body.appendChild(h('div', { class: 'card mgmt-card' },
      mgmtHead('cal', '이번 주 할 일'),
      h('div', { class: 'mgmt-empty' }, '전략 계획을 준비하고 있어요. 잠시 후 이번 주 할 일과 4주 로드맵이 여기에 표시됩니다.')));
  } else {
    const kpi = viewKpiStrip(plan);
    if (kpi) body.appendChild(kpi);
    body.appendChild(viewWeekChecklist(plan));
    body.appendChild(viewRoadmap(plan));
    const na = viewNextActions(plan);
    if (na) body.appendChild(na);
  }

  body.appendChild(viewBriefingCta());
  body.appendChild(viewEvidence());

  return h('section', { class: 'workzone col' },
    viewRerunBanner(),
    h('div', { class: 'zone-head' },
      h('span', { class: 'zone-title' }, '실행 관리', h('span', { class: 'sub' }, '이번 주 · 로드맵 · 다음 액션')),
      pill('운영 중', 'live')
    ),
    body
  );
}

// 30일 목표 지표 (KPI) — 작은 지표 스트립
function viewKpiStrip(plan) {
  const kpi = plan.kpi || [];           // N-1: 0개 가능
  if (!kpi.length) return null;
  return h('div', { class: 'kpi-strip' }, ...kpi.map(raw => {
    const parts = String(raw).split(/[:：]/);
    const hasLabel = parts.length > 1;
    const label = hasLabel ? parts[0].trim() : '목표';
    const val = hasLabel ? parts.slice(1).join(':').trim() : raw;
    return h('div', { class: 'kpi' },
      h('span', { class: 'k' }, label),
      h('span', { class: 'v' }, val));
  }));
}

// 이번 주 할 일 — 주차 탭 + 체크리스트
function taskRow(weekNum, idx, text) {
  const key = 'w' + weekNum + '-' + idx;
  const done = !!_taskDone[key];
  const box = h('span', { class: 'cbox', html: done ? ICON.check : '' });
  const row = h('div', { class: 'task' + (done ? ' done' : ''), tabindex: 0, role: 'button' },
    box, h('span', { class: 'tx' }, text));
  const toggle = () => {
    _taskDone[key] = !_taskDone[key];
    const now = !!_taskDone[key];
    row.classList.toggle('done', now);
    box.innerHTML = now ? ICON.check : '';
  };
  row.addEventListener('click', toggle);
  row.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
  return row;
}

function viewWeekChecklist(plan) {
  const weeks = plan.weeks || [];      // 항상 4개 (빈 items 포함)
  const cur = weeks.find(w => w.num === _planWeek) || weeks[0] || { num: 1, items: [] };
  const items = cur.items || [];

  const tabs = h('div', { class: 'wk-tabs' }, ...[1, 2, 3, 4].map(n => {
    const w = weeks.find(x => x.num === n);
    const cnt = w && w.items ? w.items.length : 0;
    return h('button', { class: 'wk-tab' + (n === _planWeek ? ' active' : ''),
      onclick: () => { _planWeek = n; State.notify(); } },
      'Week ' + n,
      h('span', { class: 'cnt' }, cnt ? String(cnt) : '·'));
  }));

  const doneCount = items.reduce((a, _, i) => a + (_taskDone['w' + cur.num + '-' + i] ? 1 : 0), 0);

  const list = items.length
    ? h('div', { class: 'task-list' }, ...items.map((t, i) => taskRow(cur.num, i, t)))
    : h('div', { class: 'mgmt-empty soft' },        // N-2: 빈 주차
        h('span', { class: 'pill done', style: 'margin-bottom:8px' }, h('span', { class: 'dot' }), '콘텐츠 미정'),
        h('div', null, 'Week ' + cur.num + ' 콘텐츠가 아직 정해지지 않았어요. CEO에게 이 주차 계획을 요청해보세요.'));

  return h('div', { class: 'card mgmt-card week-card' },
    mgmtHead('cal', '이번 주 할 일', 'Week ' + cur.num + ' · 촬영/게시할 콘텐츠',
      items.length ? h('span', { class: 'wk-count mono' }, doneCount + '/' + items.length) : null),
    tabs,
    list);
}

// 4주 로드맵 — 스텝퍼 + 진행률
function viewRoadmap(plan) {
  const weeks = plan.weeks || [];
  const pct = (_planWeek / 4) * 100;
  const steps = [1, 2, 3, 4].map(n => {
    const w = weeks.find(x => x.num === n) || { num: n, items: [] };
    const cnt = (w.items || []).length;
    const active = n <= _planWeek;
    const isCur = n === _planWeek;
    return h('button', { class: 'step' + (active ? ' active' : '') + (isCur ? ' current' : ''),
      onclick: () => { _planWeek = n; State.notify(); } },
      h('span', { class: 'sdot' }),
      h('span', { class: 'swk' }, 'Week ' + n),
      h('span', { class: 'smeta' }, cnt ? cnt + '개' : '미정'));
  });
  return h('div', { class: 'card mgmt-card' },
    mgmtHead('route', '4주 로드맵', '선택한 주차까지 진행'),
    h('div', { class: 'rm-track' }, h('i', { style: 'width:' + pct + '%' })),
    h('div', { class: 'stepper' }, ...steps));
}

// 다음 액션 — 지금 당장 할 일 (강조)
function viewNextActions(plan) {
  const acts = plan.next_actions || [];  // N-1: 0~3개
  if (!acts.length) return null;
  return h('div', { class: 'card mgmt-card next-card' },
    mgmtHead('bolt', '지금 당장 할 일', '오늘~3일 내 실행'),
    h('div', { class: 'act-list' }, ...acts.map((a, i) =>
      h('div', { class: 'act' },
        h('span', { class: 'idx' }, String(i + 1)),
        h('span', { class: 'tx' }, a)))));
}

// 전략 브리핑 진입 — 최종리포트.md (핸드오프 8-2)
function viewBriefingCta() {
  const reports = State.reports || [];
  const finalR = reports.find(r => /최종/.test(r.id || '') || /최종/.test(r.title || '')) || reports[0];
  const disabled = !finalR;   // reports 비면 disabled
  return h('div', {
    class: 'briefing-cta' + (disabled ? ' disabled' : ''),
    onclick: disabled ? null : () => Router.go('report', finalR.id)
  },
    h('span', { class: 'bc-ic', html: ICON.doc }),
    h('div', { style: 'flex:1;min-width:0' },
      h('div', { class: 'bc-t' }, '전략 브리핑'),
      h('div', { class: 'bc-s' }, disabled
        ? '분석이 완료되면 CEO 종합 보고서가 열립니다'
        : 'CEO 종합 보고서 — 핵심 결정 · 4주 로드맵 · 성공 지표')),
    disabled ? h('span', { class: 'pill done' }, h('span', { class: 'dot' }), '대기') : h('span', { class: 'bc-go' }, '열기 →'));
}

// 근거 자료 — 분석 4종 (접이식, 1순위 자리 양보)
function viewEvidence() {
  const grouped = {};
  State.activity.forEach(it => { (grouped[it.agent] = grouped[it.agent] || []).push(it); });
  const baseAgents = ['target', 'comp', 'platform', 'concept'];

  return h('div', { class: 'evidence' + (_evidenceOpen ? ' open' : '') },
    h('button', { class: 'ev-head',
      onclick: () => { _evidenceOpen = !_evidenceOpen; State.notify(); } },
      h('span', { class: 'ev-ic', html: ICON.layers }),
      h('div', { style: 'flex:1;text-align:left;min-width:0' },
        h('div', { class: 'ev-t' }, '근거 자료'),
        h('div', { class: 'ev-s' }, '대상 · 경쟁 · 플랫폼 · 컨셉 분석 4종 — 전략의 근거')),
      h('span', { class: 'ev-chev', html: ICON.chevD })),
    _evidenceOpen && h('div', { class: 'ev-grid' }, ...baseAgents.map(a => agentTile(a, grouped))));
}

// ════════════════════════════════════════════════════
//  RIGHT rail — 결재 · 산출물 · 매니저 알림
// ════════════════════════════════════════════════════
function viewRightRail() {
  return h('aside', { class: 'rail-right' },
    viewApprovals(),
    viewDeliverables(),
    viewManagerPanel()
  );
}

function viewApprovals() {
  if (State.approvals.length === 0) {
    return h('div', null,
      h('div', { class: 'sec-h' }, h('span', { class: 't' }, '결재 대기'), pill('클린', 'done')),
      h('div', { class: 'empty' }, h('div', { class: 't' }, '결재 대기 없음'), h('div', { class: 's' }, 'CEO가 자율 루프를 돌고 있어요.'))
    );
  }
  return h('div', null,
    h('div', { class: 'sec-h' }, h('span', { class: 't' }, '결재 대기'), pill(State.approvals.length + '건', 'alert')),
    ...State.approvals.map(p =>
      h('div', { class: 'approval' },
        h('div', { class: 'head' },
          pill('조건 ' + p.condition + '번', 'alert'),
          h('span', { class: 'mono', style: 'font-size:10.5px;color:var(--fg-muted)' }, p.age)),
        h('div', { class: 'title' }, p.title),
        h('div', { class: 'summary' }, p.summary),
        h('button', { class: 'btn primary sm', style: 'width:100%;margin-top:2px',
          onclick: () => Router.go('briefing', p.id || p.job_id) }, '보고서 열기 →')
      )
    )
  );
}

function viewDeliverables() {
  const head = h('div', { class: 'sec-h' },
    h('span', { class: 't' }, '산출물'),
    State.reports.length > 0
      ? h('button', { class: 'btn subtle sm', onclick: () => Router.go('report', State.reports[0].id) }, '전체 보기 ↗')
      : h('span', { class: 'meta' }, '0개')
  );
  if (State.reports.length === 0) {
    return h('div', null, head,
      h('div', { class: 'empty' }, h('div', { class: 't' }, '산출물 없음'), h('div', { class: 's' }, 'CEO가 에이전트를 실행하면 여기에 나타납니다.')));
  }
  return h('div', null, head,
    h('div', { class: 'card deliv-list' },
      ...State.reports.map(r => {
        const meta = AGENT_META[r.agent] || AGENT_META.ceo;
        return h('div', { class: 'row', onclick: () => Router.go('report', r.id) },
          h('span', { class: 'tag-agent', style: { background: 'var(--ag-' + r.agent + '-bg, var(--primary-soft))', color: 'var(--ag-' + r.agent + ', var(--primary))' } },
            h('span', { class: 'ic', style: { background: 'var(--ag-' + r.agent + ', var(--primary))' } }, meta.initial),
            meta.name),
          h('span', { class: 'ttl', style: 'font-size:13px;font-weight:550' }, r.title),
          h('span', { class: 'mono', style: 'font-size:10.5px;color:var(--fg-muted)' }, r.at)
        );
      })
    )
  );
}

// ─── 매니저 알림 ───
const MANAGER_KIND = {
  weekly_card: '주간 실행 카드', progress: '진행 보고',
  performance_request: '성과 입력 요청', completion: '완료 요약', info: '알림',
};
function viewManagerPanel() {
  const notes = State.managerNotes || [];
  const head = h('div', { class: 'sec-h' },
    h('span', { class: 't' }, '매니저 알림'), pill(notes.length + '건', 'purple'));
  if (notes.length === 0) {
    return h('div', null, head,
      h('div', { class: 'empty-note' }, '아직 매니저 알림이 없습니다. 분석이 완료되면 주간 카드와 성과 요청이 도착합니다.'));
  }
  return h('div', null, head,
    h('div', { class: 'note-list' },
      ...notes.slice(0, 8).map(n =>
        h('div', { class: 'note-item kind-' + n.kind },
          h('div', { class: 'note-head' },
            h('span', { class: 'note-kind' }, MANAGER_KIND[n.kind] || n.kind),
            h('span', { class: 'note-time mono' }, n.t)),
          h('div', { class: 'note-body', html: renderMd(n.content || '') }))))
  );
}

// ════════════════════════════════════════════════════
//  AGENT DETAIL modal
// ════════════════════════════════════════════════════
function viewAgentDetailModal() {
  if (!State.agentDetail) return null;
  const { agent, content } = State.agentDetail;
  const close = () => { State.agentDetail = null; State.notify(); };
  return h('div', { class: 'agent-detail-overlay', onclick: (e) => { if (e.target.classList.contains('agent-detail-overlay')) close(); } },
    h('div', { class: 'agent-detail-modal' },
      h('button', { class: 'close-btn', onclick: close, html: ICON.close }),
      h('h2', null, agent + ' 상세 결과'),
      h('div', { class: 'md-content', html: renderMd(content) })
    )
  );
}

// ════════════════════════════════════════════════════
//  BRIEFING modal
// ════════════════════════════════════════════════════
function viewBriefing(briefingId) {
  const b = State.approvals.find(x => x.id === briefingId || x.job_id === briefingId) || State.approvals[0];
  if (!b) return null;

  const submit = (choice) => {
    const jobId = b.job_id || State.currentJobId;
    API.decision(jobId, choice, '').catch(err => console.warn('/decision failed:', err.message));
    State.approvals = State.approvals.filter(x => x !== b);
    State.ceoState = 'running';
    State.notify();
    Router.go('dashboard');
  };

  return h('div', { class: 'briefing-overlay' },
    h('div', { class: 'briefing' },
      h('div', { class: 'head' },
        h('div', { style: 'margin-bottom:8px' }, pill('회장 보고 · 조건 ' + b.condition + '번', 'alert')),
        h('h2', null, b.title)
      ),
      h('div', { class: 'summary' }, b.summary),
      h('div', { class: 'opts' },
        ['A', 'B'].map(k => {
          const o = k === 'A' ? b.optionA : b.optionB;
          return h('div', { class: 'opt' + (b.rec === k ? ' rec' : '') },
            h('div', { style: 'display:flex;align-items:center;gap:8px;margin-bottom:10px' },
              h('span', { style: 'width:24px;height:24px;border-radius:6px;background:' + (b.rec === k ? 'var(--primary)' : 'var(--bg-sunken)') + ';color:' + (b.rec === k ? '#fff' : 'var(--fg-secondary)') + ';display:inline-flex;align-items:center;justify-content:center;font-weight:700' }, k),
              h('span', { style: 'font-weight:700;font-size:14px' }, o.label),
              b.rec === k && h('span', { style: 'margin-left:auto;font-size:10px;color:#fff;background:var(--primary);padding:2px 8px;border-radius:999px;font-weight:600' }, 'CEO 권고')
            ),
            h('div', { style: 'font-size:12.5px;color:var(--fg-secondary);line-height:1.55' }, o.detail)
          );
        })
      ),
      h('div', { class: 'foot' },
        h('div', { style: 'font-size:11.5px;color:var(--fg-muted)' }, 'A / B 키로 선택'),
        h('div', { style: 'display:flex;gap:8px' },
          h('button', { class: 'btn', onclick: () => submit('B') }, 'B · ' + b.optionB.label),
          h('button', { class: 'btn primary', onclick: () => submit('A') }, 'A · ' + b.optionA.label)
        )
      )
    )
  );
}

// ════════════════════════════════════════════════════
//  REPORT viewer (산출물 별도 창 — 토글 오버레이)
// ════════════════════════════════════════════════════
const MD_CACHE = {};
function _mdKey(name, file) { return (name || '') + '|' + file; }
function clearMdCache() { for (const k in MD_CACHE) delete MD_CACHE[k]; }
async function viewReport(reportId) {
  const view = h('div', { class: 'report-view' });
  const active = reportId || (State.reports[0] && State.reports[0].id);
  if (!active) {
    view.appendChild(h('div', { style: 'padding:40px;text-align:center;color:var(--fg-muted)' }, '산출물이 없습니다.'));
    return view;
  }
  const r = State.reports.find(x => x.id === active) || State.reports[0];

  view.appendChild(h('div', { class: 'breadcrumb' },
    h('div', null,
      h('button', { class: 'btn subtle sm', onclick: () => Router.go('dashboard') }, '← 대시보드'),
      h('span', { style: 'color:var(--fg-muted)' }, '/'),
      h('span', null, '산출물'),
      h('span', { style: 'color:var(--fg-muted)' }, '/'),
      h('span', { style: 'color:var(--fg);font-weight:600' }, r.title)
    ),
    h('button', { class: 'icon-btn', title: '닫기', onclick: () => Router.go('dashboard'), html: ICON.close })
  ));

  const body = h('div', { class: 'body' });
  body.appendChild(h('aside', { class: 'side' },
    h('div', { class: 'eyebrow', style: 'padding:4px 11px 8px' }, '산출물 ' + State.reports.length + '종'),
    ...State.reports.map(rr =>
      h('div', { class: 'side-item' + (rr.id === active ? ' active' : ''), onclick: () => Router.go('report', rr.id) }, rr.title))
  ));

  const mdWrap = h('div', { class: 'md-wrap' }, h('div', { class: 'md-body' }, '로딩 중...'));
  body.appendChild(mdWrap);

  body.appendChild(h('aside', { class: 'toc' },
    h('div', { class: 'eyebrow', style: 'margin-bottom:12px' }, '메타'),
    h('div', { style: 'display:flex;flex-direction:column;gap:8px;font-size:12px;color:var(--fg-secondary)' },
      h('div', null, h('span', { style: 'color:var(--fg-muted)' }, '에이전트 · '), AGENT_META[r.agent]?.name || r.agent),
      h('div', null, h('span', { style: 'color:var(--fg-muted)' }, '갱신 · '), r.at)
    )
  ));
  view.appendChild(body);

  const name = State.influencerName;
  const cacheKey = _mdKey(name, active);
  if (name && !MD_CACHE[cacheKey]) {
    try {
      const data = await API.getReport(name, active);
      MD_CACHE[cacheKey] = data.content || data;
    } catch (_) {
      MD_CACHE[cacheKey] = '# 로딩 실패\n\n백엔드에서 산출물을 가져올 수 없습니다.';
    }
  }
  const md = MD_CACHE[cacheKey] || '# 데모 모드\n\n백엔드 미연결.';
  $('.md-body', mdWrap).innerHTML = renderMd(md);
  return view;
}

// ════════════════════════════════════════════════════
//  ENTRY (최초 임명 — 대화형 인터뷰 / 재분석)
// ════════════════════════════════════════════════════
function viewEntry() {
  const root = h('div', { class: 'entry-root' });

  root.appendChild(h('header', { class: 'topbar' },
    h('div', { class: 'left' },
      h('div', { class: 'brand' }, h('div', { class: 'brand-mark' }, '기'), 'AI 기획사'),
      h('span', { class: 'divider-v' }),
      h('span', { class: 'mono', style: 'font-size:11.5px;color:var(--fg-muted)' }, State.entryTab === 'reanalyze' ? '기존 대상자' : 'CEO 최초 임명')
    ),
    h('div', { class: 'right' },
      h('span', { style: 'font-size:11.5px;color:var(--fg-muted)' }, '회장'),
      avatar('pingoo', 28)
    )
  ));

  const tabStyle = (active) => 'padding:12px 16px;font-size:13px;font-weight:' + (active ? '650' : '550') + ';border-bottom:2px solid ' + (active ? 'var(--primary)' : 'transparent') + ';color:' + (active ? 'var(--primary)' : 'var(--fg-muted)');
  root.appendChild(h('div', { style: 'display:flex;border-bottom:1px solid var(--border);padding:0 32px;background:var(--bg-surface);flex-shrink:0' },
    h('button', { style: tabStyle(State.entryTab !== 'reanalyze'),
      onclick: () => { State.entryTab = 'interview'; State.notify(); } }, '새 대상자 (대화)'),
    h('button', { style: tabStyle(State.entryTab === 'reanalyze'),
      onclick: () => { State.entryTab = 'reanalyze'; Actions.loadSubjects(); State.notify(); } }, '기존 대상자')
  ));

  root.appendChild(State.entryTab === 'reanalyze' ? viewReanalyzeEntry() : viewInterview());
  return root;
}

// ─── Interview ───
function viewInterview() {
  if (!State.interview) {
    return h('div', { class: 'interview-launch' },
      h('div', { class: 'interview-launch-card' },
        pill('대화형 상담', 'purple'),
        h('h1', null, 'CEO와 ', h('span', { style: 'color:var(--primary)' }, '대화'), '로 시작하세요'),
        h('p', null, 'CEO가 질문을 던지며 자연스럽게 정보를 모읍니다. 충분히 파악되면 바로 분석을 시작합니다.'),
        h('button', { class: 'btn primary', style: 'margin-top:4px', onclick: () => Actions.startInterview() }, 'CEO와 대화 시작하기 →')
      )
    );
  }
  const iv = State.interview;
  const chat = h('div', { class: 'chat-scroll' });
  iv.messages.forEach(m => {
    chat.appendChild(h('div', { class: 'chat-msg ' + m.role },
      m.role === 'ceo' && h('span', { class: 'chat-who' }, 'CEO'),
      h('div', { class: 'bubble' }, m.text)));
  });
  if (iv.pending) {
    chat.appendChild(h('div', { class: 'chat-msg ceo' },
      h('span', { class: 'chat-who' }, 'CEO'), h('div', { class: 'bubble typing' }, '•••')));
  }
  setTimeout(() => { chat.scrollTop = chat.scrollHeight; }, 0);

  const input = h('textarea', { rows: 1, class: 'chat-input', placeholder: '답변을 입력하고 Enter (줄바꿈 Shift+Enter)' });
  const send = () => { const v = input.value; if (!v.trim()) return; input.value = ''; Actions.sendInterview(v); };
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

  const confirmBar = iv.canSubmit
    ? h('div', { class: 'confirm-bar', style: 'flex-direction:column;align-items:stretch;gap:9px' },
        h('span', null, '필요한 정보가 모였어요. 이대로 분석을 시작할까요?'),
        h('label', { class: 'mode-toggle', style: 'display:flex;align-items:center;gap:7px;font-size:12px;font-weight:500;color:var(--fg-muted);cursor:pointer' },
          h('input', { type: 'checkbox', style: 'flex-shrink:0', checked: State.runMode === 'autonomous',
            onchange: (e) => { State.runMode = e.target.checked ? 'autonomous' : 'linear'; State.notify(); } }),
          h('span', null, '자율 모드 — CEO가 도구를 스스로 호출 (2장 도구 루프)')),
        h('button', { class: 'btn primary sm', onclick: () => Actions.confirmInterview(), disabled: iv.pending }, '확정하고 분석 시작 →'))
    : h('div', { class: 'confirm-bar muted' },
        h('span', null, '대화를 이어가 주세요. 성함과 핵심 정보가 모이면 분석을 시작할 수 있어요.'));

  const fields = ['이름', '직업', '특기', '성격', '타겟연령대', 'SNS경험', '목표'];
  const side = h('aside', { class: 'extract-panel' },
    h('div', { class: 'extract-title' }, '수집된 정보 ',
      h('span', { class: 'mono', style: 'color:var(--fg-muted);font-size:11px;font-weight:400' }, '· ' + iv.turn + '턴')),
    ...fields.map(f => {
      const v = iv.extracted[f];
      const filled = v && v !== '정보 없음';
      return h('div', { class: 'extract-row' }, h('span', { class: 'k' }, f), h('span', { class: 'v' + (filled ? ' filled' : '') }, filled ? v : '—'));
    }));

  return h('div', { class: 'interview-root' },
    h('div', { class: 'chat-col' }, chat, confirmBar, h('div', { class: 'chat-input-row' }, input, h('button', { class: 'btn primary', onclick: send, disabled: iv.pending }, '전송'))),
    side);
}

// ─── Reanalyze entry ───
function viewReanalyzeEntry() {
  const wrap = h('div', { class: 'body', style: 'padding:24px 32px' });

  if (State.subjects.length === 0) {
    wrap.appendChild(h('div', { style: 'text-align:center;padding:48px;color:var(--fg-muted)' },
      h('div', { style: 'font-size:14px;margin-bottom:8px' }, '기존 대상자가 없습니다'),
      h('div', { style: 'font-size:12px' }, '먼저 "새 대상자" 탭에서 1차 분석을 실행하세요.')));
    return wrap;
  }

  wrap.appendChild(h('div', { style: 'margin-bottom:16px' },
    h('h2', { style: 'font-size:17px;font-weight:700;margin:0 0 4px' }, '대상자 선택'),
    h('p', { style: 'font-size:12.5px;color:var(--fg-muted);margin:0' }, '"대시보드 열기"로 기존 결과를 보거나, 선택 후 피드백·성과를 입력해 재분석하세요')));

  const grid = h('div', { style: 'display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:24px' });
  State.subjects.forEach(s => {
    const sel = State.selectedSubject === s.name;
    const badge = (txt, varName) => h('span', { style: 'font-size:10px;padding:2px 7px;border-radius:4px;background:var(--' + varName + '-bg);color:var(--' + varName + ')' }, txt);
    const badges = [];
    if (s.has_outputs) badges.push(badge('산출물', 'ag-platform'));
    if (s.has_feedback) badges.push(badge('피드백', 'ag-comp'));
    if (s.has_performance) badges.push(badge('성과기록', 'ag-target'));
    grid.appendChild(h('div', {
      style: 'padding:16px;border-radius:11px;border:1.5px solid ' + (sel ? 'var(--primary)' : 'var(--border)') + ';background:' + (sel ? 'var(--primary-soft)' : 'var(--bg-surface)') + ';cursor:pointer;transition:all .15s',
      onclick: () => Actions.selectSubject(s.name),
    },
      h('div', { style: 'font-weight:700;font-size:14px;margin-bottom:8px' }, s.name),
      h('div', { style: 'display:flex;gap:6px;flex-wrap:wrap' }, ...badges),
      h('button', { class: 'btn subtle sm', style: 'margin-top:12px;width:100%',
        onclick: (e) => { e.stopPropagation(); Actions.openSubject(s.name); } }, '대시보드 열기 →')));
  });
  wrap.appendChild(grid);

  if (State.selectedSubject) {
    const editor = h('div', { style: 'display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px' });
    const mkEditor = (title, getVal, setVal, ph, saveFn) => {
      const ta = h('textarea', { style: 'width:100%;min-height:170px;padding:12px;border:1px solid var(--border-strong);border-radius:8px;font-size:13px;line-height:1.55;resize:vertical;background:var(--bg-surface);box-sizing:border-box', placeholder: ph });
      ta.value = getVal();
      ta.addEventListener('input', (e) => setVal(e.target.value));
      return h('div', null,
        h('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:8px' },
          h('label', { style: 'font-weight:650;font-size:13px' }, title),
          h('button', { class: 'btn subtle sm', onclick: async () => { if (getVal().trim()) { try { await saveFn(State.selectedSubject, getVal()); } catch (_) {} } } }, '저장')),
        ta);
    };
    editor.appendChild(mkEditor('피드백', () => State.feedbackContent, v => State.feedbackContent = v,
      '수정 요청 사항을 자유롭게 작성하세요.\n예: 컨셉 A 대신 B로 진행, 플랫폼 유튜브 위주로 변경…', API.saveFeedback));
    editor.appendChild(mkEditor('성과 기록', () => State.performanceContent, v => State.performanceContent = v,
      '주차별 성과를 기록하세요.\n팔로워 수, 게시물 수, 조회수 등…', API.savePerformance));
    wrap.appendChild(editor);

    if (State.reanalyzeNotice) {
      wrap.appendChild(h('div', { style: 'text-align:right;color:var(--danger,#d33);font-size:12px;margin-bottom:8px' }, State.reanalyzeNotice));
    }
    wrap.appendChild(h('div', { style: 'display:flex;flex-direction:column;align-items:flex-end;gap:4px' },
      h('span', { style: 'font-size:11.5px;color:var(--fg-muted)' }, '재분석하려면 피드백·성과·방향 중 하나가 필요해요'),
      h('button', { class: 'btn primary', style: 'padding:10px 28px;font-size:14px', onclick: () => Actions.startReanalyze() }, '재분석 시작 →')));
  }
  return wrap;
}
