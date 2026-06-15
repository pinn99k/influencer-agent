# Claude Design UI Request - Influencer Agent Web UI

## Project Summary

An AI agency system. A CEO agent autonomously manages 1 influencer.
The user (Pinggu/Chairman) sets goals and subject info, then the CEO runs
4 sub-agents (Subject Analysis, Competition Analysis, Platform Recommendation,
Concept Planning) in order, aggregates results, and builds strategy.

The chairman only intervenes when 1 of 10 report conditions is triggered.
The UI is NOT an execution button - it's a window to see what the CEO is doing
+ a notification panel for chairman approvals.

## Current Backend (Already Complete - CLI verified)
- Python 3.11+, no framework (direct API calls via requests)
- LLM: Groq llama-3.3-70b / Gemini 2.0 Flash (switchable)
- Web search: Serper API
- No DB - markdown file based storage
- Entry point: src/main.py (CLI)
- Tests: 101/101 passing

## Agent Pipeline (Verified)
1. CEO interprets goal -> generates plan.md
2. PlanningDepartment runs 4 agents in sequence
3. Each agent result -> OutputValidator check -> retry once on fail
4. Context compression (3-line summary) between agents
5. All done -> Department briefing -> CEO judgment -> Chairman report check
6. 4 markdown output files saved

## Output File Structure
```
outputs/{influencer_name}/
  deliverables/          <- Final user-facing outputs
    01_subject_analysis.md
    02_competition_analysis.md
    03_platform_recommendation.md
    04_concept_planning.md
    .versions/           <- Auto-versioned backups
  handover/              <- Per-session handover docs
  .system/
    ceo/plan.md, state.md
    agents/{name}/raw_output.md, validation.md
    briefings/           <- Chairman report history
    logs/*.jsonl         <- UI real-time display
```

## Tech Stack for UI
- Backend: FastAPI + SSE (Server-Sent Events)
- Frontend: Static HTML/CSS/JS (no React/Vue needed)
- Markdown rendering: marked.js + DOMPurify
- Design mood: Linear, Vercel Dashboard - clean, functional, no decoration

## Screen Layout
```
+-----------------------------------------------------------+
|  Top bar: Managed influencer list + CEO overall status     |
+------------------------+----------------------------------+
|                        |                                  |
|  Left: Real-time       |  Right: Dashboard                |
|  Activity Feed         |                                  |
|                        |  CEO current plan                |
|  Which agent is        |  Recent completions              |
|  doing what, live      |  Performance metrics             |
|                        |  Pending approvals               |
|                        |                                  |
+------------------------+----------------------------------+
```

## 7 Core Components

### C-01: ActivityFeed (Real-time Activity Panel)
- Fixed left panel, SSE real-time streaming
- Display: [time] AgentName - status message
- When user opens browser, if CEO is already working, show immediately

### C-02: CEODashboard
- Current goal + D-day countdown
- CEO current state (what it's doing)
- Recent completed tasks
- Performance metrics (subscriber count changes, etc.)

### C-03: PendingApprovals
- Chairman report condition cards
- If empty = CEO is running fine. If present = CEO is BLOCKED waiting for approval
- Card click -> opens BriefingModal
- Badge notification when new approval needed

### C-04: BriefingModal
- Full-screen overlay (NO close button - must choose A or B)
- Content: Report condition / Status summary / Options A,B (pros/cons) / CEO recommendation
- After selection: POST /decision/{job_id} -> CEO loop resumes

### C-05: AgentActivityBar
- Per-agent status: WAITING / RUNNING / DONE / FAILED
- Widget in dashboard or above ActivityFeed

### C-06: ReportViewer
- View completed agent outputs
- Tabs: Subject / Competition / Platform / Concept
- Markdown rendered + download (.md)

### C-07: GoalEditor
- Edit goal or subject info from dashboard settings
- Changes notify CEO (may trigger report condition #3)

## Entry Screen (First time only)
- 7 subject fields: Name, Job, Specialty, Personality, Target Age, SNS Experience, Goal
- Final goal text for CEO
- Button: "Appoint CEO" (start management)
- After this screen, never shown again. Edits via GoalEditor.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /start | Appoint CEO (first time) |
| GET | /status | CEO + running jobs full state |
| GET | /stream | SSE - all events real-time |
| GET | /stream/{job_id} | SSE - specific job events |
| DELETE | /job/{job_id} | Cancel running job |
| POST | /decision/{job_id} | Chairman report response |
| PATCH | /goal | Edit goal |
| GET | /reports | List deliverables |
| GET | /reports/{filename} | Get deliverable content (markdown) |

## SSE Event Structure
```json
{"timestamp": "...", "type": "agent_start", "agent": "competition_analysis", "job_id": "..."}
{"timestamp": "...", "type": "agent_done", "agent": "competition_analysis", "job_id": "..."}
{"timestamp": "...", "type": "ceo_thinking", "detail": "deciding next action"}
{"timestamp": "...", "type": "validation_pass", "agent": "subject_analysis"}
{"timestamp": "...", "type": "validation_fail", "agent": "subject_analysis", "retry": 1}
{"timestamp": "...", "type": "briefing", "condition": 5, "job_id": "..."}
{"timestamp": "...", "type": "completed", "detail": "full pipeline done"}
```

## Backend File Structure (to create)
```
src/api/
  main.py               <- FastAPI app entry
  session_manager.py    <- CEO state + job tracking + SSE event queue
  routes/
    ceo.py              <- /start, /status, /goal
    stream.py           <- /stream, /stream/{job_id}
    decision.py         <- /decision/{job_id}, /job/{job_id}
    reports.py          <- /reports, /reports/{filename}
  static/
    index.html
    style.css
    app.js
```

## 10 Chairman Report Conditions
(CEO stops and asks chairman for approval)

1. Any cost-incurring decision
2. Legal risk detected
3. Initial goal change needed
4. Creator swap / full concept overhaul affecting people
5. Agent fails after 2 retries
6. Conflicting results between agents
7. Need to contact real external people
8. Need to share personal data externally
9. AI output transitioning to real execution (filming, uploading)
10. Results significantly different from chairman expectations

## Reference Files in Codebase
- docs/workflow/step7_구현/claude-design-handoff.md (detailed handoff)
- docs/workflow/step6_아키텍처/아키텍처.md (system architecture)
- docs/workflow/step4_기능명세/워크스페이스_구조.md (folder structure)
- src/agents/ceo.py (CEO orchestration)
- src/departments/planning.py (Planning department layer)
- src/core/file_manager.py (file save logic)
- src/validators/output_validator.py (output validation)

## Implementation Order
1. session_manager.py - CEO state + job tracking + event queue
2. SSE endpoint (/stream) - session_manager event streaming
3. Dashboard skeleton (C-02) + Activity Feed (C-01)
4. Pending Approvals (C-03) + Briefing Modal (C-04)
5. Report Viewer (C-06)
6. Entry screen (first-time CEO appointment)
7. Styling