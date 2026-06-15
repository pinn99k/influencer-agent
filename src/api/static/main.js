/* main.js — MVC layer (auto-split from app.js, behavior preserved)
   Boot: Router + render subscribe + init + SSE recovery + keyboard */

// ─── Router ────────────────────────────────────────
const Router = {
  go(view, param) {
    State.set({ view, viewParam: param || null });
  },
};

// ─── Mount ─────────────────────────────────────────
async function render() {
  const root = $('#root');
  clear(root);

  if (!State.appointed) {
    root.appendChild(viewEntry());
    return;
  }

  const app = h('div', { class: 'app-root' }, viewTopBar(), viewDashboard());
  app.appendChild(h('button', { class: 'dev-reset', onclick: () => Actions.reset() }, '↺ 임명 초기화 (DEV)'));
  root.appendChild(app);

  if (State.agentDetail) {
    root.appendChild(viewAgentDetailModal());
  }

  if (State.view === 'briefing') {
    root.appendChild(viewBriefing(State.viewParam));
  } else if (State.view === 'report') {
    const reportEl = await viewReport(State.viewParam);
    root.appendChild(reportEl);
  }
}

// ─── Boot ──────────────────────────────────────────
State.init();
State.subscribe(render);
render();

// Boot recovery — disk-first (survives server restart). See Actions.bootRecover (Fix A).
Actions.bootRecover();

// Keyboard shortcuts
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && State.view !== 'dashboard') {
    Router.go('dashboard');
  }
  if (State.view === 'briefing') {
    if (e.key.toLowerCase() === 'a') $('.briefing .btn.primary')?.click();
    if (e.key.toLowerCase() === 'b') $('.briefing .btn:not(.primary)')?.click();
  }
});
