"""Smoke vs full experiment presets.

Smoke mode is intentionally tiny (few seeds, short episodes, light agent
kwargs) so CI / ``pytest`` plumbing stays fast. Full mode is the report
default: more seeds, longer caps, and richer search/MDP settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Sequence, Tuple


DEFAULT_AGENTS: Tuple[str, ...] = (
    "random",
    "baseline",
    "lookahead",
    "expectimax",
    "mdp",
)


@dataclass(frozen=True)
class ExperimentPresets:
    """Shared knobs for all E1–E4 runs."""

    mode: str = "full"
    agents: Tuple[str, ...] = DEFAULT_AGENTS
    seeds: Tuple[int, ...] = (42, 43, 44, 45, 46, 47, 48, 49, 50, 51)
    max_steps: int = 400
    observation_k: int = 8
    k_values: Tuple[int, ...] = (2, 4, 6, 8, 12)
    speed_schedules: Tuple[Tuple[str, float, float, int], ...] = (
        ("slow", 1.0, 0.02, 80),
        ("default", 1.0, 0.05, 50),
        ("fast", 1.5, 0.10, 30),
        ("blitz", 2.0, 0.15, 20),
    )
    climb_values: Tuple[bool, ...] = (True, False)
    agent_kwargs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    experiments: Tuple[str, ...] = ("e1", "e2", "e3", "e4")
    results_dir: str = "experiments/results"
    write_plots: bool = True


def _full_agent_kwargs() -> Dict[str, Dict[str, Any]]:
    return {
        "expectimax": {"extra_depth": 2, "chance_outcomes": 16},
        "mdp": {
            "horizon_rows": 1,
            "max_iterations": 40,
            "chance_outcomes": 24,
            "theta": 1e-3,
        },
    }


def _smoke_agent_kwargs() -> Dict[str, Dict[str, Any]]:
    # Keep Expectimax/MDP cheap for CI (no multi-minute sims).
    return {
        "expectimax": {"extra_depth": 0, "chance_outcomes": 2},
        "mdp": {
            "horizon_rows": 1,
            "max_iterations": 5,
            "chance_outcomes": 2,
            "theta": 1e-2,
        },
    }


def full_presets() -> ExperimentPresets:
    return ExperimentPresets(mode="full", agent_kwargs=_full_agent_kwargs())


def smoke_presets() -> ExperimentPresets:
    """Short CI-friendly defaults."""
    return ExperimentPresets(
        mode="smoke",
        seeds=(42, 43),
        max_steps=15,
        observation_k=3,
        k_values=(2, 3),
        speed_schedules=(
            ("default", 1.0, 0.05, 50),
            ("fast", 1.5, 0.10, 30),
        ),
        agent_kwargs=_smoke_agent_kwargs(),
        write_plots=True,
    )


def presets_for_mode(mode: str) -> ExperimentPresets:
    key = (mode or "full").strip().lower()
    if key in {"smoke", "ci", "quick"}:
        return smoke_presets()
    if key in {"full", "default", "report"}:
        return full_presets()
    raise ValueError(f"Unknown experiment mode {mode!r}; use 'smoke' or 'full'")


def with_experiments(
    presets: ExperimentPresets, experiment_ids: Sequence[str]
) -> ExperimentPresets:
    ids = tuple(e.strip().lower() for e in experiment_ids)
    return replace(presets, experiments=ids)


def agent_kwargs_for(presets: ExperimentPresets, agent_name: str) -> Dict[str, Any]:
    return dict(presets.agent_kwargs.get(agent_name, {}))
