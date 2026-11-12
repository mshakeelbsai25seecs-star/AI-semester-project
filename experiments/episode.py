"""Single-episode evaluation with seeded metrics."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from agents import create_agent
from game import GameConfig, GameCore


@dataclass
class EpisodeResult:
    """One seeded episode outcome (proposal metrics)."""

    experiment: str
    agent: str
    seed: int
    survival_steps: int
    coins: int
    score: float
    crashed: bool
    decisions: int
    nodes_expanded_total: int
    nodes_expanded_mean: float
    nodes_expanded_max: int
    decision_time_total_s: float
    decision_time_mean_s: float
    memory_or_policy_size: float
    observation_k: int
    initial_speed: float
    speed_increment: float
    speed_interval_rows: int
    train_climbing_enabled: bool
    max_steps: int
    mode: str = "full"
    label: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> Dict[str, Any]:
        row = asdict(self)
        for key in ("speed_schedule", "climb", "variant"):
            if key in self.extra and key not in row:
                row[key] = self.extra[key]
        row["extra"] = ";".join(f"{k}={v}" for k, v in sorted(self.extra.items()))
        return row


def _memory_or_policy_size(agent: Any) -> float:
    """Spatial-cost proxy: MDP policy size, else 0 for non-table agents."""
    stats = getattr(agent, "stats", None)
    if stats is not None:
        policy_size = getattr(stats, "policy_size", None)
        if policy_size is not None:
            return float(policy_size)
        states = getattr(stats, "states", None)
        if states is not None:
            return float(states)
    policy = getattr(agent, "policy", None)
    if isinstance(policy, dict):
        return float(len(policy))
    return 0.0


def run_episode(
    agent_name: str,
    *,
    seed: int,
    config: Optional[GameConfig] = None,
    max_steps: int = 400,
    experiment: str = "",
    mode: str = "full",
    label: str = "",
    agent_seed: int = 0,
    agent_kwargs: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> EpisodeResult:
    """Run one seeded episode and collect proposal metrics."""
    cfg = config or GameConfig()
    kwargs = dict(agent_kwargs or {})
    agent = create_agent(agent_name, config=cfg, seed=agent_seed, **kwargs)
    if hasattr(agent, "reset"):
        agent.reset()

    core = GameCore(cfg)
    obs = core.reset(seed=seed)

    nodes_total = 0
    nodes_max = 0
    time_total = 0.0
    decisions = 0
    policy_size = _memory_or_policy_size(agent)

    while not core.is_terminal and core.state.steps < max_steps:
        t0 = time.perf_counter()
        action = agent.act(obs)
        dt = time.perf_counter() - t0
        time_total += dt
        decisions += 1

        nodes = int(getattr(agent, "nodes_expanded", 0) or 0)
        nodes_total += nodes
        if nodes > nodes_max:
            nodes_max = nodes

        obs, _reward, _done, _info = core.step(action)

    policy_size = max(policy_size, _memory_or_policy_size(agent))

    return EpisodeResult(
        experiment=experiment,
        agent=agent_name,
        seed=seed,
        survival_steps=int(core.state.steps),
        coins=int(core.state.coins),
        score=float(core.state.score),
        crashed=bool(core.state.crashed),
        decisions=decisions,
        nodes_expanded_total=nodes_total,
        nodes_expanded_mean=(nodes_total / decisions) if decisions else 0.0,
        nodes_expanded_max=nodes_max,
        decision_time_total_s=time_total,
        decision_time_mean_s=(time_total / decisions) if decisions else 0.0,
        memory_or_policy_size=policy_size,
        observation_k=int(cfg.observation_k),
        initial_speed=float(cfg.initial_speed),
        speed_increment=float(cfg.speed_increment),
        speed_interval_rows=int(cfg.speed_interval_rows),
        train_climbing_enabled=bool(cfg.train_climbing_enabled),
        max_steps=max_steps,
        mode=mode,
        label=label,
        extra=dict(extra or {}),
    )
