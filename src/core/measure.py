"""Measurement/experiment layer — KPI, content variable tagging, decision log.

Spec: docs/workflow/2장_에이전트하네스/03_측정실험설계.md
Why this exists: performance data without variable attribution is noise. Every
content item carries its experiment variables (topic/format/length/time slot),
and every strategy decision carries provenance (AI vs human) so the portfolio
can honestly say "AI decided N, human decided M".

Storage (markdown tables, no DB — project principle):
  outputs/{name}/.system/measure/
    ├── kpi.md           weekly KPI rows
    ├── content_log.md   one row per content item ({KPI + variable tags})
    └── decision_log.md  one row per decision (+ provenance)

SRP: this module only records/loads/aggregates. Callers (CEO hooks, routes)
decide WHEN to log. No LLM, no HTTP here.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import datetime

from core.config import OUTPUTS_DIR

ACTOR_AI = "AI"
ACTOR_HUMAN = "사람"

# Variable tags available for comparison — extend the list to add experiments (OCP).
_COMPARABLE_VARS = ("topic", "fmt", "length", "time_slot", "week")

_KPI_HEADER = "| week | followers | content_count | total_views | engagement | conversions |"
_KPI_SEP = "|---|---|---|---|---|---|"
_CONTENT_HEADER = ("| date | week | title | topic | fmt | length | time_slot "
                   "| views | likes | saves | comments |")
_CONTENT_SEP = "|---|---|---|---|---|---|---|---|---|---|---|"
_DECISION_HEADER = "| timestamp | actor | basis | decision | result |"
_DECISION_SEP = "|---|---|---|---|---|"


@dataclass
class WeeklyKPI:
    week: int
    followers: int = 0
    content_count: int = 0
    total_views: int = 0
    engagement: int = 0      # saves+likes+comments aggregate for the week
    conversions: int = 0     # inquiries/sponsorships


@dataclass
class ContentEntry:
    date: str                # YYYY-MM-DD
    title: str
    topic: str               # 주제: before/after, 컬러, 시술 팁, 일상 ...
    fmt: str                 # 형식: 릴스, 쇼츠, 캐러셀, 스토리
    length: str              # 길이: 15초/30초/60초
    time_slot: str           # 시간대: 오전/점심/저녁/밤
    views: int = 0
    likes: int = 0
    saves: int = 0
    comments: int = 0
    week: int = 0

    @property
    def engagement(self) -> int:
        return self.likes + self.saves + self.comments


@dataclass
class DecisionEntry:
    actor: str               # ACTOR_AI | ACTOR_HUMAN — provenance is mandatory
    basis: str               # what evidence drove it
    decision: str            # what was changed
    result: str = ""         # observed effect (filled in later weeks)
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    def __post_init__(self):
        if self.actor not in (ACTOR_AI, ACTOR_HUMAN):
            raise ValueError(f"actor must be '{ACTOR_AI}' or '{ACTOR_HUMAN}', got: {self.actor}")


def _esc(v) -> str:
    """Markdown-table-safe cell."""
    return str(v).replace("|", "/").replace("\n", " ").strip()


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


class MeasureStore:
    def __init__(self, influencer_name: str):
        self.name = influencer_name
        self.base = OUTPUTS_DIR / influencer_name / ".system" / "measure"

    # ---------- weekly KPI ----------
    def record_kpi(self, kpi: WeeklyKPI) -> Path:
        """Insert or replace the row for kpi.week (idempotent weekly update)."""
        kpis = {k.week: k for k in self.load_kpis()}
        kpis[kpi.week] = kpi
        rows = [_KPI_HEADER, _KPI_SEP]
        for w in sorted(kpis):
            k = kpis[w]
            rows.append("| " + " | ".join(_esc(v) for v in (
                k.week, k.followers, k.content_count, k.total_views,
                k.engagement, k.conversions)) + " |")
        return self._write("kpi.md", "# 주차별 KPI\n\n" + "\n".join(rows) + "\n")

    def load_kpis(self) -> list[WeeklyKPI]:
        out = []
        for cells in self._table_rows("kpi.md", ncols=6):
            try:
                out.append(WeeklyKPI(*[int(c) for c in cells]))
            except ValueError:
                continue
        return sorted(out, key=lambda k: k.week)

    # ---------- per-content log ----------
    def log_content(self, entry: ContentEntry) -> Path:
        path = self.base / "content_log.md"
        if not path.exists():
            self._write("content_log.md",
                        "# 게시물 기록 (KPI + 변수 태그)\n\n"
                        + _CONTENT_HEADER + "\n" + _CONTENT_SEP + "\n")
        row = "| " + " | ".join(_esc(v) for v in (
            entry.date, entry.week, entry.title, entry.topic, entry.fmt,
            entry.length, entry.time_slot, entry.views, entry.likes,
            entry.saves, entry.comments)) + " |\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(row)
        return path

    def load_contents(self) -> list[ContentEntry]:
        out = []
        for c in self._table_rows("content_log.md", ncols=11):
            try:
                out.append(ContentEntry(
                    date=c[0], week=int(c[1]), title=c[2], topic=c[3], fmt=c[4],
                    length=c[5], time_slot=c[6], views=int(c[7]), likes=int(c[8]),
                    saves=int(c[9]), comments=int(c[10])))
            except ValueError:
                continue
        return out

    # ---------- decision log (provenance) ----------
    def log_decision(self, entry: DecisionEntry) -> Path:
        path = self.base / "decision_log.md"
        if not path.exists():
            self._write("decision_log.md",
                        "# 의사결정 로그 (provenance: AI/사람 구분)\n\n"
                        + _DECISION_HEADER + "\n" + _DECISION_SEP + "\n")
        row = "| " + " | ".join(_esc(v) for v in (
            entry.timestamp, entry.actor, entry.basis, entry.decision,
            entry.result or "-")) + " |\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(row)
        return path

    def load_decisions(self) -> list[DecisionEntry]:
        out = []
        for c in self._table_rows("decision_log.md", ncols=5):
            try:
                out.append(DecisionEntry(
                    timestamp=c[0], actor=c[1], basis=c[2], decision=c[3],
                    result="" if c[4] == "-" else c[4]))
            except ValueError:
                continue   # unknown actor rows are skipped, not crashed on
        return out

    def decision_counts(self) -> dict:
        counts = {ACTOR_AI: 0, ACTOR_HUMAN: 0}
        for d in self.load_decisions():
            counts[d.actor] = counts.get(d.actor, 0) + 1
        return counts

    # ---------- aggregation (attribution baseline) ----------
    def compare_by(self, variable: str) -> dict:
        """Average views/engagement per value of one experiment variable.

        One variable at a time — mirrors the experiment principle (change one
        variable per week so effects stay attributable)."""
        if variable not in _COMPARABLE_VARS:
            raise ValueError(f"comparable variables: {_COMPARABLE_VARS}, got: {variable}")
        groups: dict = {}
        for e in self.load_contents():
            key = str(getattr(e, variable))
            g = groups.setdefault(key, {"count": 0, "views": 0, "engagement": 0})
            g["count"] += 1
            g["views"] += e.views
            g["engagement"] += e.engagement
        return {
            k: {
                "count": g["count"],
                "avg_views": g["views"] / g["count"],
                "avg_engagement": g["engagement"] / g["count"],
            }
            for k, g in groups.items()
        }

    def weekly_report(self) -> str:
        """Compact Korean summary: KPI trend + decision provenance counts."""
        lines = ["# 측정 요약", ""]
        kpis = self.load_kpis()
        if kpis:
            lines.append("## 주차별 KPI")
            for k in kpis:
                lines.append(f"- Week {k.week}: 팔로워 {k.followers}, "
                             f"콘텐츠 {k.content_count}개, 조회 {k.total_views}, "
                             f"참여 {k.engagement}, 전환 {k.conversions}")
        contents = self.load_contents()
        if contents:
            lines.append("")
            lines.append(f"## 게시물 {len(contents)}건 — 주제별 평균 조회")
            for topic, g in self.compare_by("topic").items():
                lines.append(f"- {topic}: {g['avg_views']:.0f}회 (n={g['count']})")
        counts = self.decision_counts()
        if counts[ACTOR_AI] or counts[ACTOR_HUMAN]:
            lines.append("")
            lines.append(f"## 의사결정 provenance — AI {counts[ACTOR_AI]}건 / "
                         f"사람 {counts[ACTOR_HUMAN]}건")
        return "\n".join(lines) if len(lines) > 2 else "# 측정 요약\n\n기록 없음"

    # ---------- io ----------
    def _write(self, fname: str, content: str) -> Path:
        self.base.mkdir(parents=True, exist_ok=True)
        path = self.base / fname
        path.write_text(content, encoding="utf-8")
        return path

    def _table_rows(self, fname: str, ncols: int) -> list[list[str]]:
        path = self.base / fname
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = _split_row(line)
            if len(cells) != ncols:
                continue
            if cells[0] in ("week", "date", "timestamp") or set(cells[0]) <= {"-"}:
                continue   # header/separator
            rows.append(cells)
        return rows
