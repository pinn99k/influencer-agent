/* api.js — MVC layer (auto-split from app.js, behavior preserved)
   Controller(transport): REST client + SSE openStream. fetch lives ONLY here */

// ─── API Client (adapted to /api/* backend) ─────────
const API = {
  base: '/api',
  _closeStream: null,

  async _req(path, opts = {}) {
    const res = await fetch(this.base + path, {
      headers: { 'content-type': 'application/json' },
      ...opts,
    });
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.json()).detail || ''; } catch (_) {}
      throw new Error(detail || `${res.status} ${res.statusText}`);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('json') ? res.json() : res.text();
  },

  /** POST /api/start — wraps persona as {subject: persona} */
  start(persona) {
    return this._req('/start', {
      method: 'POST',
      body: JSON.stringify({ subject: persona }),
    });
  },

  /** GET /api/status/{job_id} — full job state for recovery */
  jobStatus(jobId) {
    return this._req('/status/' + jobId);
  },

  /** POST /api/decision/{job_id} */
  decision(jobId, choice, reason) {
    return this._req('/decision/' + jobId, {
      method: 'POST',
      body: JSON.stringify({ choice, reason: reason || '' }),
    });
  },

  /** DELETE /api/job/{job_id} */
  cancelJob(jobId) {
    return this._req('/job/' + jobId, { method: 'DELETE' });
  },

  /** GET /api/reports/{name} — list */
  listReports(name) {
    return this._req('/reports/' + encodeURIComponent(name));
  },

  /** GET /api/reports/{name}/{file} — content */
  getReport(name, filename) {
    return this._req('/reports/' + encodeURIComponent(name) + '/' + encodeURIComponent(filename));
  },

  /** GET /api/plan/{name} */
  getPlan(name) {
    return this._req('/plan/' + encodeURIComponent(name));
  },

  /** GET /api/subjects — 기존 대상자 목록 */
  listSubjects() { return this._req('/subjects'); },

  /** POST /api/reanalyze — 재분석 시작 */
  startReanalyze(name, feedback) {
    return this._req('/reanalyze', {
      method: 'POST',
      body: JSON.stringify({ name, feedback: feedback || undefined }),
    });
  },

  /** GET /api/feedback/{name} */
  getFeedback(name) { return this._req('/feedback/' + encodeURIComponent(name)); },

  /** PUT /api/feedback/{name} */
  saveFeedback(name, content) {
    return this._req('/feedback/' + encodeURIComponent(name), {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  /** GET /api/performance/{name} */
  getPerformance(name) { return this._req('/performance/' + encodeURIComponent(name)); },

  /** PUT /api/performance/{name} */
  savePerformance(name, content) {
    return this._req('/performance/' + encodeURIComponent(name), {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  /** POST /api/chat/start — 컨텍스트 인지 CEO 채팅 세션 시작 */
  chatStart(name) {
    return this._req('/chat/start', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  /** POST /api/chat/reply — {message, captured_direction} */
  chatReply(chatId, message) {
    return this._req('/chat/reply', {
      method: 'POST',
      body: JSON.stringify({ chat_id: chatId, message }),
    });
  },

  /** GET /api/chat/history/{name} — 영속된 CEO 대화 (부팅 복원) */
  chatHistory(name) { return this._req('/chat/history/' + encodeURIComponent(name)); },

  /** GET /api/direction/{name} */
  getDirection(name) { return this._req('/direction/' + encodeURIComponent(name)); },

  /** PUT /api/direction/{name} */
  saveDirection(name, content) {
    return this._req('/direction/' + encodeURIComponent(name), {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  /** PUT /api/measure/{name}/kpi — 주간 KPI 기록 */
  measureKpi(name, body) {
    return this._req('/measure/' + encodeURIComponent(name) + '/kpi', {
      method: 'PUT', body: JSON.stringify(body),
    });
  },

  /** POST /api/measure/{name}/content — 게시물 기록 (변수 태깅) */
  measureContent(name, body) {
    return this._req('/measure/' + encodeURIComponent(name) + '/content', {
      method: 'POST', body: JSON.stringify(body),
    });
  },

  /** GET /api/measure/{name}/summary */
  measureSummary(name) {
    return this._req('/measure/' + encodeURIComponent(name) + '/summary');
  },

  /** POST /api/interview/start */
  interviewStart() { return this._req('/interview/start', { method: 'POST' }); },

  /** POST /api/interview/reply */
  interviewReply(id, message) {
    return this._req('/interview/reply', {
      method: 'POST',
      body: JSON.stringify({ interview_id: id, message }),
    });
  },

  /** POST /api/interview/confirm */
  interviewConfirm(id, approved, corrections, startJob) {
    return this._req('/interview/confirm', {
      method: 'POST',
      body: JSON.stringify({
        interview_id: id, approved: approved !== false,
        corrections: corrections || null, start_job: startJob !== false,
      }),
    });
  },

  /** SSE stream per job. Returns close function. */
  openStream(jobId, onEvent) {
    if (this._closeStream) this._closeStream();
    const url = this.base + '/stream/' + jobId;
    try {
      const es = new EventSource(url);
      es.onmessage = (e) => {
        try { onEvent(JSON.parse(e.data)); } catch (_) {}
      };
      es.onerror = () => console.warn('SSE reconnecting...');
      this._closeStream = () => es.close();
      return this._closeStream;
    } catch (err) {
      console.warn('SSE unavailable — demo mode');
      return () => {};
    }
  },
};

