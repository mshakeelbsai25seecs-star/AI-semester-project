"""AI players for Subway Surfers Lite (use ``game`` for all rules)."""

from agents.baseline import BaselineAgent
from agents.expectimax import ExpectimaxAgent
from agents.lookahead import LookaheadAgent
from agents.mdp import MdpAgent
from agents.random_agent import RandomAgent
from agents.registry import (
    AGENT_NAMES,
    AGENT_ORDER,
    HumanAgent,
    create_agent,
    display_name,
    list_agents,
    list_all_agent_slots,
    list_available_agents,
    normalize_agent_name,
    refresh_registry,
)

__all__ = [
    "AGENT_NAMES",
    "AGENT_ORDER",
    "BaselineAgent",
    "ExpectimaxAgent",
    "HumanAgent",
    "LookaheadAgent",
    "MdpAgent",
    "RandomAgent",
    "create_agent",
    "display_name",
    "list_agents",
    "list_all_agent_slots",
    "list_available_agents",
    "normalize_agent_name",
    "refresh_registry",
]
