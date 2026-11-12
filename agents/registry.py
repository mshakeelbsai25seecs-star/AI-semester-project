"""Viewer / experiment agent selection API."""

from __future__ import annotations

from typing import Any, Dict, List, Type

from game.agent import Agent
from game.config import GameConfig

from agents.baseline import BaselineAgent
from agents.expectimax import ExpectimaxAgent
from agents.lookahead import LookaheadAgent
from agents.mdp import MdpAgent
from agents.random_agent import RandomAgent

AGENT_NAMES = (
    "random",
    "baseline",
    "lookahead",
    "expectimax",
    "mdp",
)

_REGISTRY: Dict[str, Type] = {
    "random": RandomAgent,
    "baseline": BaselineAgent,
    "lookahead": LookaheadAgent,
    "expectimax": ExpectimaxAgent,
    "mdp": MdpAgent,
}


def list_agents() -> List[str]:
    return list(AGENT_NAMES)


def create_agent(
    name: str,
    *,
    config: GameConfig | None = None,
    seed: int = 0,
    **kwargs: Any,
) -> Agent:
    """Build an agent by registry name (for UI / experiments).

    Examples::

        agent = create_agent("lookahead", config=cfg)
        agent = create_agent("mdp", config=cfg, horizon=2)
    """
    key = name.strip().lower()
    if key not in _REGISTRY:
        raise KeyError(f"Unknown agent {name!r}; choose from {list_agents()}")
    cls = _REGISTRY[key]
    cfg = config or GameConfig()
    if key == "random":
        return cls(seed=seed, **kwargs)
    if key == "baseline":
        return cls(**kwargs)
    if key == "mdp":
        return cls(config=cfg, seed=seed, **kwargs)
    return cls(config=cfg, **kwargs)
