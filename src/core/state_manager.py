import datetime

from core.file_manager import FileManager


class CEOStateManager:
    """CEO 상태 초기화/갱신/저장 전담. SRP: 상태 관리만."""

    def __init__(self, file_manager: FileManager):
        self._fm = file_manager
        self.state: dict = {}

    def init_state(self, subject_name: str) -> None:
        self.state = {
            "subject": subject_name,
            "current_phase": "전략수립",
            "current_agent": "없음",
            "completed_agents": [],
            "retry_count": 0,
            "started_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._fm.save_state(self.state)

    def update(self, key: str, value) -> None:
        self.state[key] = value
        self._fm.save_state(self.state)

    def update_agent(self, agent_name: str, status: str) -> None:
        self.state["current_agent"] = agent_name
        self.state["agent_status"] = status
        if status == "DONE":
            completed = self.state.get("completed_agents", [])
            if agent_name not in completed:
                completed.append(agent_name)
            self.state["completed_agents"] = completed
        self._fm.save_state(self.state)

    def assert_initialized(self) -> None:
        if not self.state:
            raise RuntimeError("state not initialized. Call init_state() first.")

    @property
    def current_phase(self) -> str:
        return self.state.get("current_phase", "")
