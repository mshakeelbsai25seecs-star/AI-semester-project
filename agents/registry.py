"""Viewer / experiment agent selection API.

Canonical names (experiments + ``create_agent``): ``random``, ``baseline``,
``lookahead``, ``expectimax``, ``mdp``. The viewer also accepts ``human`` and
capitalized aliases (``Human``, ``Lookahead``, …).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type

from game.actions import Action
from game.agent import Agent, Observation
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

# Viewer menu order (human first, then the five AI players).
AGENT_ORDER: Tuple[str, ...] = ("human",) + AGENT_NAMES

_DISPLAY_NAMES: Dict[str, str] = {
    "human": "Human",
    "random": "Random",
    "baseline": "Baseline",
    "lookahead": "Lookahead",
    "expectimax": "Expectimax",
    "mdp": "MDP",
}

_ALIASES: Dict[str, str] = {
    "human": "human",
    "random": "random",
    "baseline": "baseline",
    "lookahead": "lookahead",
    "expectimax": "expectimax",
    "mdp": "mdp",
    # Capitalized / UI labels
    "Human": "human",
    "Random": "random",
    "Baseline": "baseline",
    "Lookahead": "lookahead",
    "Expectimax": "expectimax",
    "MDP": "mdp",
    "Mdp": "mdp",
}


class HumanAgent:
    """Placeholder; the viewer supplies keyboard actions instead of ``act``."""

    name = "human"

    def reset(self, *args: Any, **kwargs: Any) -> None:
        return None

    def act(self, observation: Observation) -> Action:
        del observation
        return Action.STAY


_REGISTRY: Dict[str, Type] = {
    "human": HumanAgent,
    "random": RandomAgent,
    "baseline": BaselineAgent,
    "lookahead": LookaheadAgent,
    "expectimax": ExpectimaxAgent,
    "mdp": MdpAgent,
}


def normalize_agent_name(name: str) -> str:
    """Map UI / alias strings to canonical lowercase keys."""
    key = _ALIASES.get(name)
    if key is not None:
        return key
    lowered = name.strip().lower()
    if lowered in _REGISTRY:
        return lowered
    raise KeyError(
        f"Unknown agent {name!r}; choose from {list_available_agents()} "
        f"(or AI-only {list_agents()})"
    )


def display_name(name: str) -> str:
    """Pretty label for HUD / menus."""
    key = normalize_agent_name(name)
    return _DISPLAY_NAMES.get(key, key.title())


def list_agents() -> List[str]:
    """AI agent keys for experiments (excludes human)."""
    return list(AGENT_NAMES)


def list_available_agents() -> List[str]:
    """Viewer-facing keys that can be constructed (includes ``human``)."""
    return [name for name in AGENT_ORDER if name in _REGISTRY]


def list_all_agent_slots() -> List[Tuple[str, bool]]:
    """Planned viewer slots with availability flag."""
    return [(name, name in _REGISTRY) for name in AGENT_ORDER]


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
        agent = create_agent("human")
        agent = create_agent("Human")  # alias OK
    """
    key = normalize_agent_name(name)
    cls = _REGISTRY[key]
    cfg = config or GameConfig()

    if key == "human":
        return cls(**kwargs) if kwargs else cls()
    if key == "random":
        return cls(seed=seed, **kwargs)
    if key == "baseline":
        return cls(**kwargs)
    if key == "mdp":
        return cls(config=cfg, seed=seed, **kwargs)
    return cls(config=cfg, **kwargs)


def refresh_registry() -> None:
    """No-op kept for viewer compatibility (imports are eager now)."""
    return None
