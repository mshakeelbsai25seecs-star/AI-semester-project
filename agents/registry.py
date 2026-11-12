"""Thin agent registry with graceful import fallbacks.

Human and Random always work. Baseline / Lookahead / Expectimax / MDP are
wired when their modules exist on disk; otherwise they appear unavailable.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from game.actions import Action
from game.agent import Observation, RandomAgent

AgentFactory = Callable[[], object]

AGENT_ORDER: Tuple[str, ...] = (
    "Human",
    "Random",
    "Baseline",
    "Lookahead",
    "Expectimax",
    "MDP",
)


class HumanAgent:
    """Placeholder; the viewer supplies keyboard actions instead."""

    name = "Human"

    def reset(self) -> None:
        return None

    def act(self, observation: Observation) -> Action:
        del observation
        return Action.STAY


def _try_import_factory(module_path: str, attr: str) -> Optional[AgentFactory]:
    try:
        module = __import__(module_path, fromlist=[attr])
    except ImportError:
        return None
    cls = getattr(module, attr, None)
    if cls is None:
        return None

    def factory() -> object:
        try:
            return cls()
        except TypeError:
            # Some agents may require seed/config; try common kwargs.
            try:
                return cls(seed=0)
            except TypeError:
                return cls(config=None)

    return factory


def _build_registry() -> Dict[str, Optional[AgentFactory]]:
    registry: Dict[str, Optional[AgentFactory]] = {
        "Human": HumanAgent,
        "Random": lambda: RandomAgent(seed=0),
        "Baseline": None,
        "Lookahead": None,
        "Expectimax": None,
        "MDP": None,
    }

    # Prefer package modules; also accept flat names if teammates land them early.
    candidates = {
        "Baseline": [
            ("agents.baseline", "BaselineAgent"),
            ("agents.baseline_agent", "BaselineAgent"),
            ("game.agent", "BaselineAgent"),
        ],
        "Lookahead": [
            ("agents.lookahead", "LookaheadAgent"),
            ("agents.lookahead_agent", "LookaheadAgent"),
        ],
        "Expectimax": [
            ("agents.expectimax", "ExpectimaxAgent"),
            ("agents.expectimax_agent", "ExpectimaxAgent"),
        ],
        "MDP": [
            ("agents.mdp", "MDPAgent"),
            ("agents.mdp_agent", "MDPAgent"),
        ],
    }
    for name, paths in candidates.items():
        for module_path, attr in paths:
            factory = _try_import_factory(module_path, attr)
            if factory is not None:
                registry[name] = factory
                break
    return registry


_REGISTRY = _build_registry()


def list_available_agents() -> List[str]:
    """Names that can be constructed right now (includes Human)."""
    return [name for name in AGENT_ORDER if _REGISTRY.get(name) is not None]


def list_all_agent_slots() -> List[Tuple[str, bool]]:
    """All planned modes with availability flag."""
    return [(name, _REGISTRY.get(name) is not None) for name in AGENT_ORDER]


def create_agent(name: str):
    """Construct an agent by UI name. Raises KeyError if unknown/unavailable."""
    factory = _REGISTRY.get(name)
    if factory is None:
        available = ", ".join(list_available_agents())
        raise KeyError(f"Agent {name!r} is not available yet. Available: {available}")
    agent = factory()
    if hasattr(agent, "reset"):
        agent.reset()
    return agent


def refresh_registry() -> None:
    """Re-scan imports (useful after agents land without restarting Python)."""
    global _REGISTRY
    _REGISTRY = _build_registry()
