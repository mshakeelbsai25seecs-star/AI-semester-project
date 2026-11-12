"""AI agents for Subway Surfers Lite.

Individual agent modules may land on other branches. Import through
``agents.registry`` so the viewer always has Human + Random available.
"""

from agents.registry import AGENT_ORDER, create_agent, list_available_agents

__all__ = [
    "AGENT_ORDER",
    "create_agent",
    "list_available_agents",
]
