/* model.js — MVC Model layer
   Pure state: data fields + pub/sub (subscribe/notify/set/init).
   Knows NOTHING about DOM or fetch. Views read this; Actions mutate it. */

const State = {
  appointed: false,
  persona: null,
  currentJobId: null,
  influencerName: null,
  ceoState: 'thinking',
  activity: [],
  approvals: [],
  reports: [],
  plan: null,
  view: 'dashboard',
  viewParam: null,
  activityTab: 'timeline',  // 'timeline' or 'agents'
  agentDetail: null,  // {agent, content} when modal is open
  entryTab: 'interview',     // 'interview' | 'new' | 'reanalyze'
  interview: null,           // active interview session
  managerNotes: [],          // manager notifications
  reanalyzeMode: false,
  subjects: [],
  selectedSubject: null,
  feedbackContent: '',
  performanceContent: '',
  dockMode: 'chat',        // 좌측 도크: 'chat'(CEO 대화) | 'manager'(매니저 정보)  [v3]
  dockCollapsed: false,    // 좌측 도크 접힘 여부  [v3]
  ceoChat: [],             // 임명 후 CEO와 주고받은 메시지 {role, text}  [v3]
  rerunDecision: null,     // 재분석 시 CEO 재실행 결정 {agents, reason, at}  [Fix E]
  chatId: null,            // 실제 CEO 채팅 세션 id  [U6]
  pendingDirection: null,  // 채팅에서 포착된 방향(저장/재분석 대기)  [U6]
  reanalyzeNotice: null,   // 재분석 실패 안내 (백엔드 게이트 메시지)  [U2]
  _subs: [],

  init() {
    try {
      this.appointed = localStorage.getItem('ceo_appointed_v1') === '1';
      const p = localStorage.getItem('ceo_persona_v1');
      this.persona = p ? JSON.parse(p) : null;
      this.currentJobId = localStorage.getItem('ceo_job_id') || null;
      this.influencerName = localStorage.getItem('ceo_influencer') || null;
    } catch { /* ignore */ }
  },

  subscribe(fn) { this._subs.push(fn); return () => { this._subs = this._subs.filter(s => s !== fn); }; },
  notify() { this._subs.forEach(fn => fn()); },
  set(patch) { Object.assign(this, patch); this.notify(); },
};
