from pathlib import Path
import json
import re
import datetime

from core.config import OUTPUTS_DIR


class FileManager:
    def __init__(self, influencer_name: str):
        self.name = self._sanitize_name(influencer_name)
        self.base = OUTPUTS_DIR / self.name
        self._ensure_dirs()

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Allow Korean, alphanumeric, underscore, hyphen only."""
        sanitized = re.sub(r"[^\w가-힯ㄱ-ㅣ-]", "_", name)
        sanitized = sanitized.strip("_.")
        if not sanitized:
            raise ValueError(f"Invalid influencer name: {name!r}")
        return sanitized

    # ── public API ──

    def save_output(self, prefix: str, agent_name: str, content: str) -> Path:
        """산출물/ 저장. 덮어쓰기 전 .versions/ 백업. prefix는 에이전트의 output_prefix."""
        path = self.base / "산출물" / f"{prefix}_{agent_name}.md"
        self._versioned_write(path, content)
        return path

    def save_raw(self, agent_name: str, content: str) -> None:
        path = self.base / ".system" / "agents" / agent_name / "raw_output.md"
        self._versioned_write(path, content)

    def save_validation(self, agent_name: str, result) -> None:
        path = self.base / ".system" / "agents" / agent_name / "validation.md"
        lines = [
            f"# 검증 결과 — {agent_name}",
            f"통과: {'PASS' if result.passed else 'FAIL'}",
            f"재시도 필요: {result.retry_required}",
        ]
        if result.failed_rules:
            lines.append("\n## 실패 규칙")
            lines.extend(f"- {r}" for r in result.failed_rules)
        path.write_text("\n".join(lines), encoding="utf-8")

    def save_rework(self, agent_name: str, instruction: str) -> None:
        path = self.base / ".system" / "agents" / agent_name / "rework.md"
        path.write_text(instruction, encoding="utf-8")

    def save_state(self, state: dict) -> None:
        path = self.base / ".system" / "ceo" / "state.md"
        lines = ["# CEO 상태", f"updated: {_now()}", ""]
        for k, v in state.items():
            lines.append(f"**{k}:** {v}")
        path.write_text("\n".join(lines), encoding="utf-8")

    def save_plan(self, content: str) -> None:
        path = self.base / ".system" / "ceo" / "plan.md"
        path.write_text(content, encoding="utf-8")

    def save_progress(self, content: str) -> None:
        # Progress checklist lives separately so it never overwrites the
        # strategic plan.md produced by CEO._interpret_goal.
        path = self.base / ".system" / "ceo" / "progress.md"
        path.write_text(content, encoding="utf-8")

    def save_final_report(self, content: str) -> None:
        path = self.base / "산출물" / "최종리포트.md"
        self._versioned_write(path, content)

    def load_final_report(self) -> str | None:
        """최종리포트.md 로드. 없으면 None."""
        path = self.base / "산출물" / "최종리포트.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def save_briefing(self, condition_no: int, content: str) -> None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")
        bdir = self.base / ".system" / "briefings"
        path = bdir / f"briefing_{ts}_조건{condition_no}.md"
        n = 1
        while path.exists():  # 같은 마이크로초 충돌 방지
            path = bdir / f"briefing_{ts}_조건{condition_no}_{n}.md"
            n += 1
        path.write_text(content, encoding="utf-8")

    def save_manager_output(self, filename: str, content: str) -> Path:
        """매니저 산출물을 .system/manager/ 에 저장한다."""
        mdir = self.base / ".system" / "manager"
        mdir.mkdir(parents=True, exist_ok=True)
        path = mdir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def load_manager_outputs(self) -> list[dict]:
        """매니저 산출물(.system/manager/*.md)을 알림 형태로 복원한다.

        라이브 SSE 이벤트가 아니면 매니저 패널이 비므로 디스크에서 복원한다.
        파일명 접두사로 종류(kind)와 주차(week)를 추론한다. 완료 요약은
        디스크에 저장되지 않으므로 복원 대상이 아니다."""
        mdir = self.base / ".system" / "manager"
        if not mdir.exists():
            return []
        notes = []
        for p in sorted(mdir.glob("*.md")):
            stem = p.stem
            if stem.startswith("weekly_card"):
                kind = "weekly_card"
            elif stem.startswith("performance_request"):
                kind = "performance_request"
            elif stem.startswith("progress_report"):
                kind = "progress"
            else:
                kind = "info"
            m = re.search(r"week(\d+)", stem)
            week = int(m.group(1)) if m else None
            try:
                mtime = datetime.datetime.fromtimestamp(
                    p.stat().st_mtime).strftime("%H:%M:%S")
            except OSError:
                mtime = ""
            notes.append({
                "kind": kind, "week": week,
                "content": p.read_text(encoding="utf-8"), "t": mtime,
            })
        return notes

    def save_prompt_output(self, name: str, content: str) -> None:
        """Spiral 0-A 전용 — .system/prompts/ 에 프롬프트 파일 저장."""
        path = self.base / ".system" / "prompts" / f"{name}.md"
        path.write_text(content, encoding="utf-8")

    def save_performance_record(self, data: str) -> Path:
        """outputs/{name}/성과기록.md 저장 (덮어쓰기, 버전 백업)."""
        path = self.base / "성과기록.md"
        self._versioned_write(path, data)
        return path

    def load_performance_record(self) -> str | None:
        """성과기록.md 로드. 파일 없으면 None 반환."""
        path = self.base / "성과기록.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def init_performance_record(self, start_date: str | None = None) -> Path:
        """성과기록.md 초기 템플릿 생성. 이미 존재하면 기존 파일 경로 반환."""
        path = self.base / "성과기록.md"
        if path.exists():
            return path
        if start_date is None:
            start_date = datetime.datetime.now().strftime("%Y-%m-%d")
        template = (
            f"# 성과 기록\n"
            f"**대상자:** {self.name}\n"
            f"**시작일:** {start_date}\n"
            f"\n"
            f"## 주차별 성과\n"
            f"\n"
            f"### Week 1\n"
            f"- 팔로워: \n"
            f"- 게시물 수: \n"
            f"- 총 조회수: \n"
            f"- 최고 조회수 콘텐츠: \n"
            f"- 참여율: \n"
            f"\n"
            f"### Week 2\n"
            f"- 팔로워: \n"
            f"- 게시물 수: \n"
            f"- 총 조회수: \n"
            f"- 최고 조회수 콘텐츠: \n"
            f"- 참여율: \n"
            f"\n"
            f"### Week 3\n"
            f"- 팔로워: \n"
            f"- 게시물 수: \n"
            f"- 총 조회수: \n"
            f"- 최고 조회수 콘텐츠: \n"
            f"- 참여율: \n"
            f"\n"
            f"### Week 4\n"
            f"- 팔로워: \n"
            f"- 게시물 수: \n"
            f"- 총 조회수: \n"
            f"- 최고 조회수 콘텐츠: \n"
            f"- 참여율: \n"
            f"\n"
            f"## 핑구 메모\n"
            f"- \n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template, encoding="utf-8")
        return path

    def load_feedback(self) -> str | None:
        """피드백.md 로드. 파일 없으면 None."""
        path = self.base / "피드백.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def append_chat_message(self, role: str, content: str) -> Path:
        """CEO 채팅 턴 1개를 .system/chat_history.jsonl에 추가 (영속)."""
        import json as _json
        path = self.base / ".system" / "chat_history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(_json.dumps({"role": role, "content": content},
                                ensure_ascii=False) + "\n")
        return path

    def load_chat_history(self) -> list:
        """채팅 히스토리 로드. [{'role', 'content'}, ...]. 없으면 []."""
        import json as _json
        path = self.base / ".system" / "chat_history.jsonl"
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                m = _json.loads(line)
                if isinstance(m, dict) and "role" in m and "content" in m:
                    out.append({"role": m["role"], "content": m["content"]})
            except ValueError:
                continue
        return out

    def save_direction(self, content: str) -> Path:
        """방향.md 저장 (덮어쓰기). 사용자가 정한 전략 방향."""
        path = self.base / "방향.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def load_direction(self) -> str | None:
        """방향.md 로드. 파일 없으면 None."""
        path = self.base / "방향.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def save_feedback(self, content: str) -> Path:
        """피드백.md 저장 (덮어쓰기)."""
        path = self.base / "피드백.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def init_feedback_template(self) -> Path:
        """피드백.md 초기 템플릿 생성. 이미 존재하면 기존 경로 반환."""
        path = self.base / "피드백.md"
        if path.exists():
            return path
        template = (
            "# 피드백\n"
            f"**대상자:** {self.name}\n\n"
            "## 수정 요청\n"
            "아래에 수정하고 싶은 내용을 자유롭게 작성하세요.\n\n"
            "예시:\n"
            "- 컨셉 A 대신 컨셉 B로 진행하고 싶음\n"
            "- 플랫폼을 유트브 위주로 변경\n"
            "- 캘린더에 '미용사 일상' 주제 추가\n"
            "- 경쟁자 OOO도 분석에 포함\n\n"
            "### 내 피드백\n"
            "- \n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template, encoding="utf-8")
        return path

    def load_existing_outputs(self) -> dict[str, str]:
        """산출물/ 폴더에서 기존 산출물 4개를 로드."""
        output_dir = self.base / "산출물"
        mapping = {
            "01_대상분석.md": "대상_분석",
            "02_경쟁분석.md": "경쟁_분석",
            "03_플랫폼추천.md": "플랫폼_추천",
            "04_컨셉기획.md": "컨셉_기획",
        }
        results = {}
        for fname, ctx_key in mapping.items():
            path = output_dir / fname
            if path.exists():
                results[ctx_key] = path.read_text(encoding="utf-8")
        return results

    def save_handover(self, content: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d")
        path = self.base / "인수인계" / f"인수인계_{ts}.md"
        path.write_text(content, encoding="utf-8")

    def save_snapshot(self) -> None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snap_dir = self.base / ".system" / "ceo" / "snapshots" / ts
        snap_dir.mkdir(parents=True, exist_ok=True)
        for fname in ("plan.md", "state.md"):
            src = self.base / ".system" / "ceo" / fname
            if src.exists():
                (snap_dir / fname).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    def append_log(self, event: dict) -> None:
        """logs/{날짜}.jsonl — Spiral 3 SSE 연동용."""
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        path = self.base / ".system" / "logs" / f"{date_str}.jsonl"
        event["timestamp"] = _now()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # ── private ──

    def _versioned_write(self, path: Path, content: str) -> None:
        """덮어쓰기 전 .versions/v{N} 백업 후 저장."""
        if path.exists():
            versions_dir = path.parent / ".versions"
            versions_dir.mkdir(exist_ok=True)
            existing = list(versions_dir.glob(f"{path.stem}_v*.md"))
            next_v = len(existing) + 1
            backup = versions_dir / f"{path.stem}_v{next_v}.md"
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _ensure_dirs(self) -> None:
        dirs = [
            self.base / "산출물" / ".versions",
            self.base / "인수인계",
            self.base / ".system" / "ceo" / "snapshots",
            self.base / ".system" / "agents",
            self.base / ".system" / "briefings",
            self.base / ".system" / "prompts",
            self.base / ".system" / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
