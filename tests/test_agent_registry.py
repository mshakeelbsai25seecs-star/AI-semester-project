"""Agent registry fallbacks (no Panda3D required)."""

from agents.registry import (
    AGENT_ORDER,
    create_agent,
    list_all_agent_slots,
    list_available_agents,
)
from game.actions import Action
from game.core import GameCore


def test_human_and_random_always_available():
    available = list_available_agents()
    assert "Human" in available
    assert "Random" in available


def test_planned_slots_listed():
    slots = dict(list_all_agent_slots())
    for name in AGENT_ORDER:
        assert name in slots


def test_create_human_and_random():
    human = create_agent("Human")
    random_agent = create_agent("Random")
    core = GameCore()
    obs = core.reset(seed=1)
    assert isinstance(human.act(obs), Action)
    assert isinstance(random_agent.act(obs), Action)


def test_missing_agent_raises():
    try:
        create_agent("DefinitelyMissingAgent")
        assert False, "expected KeyError"
    except KeyError:
        pass
