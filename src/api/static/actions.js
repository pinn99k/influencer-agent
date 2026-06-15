/* actions.js — MVC Controller layer
   All side-effecting logic: calls API (api.js), mutates State (model.js),
   wires SSE. Views call Actions.xxx(); Views never fetch directly. */

const Actions = {
  async appoint(persona) {
    // Fill empty fields with "정보 없음"
    FIELDS.forEach(f => {
      if (!persona[f.key] || !persona[f.key].trim()) persona[f.key] = '정보 없음';
    });

    State.persona = persona;
    State.appointed = true;
    State.reanalyzeMode = false;   // fresh first analysis — clear any stale reanalysis flag
    State.rerunDecision = null;
    State.chatId = null;
    State.pendingDirection = null;

    try {
      localStorage.setItem('ceo_appointed_v1', '1');
      localStorage.setItem('ceo_persona_v1', JSON.stringify(persona));
    } catch {}

    State.notify();

    // Call backend
    try {
      const data = await API.start(persona);
      State.currentJobId = data.job_id;
      State.influencerName = persona['이름'] || 'unknown';
      try {
        localStorage.setItem('ceo_job_id', data.job_id);
        localStorage.setItem('ceo_influencer', State.influencerName);
      } catch {}

      // Connect SSE
      API.openStream(data.job_id, (evt) => Actions.pushActivity(evt));
      State.notify();
    } catch (err) {
      console.warn('/start failed — demo mode:', err.message);
    }
  },

  reset() {
    try {
      localStorage.removeItem('ceo_appointed_v1');
      localStorage.removeItem('ceo_persona_v1');
      localStorage.removeItem('ceo_job_id');
      localStorage.removeItem('ceo_influencer');
    } catch {}
    if (API._closeStream) API._closeStream();
    State.appointed = false;
    State.persona = null;
    State.currentJobId = null;
    State.influencerName = null;
    State.activity = [];
    State.approvals = [];
    State.reports = [];
    State.plan = null;
    State.ceoState = 'thinking';
    State.reanalyzeMode = false;
    State.subjects = [];
    State.selectedSubject = null;
    State.feedbackContent = '';
    State.performanceContent = '';
    State.entryTab = 'interview';
    State.interview = null;
    State.managerNotes = [];
    State.dockMode = 'chat';
    State.dockCollapsed = false;
    State.ceoChat = [];
    State.rerunDecision = null;
    State.chatId = null;
    State.pendingDirection = null;
    State.notify();
  },

  // Disk-first boot recovery (Fix A).
  // Prior bug: recovery depended on the in-memory job (/status/{job_id}); a server
  // restart cleared SessionManager → 404 → Actions.reset() wiped everything even
  // though outputs/ on disk were intact. Now: restore from disk by influencer name
  // first; the in-memory job is used ONLY to replay live events / reconnect SSE for
  // a still-running job. A 404 must never wipe state.
  async bootRecover() {
    const name = State.influencerName;
    let restoredFromDisk = false;

    if (name) {
      try {
        const data = await API.listReports(name);
        if (data && data.reports && data.reports.length > 0) {
          State.reports = data.reports.map((fname, i) => ({
            id: fname,
            agent: ['target', 'comp', 'platform', 'concept'][i] || 'ceo',
            title: fname.replace('.md', '').replace(/_/g, ' '),
            at: '이전 세션', size: '—',
          }));
          State.appointed = true;
          State.ceoState = 'completed';
          restoredFromDisk = true;
          await Actions.loadPlan(name);
          State.notify();
        }
      } catch (_) {
        // No outputs on disk yet — keep state restored from localStorage.
      }
      // Restore the persisted CEO conversation (survives refresh/restart).
      try {
        const hist = await API.chatHistory(name);
        if (hist && hist.messages && hist.messages.length) {
          State.ceoChat = hist.messages.map(m => ({
            role: m.role === 'assistant' ? 'ceo' : 'user', text: m.content,
          }));
          State.notify();
        }
      } catch (_) {}
    }

    if (!State.currentJobId) return;

    // In-memory job: replay events / reconnect SSE only. 404 must NOT wipe state.
    try {
      const s = await API.jobStatus(State.currentJobId);
      if (!s) return;
      if (s.subject) State.persona = s.subject;

      const running = s.status === 'running' || s.status === 'waiting_decision';

      if (!restoredFromDisk && s.reports && s.reports.length > 0) {
        State.reports = s.reports.map((fname, i) => ({
          id: fname,
          agent: ['target', 'comp', 'platform', 'concept'][i] || 'ceo',
          title: fname.replace('.md', '').replace(/_/g, ' '),
          at: '이전 세션', size: '—',
        }));
        State.ceoState = running ? State.ceoState : 'completed';
        Actions.loadPlan(s.influencer_name || name);
      }

      if (s.recent_events) {
        const decided = s.recent_events.some(e => e.type === 'decision_received');
        s.recent_events.forEach(evt => {
          if (evt.type === 'briefing_pending' && (decided || s.status !== 'waiting_decision')) {
            return; // Skip — already decided or job not waiting
          }
          Actions.pushActivity(evt);
        });
      }

      if (running) {
        API.openStream(State.currentJobId, (evt) => Actions.pushActivity(evt));
      }
      State.notify();
    } catch (_) {
      // Job gone (server restarted). Disk state (if any) stands. Never reset here.
      // Drop the dead job pointer so name-based disk fallbacks (agent detail, Fix B)
      // resolve against the influencer name instead of a stale job id.
      State.currentJobId = null;
      try { localStorage.removeItem('ceo_job_id'); } catch (__) {}
      State.notify();
    }
  },

  // U6 — 실제 CEO 채팅 백엔드 연결. 컨텍스트 인지 멀티턴 대화 + 방향 포착.
  async sendCeoMessage(text) {
    if (!text || !text.trim()) return;
    const t = text.trim();
    State.ceoChat = (State.ceoChat || []).concat([{ role: 'user', text: t }]);
    State.notify();

    const name = State.influencerName || (State.persona && State.persona['이름']);
    if (!name) {
      State.ceoChat = State.ceoChat.concat([{ role: 'ceo',
        text: '먼저 분석을 시작하면 그 결과를 바탕으로 대화할 수 있어요.' }]);
      State.notify();
      return;
    }

    try {
      if (!State.chatId) {
        const s = await API.chatStart(name);   // 세션 생성(인사말은 UI가 이미 표시)
        State.chatId = s.chat_id;
      }
      const r = await API.chatReply(State.chatId, t);
      State.ceoChat = State.ceoChat.concat([{ role: 'ceo', text: r.message }]);
      if (r.captured_direction) {
        State.pendingDirection = r.captured_direction;   // 방향 포착 → 갱신 버튼 노출
      }
    } catch (e) {
      State.ceoChat = State.ceoChat.concat([{ role: 'ceo',
        text: '(응답 오류) 잠시 후 다시 시도해주세요.' }]);
    }
    State.notify();
  },

  // P1-U4 — 측정 레이어 기록. 실패해도 UI가 죽지 않게 ok bool 반환.
  async recordKpi(body) {
    const name = State.influencerName || (State.persona && State.persona['이름']);
    if (!name) return false;
    try { await API.measureKpi(name, body); return true; }
    catch (e) { console.warn('kpi save failed:', e.message); return false; }
  },

  async logContent(body) {
    const name = State.influencerName || (State.persona && State.persona['이름']);
    if (!name) return false;
    try { await API.measureContent(name, body); return true; }
    catch (e) { console.warn('content log failed:', e.message); return false; }
  },

  // U6 — 채팅에서 포착한 방향을 방향.md에 저장(기존 방향에 누적). reanalyze=true면 재분석까지.
  async applyDirection(reanalyze) {
    const name = State.influencerName || (State.persona && State.persona['이름']);
    if (!name || !State.pendingDirection) return;

    let existing = '';
    try { const d = await API.getDirection(name); existing = (d && d.content) || ''; } catch (_) {}
    const head = existing.trim() ? existing.trimEnd() + '\n' : '# 방향\n';
    const content = head + '- ' + State.pendingDirection + '\n';
    try { await API.saveDirection(name, content); } catch (_) {}

    const captured = State.pendingDirection;
    State.pendingDirection = null;

    if (reanalyze) {
      State.ceoChat = (State.ceoChat || []).concat([{ role: 'ceo',
        text: '방향(' + captured + ')을 반영해 재분석을 시작할게요.' }]);
      State.notify();
      await Actions.startReanalyze(name);
    } else {
      State.ceoChat = (State.ceoChat || []).concat([{ role: 'ceo',
        text: '방향을 저장했어요. 다음 재분석 때 전략에 반영할게요.' }]);
      State.notify();
    }
  },

  async startInterview() {
    State.entryTab = 'interview';
    State.interview = { id: null, messages: [], extracted: {}, sufficient: false,
                       summary: false, pending: true, turn: 0, canSubmit: false,
                       missing: [] };
    State.notify();
    try {
      const data = await API.interviewStart();
      State.interview.id = data.interview_id;
      State.interview.messages.push({ role: 'ceo', text: data.message });
    } catch (e) {
      State.interview.messages.push({ role: 'ceo',
        text: '(백엔드 미연결) 인터뷰를 시작할 수 없습니다. 서버를 확인해주세요.' });
      State.interview.error = true;
    }
    State.interview.pending = false;
    State.notify();
  },

  async sendInterview(text) {
    const iv = State.interview;
    if (!iv || !iv.id || !text || !text.trim()) return;
    iv.messages.push({ role: 'user', text: text.trim() });
    iv.pending = true;
    State.notify();
    try {
      const data = await API.interviewReply(iv.id, text.trim());
      iv.messages.push({ role: 'ceo', text: data.message });
      iv.extracted = data.extracted || iv.extracted;
      iv.sufficient = !!data.sufficient;
      iv.turn = data.turn_count || iv.turn;
      iv.summary = (data.type === 'summary');
      iv.canSubmit = !!data.can_submit;
    } catch (e) {
      iv.messages.push({ role: 'ceo', text: '(응답 오류) 다시 한 번 말씀해주시겠어요?' });
    }
    iv.pending = false;
    State.notify();
  },

  async confirmInterview() {
    const iv = State.interview;
    if (!iv || !iv.id) return;
    iv.pending = true;
    State.notify();
    try {
      const data = await API.interviewConfirm(iv.id, true, null, true);

      // Case A: not submittable yet — dialogue stays alive, CEO asks for more.
      if (data && data.approved === false) {
        iv.pending = false;
        iv.canSubmit = false;
        iv.missing = data.missing || [];
        const needName = (data.missing || []).includes('이름');
        iv.messages.push({ role: 'ceo', text: needName
          ? '분석을 시작하려면 성함이 필요해요. 실명이 부담되시면 활동명이나 닉네임이라도 좋아요.'
          : '분석을 시작하기엔 정보가 조금 더 필요해요. 몇 가지만 더 들려주시겠어요?' });
        State.notify();
        return;
      }

      // Case B: job started — move to dashboard and stream progress.
      if (data && data.job_id) {
        const subject = data.subject || {};
        State.persona = subject;
        State.appointed = true;
        State.influencerName = subject['이름'] || 'unknown';
        State.currentJobId = data.job_id;
        State.activity = []; State.approvals = []; State.reports = [];
        State.plan = null;
        State.reanalyzeMode = false; State.rerunDecision = null;
        State.chatId = null; State.pendingDirection = null;
        State.managerNotes = []; State.ceoState = 'thinking';
        try {
          localStorage.setItem('ceo_appointed_v1', '1');
          localStorage.setItem('ceo_persona_v1', JSON.stringify(subject));
          localStorage.setItem('ceo_job_id', data.job_id);
          localStorage.setItem('ceo_influencer', State.influencerName);
        } catch {}
        API.openStream(data.job_id, (evt) => Actions.pushActivity(evt));
        State.interview = null;
        State.notify();
        return;
      }

      // Case C: confirmed but no job (start_job=false) — unexpected here.
      iv.pending = false;
      iv.messages.push({ role: 'ceo', text: '확정되었지만 분석을 시작하지 못했어요. 다시 시도해주세요.' });
      State.notify();
    } catch (e) {
      iv.pending = false;
      const msg = String(e.message || '');
      iv.messages.push({ role: 'ceo',
        text: '분석 시작에 실패했어요. 잠시 후 다시 시도해주세요. (' + msg + ')' });
      State.notify();
    }
  },

  async loadSubjects() {
    try {
      const data = await API.listSubjects();
      State.subjects = data.subjects || [];
      State.notify();
    } catch (e) {
      console.warn('subjects load failed:', e.message);
      State.subjects = [];
      State.notify();
    }
  },

  async selectSubject(name) {
    State.selectedSubject = name;
    try {
      const [fb, perf] = await Promise.all([
        API.getFeedback(name),
        API.getPerformance(name),
      ]);
      State.feedbackContent = fb.content || '';
      State.performanceContent = perf.content || '';
    } catch (e) {
      State.feedbackContent = '';
      State.performanceContent = '';
    }
    State.notify();
  },

  // Single reanalyze entry point. `name` defaults to the reanalyze-screen
  // selection but the manager dock passes the active influencer (Fix D unifies
  // both feedback paths through here). Saves perf+feedback, then starts the job.
  // Returns true on success so callers can message honestly.
  async startReanalyze(name) {
    const target = name || State.selectedSubject;
    if (!target) return false;

    // Save feedback if present
    if ((State.feedbackContent || '').trim()) {
      try { await API.saveFeedback(target, State.feedbackContent); } catch(_) {}
    }
    // Save performance if present
    if ((State.performanceContent || '').trim()) {
      try { await API.savePerformance(target, State.performanceContent); } catch(_) {}
    }

    try {
      const data = await API.startReanalyze(
        target,
        (State.feedbackContent || '').trim() || undefined
      );
      State.currentJobId = data.job_id;
      State.influencerName = target;
      State.selectedSubject = target;
      State.appointed = true;
      State.reanalyzeMode = true;
      State.reanalyzeNotice = null;
      State.persona = State.persona || { '이름': target };
      State.activity = [];
      State.approvals = [];
      State.plan = null;
      State.rerunDecision = null;
      State.chatId = null;            // reanalysis changes outputs → fresh chat context
      State.pendingDirection = null;
      State.ceoState = 'thinking';

      try {
        localStorage.setItem('ceo_appointed_v1', '1');
        localStorage.setItem('ceo_job_id', data.job_id);
        localStorage.setItem('ceo_influencer', target);
      } catch {}

      API.openStream(data.job_id, (evt) => Actions.pushActivity(evt));
      State.notify();
      return true;
    } catch (err) {
      console.warn('reanalyze start failed:', err.message);
      State.reanalyzeNotice = err.message || '재분석을 시작하지 못했어요.';
      State.notify();
      return false;
    }
  },

  // Fix D — '매니저에게 전달'이 실제로 하는 일을 정직하게: 성과·피드백을 저장하고
  // 그 데이터로 재분석(CEO _decide_rerun)을 실제 트리거한다. 가짜 ack 제거.
  async deliverToManager() {
    const name = State.influencerName || (State.persona && State.persona['이름']);
    if (!name) return;
    const ok = await Actions.startReanalyze(name);
    State.dockMode = 'chat';
    State.ceoChat = (State.ceoChat || []).concat([{
      role: 'ceo',
      text: ok
        ? '전달해주신 성과·피드백으로 재분석을 시작했어요. 어떤 분석을 왜 다시 하는지는 작업 현황에 표시돼요.'
        : (State.reanalyzeNotice || '재분석을 시작하지 못했어요. 성과나 피드백을 입력해 주세요.'),
    }]);
    State.notify();
  },

  // U1 — 기존 대상자 대시보드를 재분석 없이 읽기 전용으로 연다 (디스크 복원).
  async openSubject(name) {
    if (!name) return;
    if (API._closeStream) API._closeStream();
    State.currentJobId = null;
    State.influencerName = name;
    State.persona = { '이름': name };
    State.appointed = true;
    State.reanalyzeMode = false;
    State.rerunDecision = null;
    State.activity = []; State.approvals = [];
    State.selectedSubject = name;
    State.chatId = null; State.pendingDirection = null;
    State.reanalyzeNotice = null;
    State.ceoState = 'completed';
    try {
      localStorage.setItem('ceo_appointed_v1', '1');
      localStorage.setItem('ceo_influencer', name);
      localStorage.removeItem('ceo_job_id');
    } catch {}
    State.notify();
    try {
      const data = await API.listReports(name);
      if (data && data.reports && data.reports.length) {
        State.reports = data.reports.map((fname, i) => ({
          id: fname, agent: ['target', 'comp', 'platform', 'concept'][i] || 'ceo',
          title: fname.replace('.md', '').replace(/_/g, ' '), at: '저장됨', size: '—',
        }));
      }
    } catch (_) {}
    await Actions.loadPlan(name);
    try {
      const hist = await API.chatHistory(name);
      if (hist && hist.messages && hist.messages.length) {
        State.ceoChat = hist.messages.map(m => ({
          role: m.role === 'assistant' ? 'ceo' : 'user', text: m.content }));
      }
    } catch (_) {}
    State.notify();
  },

  pushActivity(evt) {
    if (evt.type === 'rerun_decided') {
      // Fix E — surface CEO's rerun decision (which agents, why) for review/correction.
      const backendAgents = evt.rerun_agents || [];
      State.rerunDecision = {
        agents: backendAgents.map(a => BACKEND_AGENT[a] || a),
        agentsRaw: backendAgents,
        reason: evt.reason || '',
        at: new Date(evt.timestamp || Date.now()).toTimeString().slice(0, 8),
      };
      // Still record it on the timeline below (don't return early).
    }
    if (evt.type === 'reanalyze_skipped') {
      State.ceoChat = (State.ceoChat || []).concat([{ role: 'ceo',
        text: '재분석할 새 입력(성과·피드백·방향)이 없어 다시 실행하지 않았어요. 매니저 정보 탭에서 성과나 피드백을 입력해 주세요.' }]);
    }
    if (evt.type === 'manager_notification') {
      State.managerNotes.unshift({
        t: new Date(evt.timestamp || Date.now()).toTimeString().slice(0, 8),
        kind: evt.notification_type || 'info',
        week: evt.week_num || null,
        content: evt.content || '',
      });
      if (State.managerNotes.length > 30) State.managerNotes.length = 30;
      State.notify();
      return;
    }
    const agent = evt.agent
      ? (BACKEND_AGENT[evt.agent] || (AGENT_META[evt.agent] ? evt.agent : 'ceo'))
      : 'ceo';
    const t = new Date(evt.timestamp || Date.now()).toTimeString().slice(0, 8);
    State.activity.unshift({
      t, type: evt.type || 'job_started',
      agent,
      text: TYPE_LABEL[evt.type] || evt.type,
      detail: evt.detail || null,
      mode: evt.mode || null,   // 'reanalyze' for reanalysis events (CEO message wiring)
      validated: (evt.validated === undefined ? null : evt.validated),  // L3: 검증 통과 여부
    });
    if (State.activity.length > 60) State.activity.length = 60;

    // Update CEO state based on event
    if (evt.type === 'briefing_pending') {
      State.ceoState = 'waiting';
      // Add to approvals
      State.approvals.push({
        id: evt.job_id || 'br-' + Date.now(),
        condition: evt.condition || '?',
        title: '회장 보고 — 조건 ' + (evt.condition || '?'),
        summary: evt.briefing || '결재가 필요합니다.',
        age: '방금 전',
        optionA: { label: 'A 선택', detail: '첫 번째 선택지' },
        optionB: { label: 'B 선택', detail: '두 번째 선택지' },
        rec: 'A',
        job_id: evt.job_id || State.currentJobId,
      });
    } else if (evt.type === 'decision_received') {
      State.ceoState = 'running';
    } else if (evt.type === 'agent_start') {
      State.ceoState = 'running';
    } else if (evt.type === 'plan_created' || evt.type === 'finalize_started') {
      State.ceoState = 'thinking';
    } else if (evt.type === 'job_completed') {
      State.ceoState = 'completed';
      Actions._loadReports();
      Actions.loadPlan();
    } else if (evt.type === 'job_failed') {
      State.ceoState = 'failed';
    }

    State.notify();
  },

  async _loadReports() {
    if (!State.influencerName) return;
    try {
      const data = await API.listReports(State.influencerName);
      State.reports = (data.reports || []).map((fname, i) => ({
        id: fname,
        agent: ['target', 'comp', 'platform', 'concept'][i] || 'ceo',
        title: fname.replace('.md', '').replace(/_/g, ' '),
        at: '방금 완료',
        size: '—',
      }));
      State.notify();
    } catch (_) {}
  },

  async loadPlan(name) {
    const target = name || State.influencerName;
    if (!target) return;
    try {
      State.plan = await API.getPlan(target);
      State.notify();
    } catch (_) {
      State.plan = null;
      State.notify();
    }
  },
};
