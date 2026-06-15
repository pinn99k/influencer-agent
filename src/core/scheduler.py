"""Agent Dependency Graph + Parallel Execution Scheduler.

Executes agents in topological waves. Within each wave, agents that have
no dependency on each other run in parallel via ThreadPoolExecutor.

Usage:
    from core.scheduler import AgentScheduler

    scheduler = AgentScheduler(dependencies=DEPENDENCIES, max_workers=2)
    results = scheduler.execute(run_agent_callback, context)
    # results: dict[str, str | Exception]
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

logger = logging.getLogger(__name__)


class AgentScheduler:
    """Topological-wave scheduler for agent dependency graphs.

    Args:
        dependencies: Mapping of agent_name -> list of agent_names it depends on.
                      e.g. {"컨셉기획": ["경쟁분석", "플랫폼추천"]}
        max_workers:  Thread pool size for parallel waves. Ignored when sequential=True.
        sequential:   If True, ignore parallelism — run all agents one by one (debug mode).
    """

    def __init__(
        self,
        dependencies: dict[str, list[str]],
        max_workers: int = 2,
        sequential: bool = False,
    ) -> None:
        self.dependencies = dependencies
        self.max_workers = max_workers
        self.sequential = sequential
        self._waves: list[list[str]] = self._build_waves()

    # ── Public ──────────────────────────────────────────────────────────────

    def execute(
        self,
        run_agent: Callable[[str, dict], str],
        context: dict,
    ) -> dict[str, str | Exception]:
        """Run all agents respecting dependency order.

        Args:
            run_agent: Callback ``(agent_name, context) -> output_str``.
                       The callback is responsible for updating *context* with
                       its result before returning (or the CEO can do it after).
            context:   Shared context dict passed to every agent call.

        Returns:
            Ordered dict mapping agent_name -> output string or Exception on failure.
            Execution stops at the first wave that contains a failure.
        """
        results: dict[str, str | Exception] = {}

        for wave_idx, wave in enumerate(self._waves):
            logger.info(
                "Scheduler wave %d/%d: %s (mode=%s)",
                wave_idx + 1,
                len(self._waves),
                wave,
                "sequential" if self.sequential else "parallel",
            )

            wave_results = self._run_wave(run_agent, context, wave)
            results.update(wave_results)

            # Stop on first failure in this wave
            failures = {
                name: exc
                for name, exc in wave_results.items()
                if isinstance(exc, Exception)
            }
            if failures:
                logger.error(
                    "Scheduler stopping after wave %d — failures: %s",
                    wave_idx + 1,
                    list(failures.keys()),
                )
                break

        return results

    @property
    def waves(self) -> list[list[str]]:
        """Read-only view of the computed execution waves."""
        return [list(w) for w in self._waves]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run_wave(
        self,
        run_agent: Callable[[str, dict], str],
        context: dict,
        wave: list[str],
    ) -> dict[str, str | Exception]:
        """Run a single wave, either sequentially or in parallel."""
        if self.sequential or len(wave) == 1:
            return self._run_wave_sequential(run_agent, context, wave)
        return self._run_wave_parallel(run_agent, context, wave)

    def _run_wave_sequential(
        self,
        run_agent: Callable[[str, dict], str],
        context: dict,
        wave: list[str],
    ) -> dict[str, str | Exception]:
        results: dict[str, str | Exception] = {}
        for name in wave:
            results[name] = self._call_agent(run_agent, name, context)
        return results

    def _run_wave_parallel(
        self,
        run_agent: Callable[[str, dict], str],
        context: dict,
        wave: list[str],
    ) -> dict[str, str | Exception]:
        results: dict[str, str | Exception] = {}
        workers = min(self.max_workers, len(wave))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_name = {
                executor.submit(self._call_agent, run_agent, name, context): name
                for name in wave
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                results[name] = future.result()  # never raises — _call_agent catches

        return results

    @staticmethod
    def _call_agent(
        run_agent: Callable[[str, dict], str],
        name: str,
        context: dict,
    ) -> str | Exception:
        """Invoke run_agent and catch all exceptions so waves don't crash."""
        try:
            return run_agent(name, context)
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent '%s' raised: %s", name, exc, exc_info=True)
            return exc

    # ── Topological sort ────────────────────────────────────────────────────

    def _build_waves(self) -> list[list[str]]:
        """Kahn's algorithm: returns agents grouped into dependency waves.

        Wave N contains every agent whose all dependencies were satisfied in
        waves 0..N-1.  Agents within the same wave are safe to run in parallel.

        Raises:
            ValueError: if the dependency graph contains a cycle.
        """
        all_agents = set(self.dependencies.keys())

        # Validate: every declared dependency must exist in the graph
        for agent, deps in self.dependencies.items():
            for dep in deps:
                if dep not in all_agents:
                    raise ValueError(
                        f"Agent '{agent}' depends on '{dep}', "
                        f"which is not in the dependency graph."
                    )

        # in_degree[node] = number of unresolved dependencies
        in_degree: dict[str, int] = {a: 0 for a in all_agents}
        # successors[node] = agents that depend on node
        successors: dict[str, list[str]] = defaultdict(list)

        for agent, deps in self.dependencies.items():
            in_degree[agent] += len(deps)
            for dep in deps:
                successors[dep].append(agent)

        # Start with agents that have no dependencies
        queue: deque[str] = deque(
            sorted(a for a in all_agents if in_degree[a] == 0)
        )
        waves: list[list[str]] = []
        visited = 0

        while queue:
            # Everything currently in the queue forms one wave
            wave = list(queue)
            queue.clear()
            waves.append(wave)
            visited += len(wave)

            next_wave_candidates: dict[str, int] = {}
            for agent in wave:
                for successor in successors[agent]:
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        next_wave_candidates[successor] = 1

            for candidate in sorted(next_wave_candidates):
                queue.append(candidate)

        if visited != len(all_agents):
            raise ValueError(
                "Cycle detected in the agent dependency graph. "
                f"Agents not scheduled: "
                f"{all_agents - {a for wave in waves for a in wave}}"
            )

        return waves
