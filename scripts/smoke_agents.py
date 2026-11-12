"""Light smoke: run a short seeded episode with each registered agent.

Usage (repo root)::

    python scripts/smoke_agents.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import create_agent, list_agents
from game import GameConfig, GameCore


def run_one(name: str, steps: int = 40, seed: int = 42) -> None:
    cfg = GameConfig(observation_k=6)
    kwargs = {}
    if name == "expectimax":
        kwargs = {"extra_depth": 1, "chance_outcomes": 8}
    if name == "mdp":
        kwargs = {
            "horizon_rows": 1,
            "max_iterations": 20,
            "chance_outcomes": 8,
            "theta": 1e-2,
        }
    agent = create_agent(name, config=cfg, seed=0, **kwargs)
    core = GameCore(cfg)
    obs = core.reset(seed)
    for _ in range(steps):
        if core.is_terminal:
            break
        obs, _, _, _ = core.step(agent.act(obs))
    print(
        f"{name:10s}  steps={core.state.steps:3d}  coins={core.state.coins:3d}  "
        f"score={core.state.score:7.2f}  crashed={core.state.crashed}"
    )


def main() -> None:
    print("Smoke episodes (seed=42, max 40 steps):")
    for name in list_agents():
        run_one(name)


if __name__ == "__main__":
    main()
