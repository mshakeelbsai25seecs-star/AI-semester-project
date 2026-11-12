"""Unified agent registry (viewer helpers + experiment API)."""

from agents.registry import (
    AGENT_ORDER,
    create_agent,
    display_name,
    list_agents,
    list_all_agent_slots,
    list_available_agents,
)
from game.actions import Action
from game.config import GameConfig
from game.core import GameCore


def test_list_agents_excludes_human():
    assert list_agents() == [
        "random",
        "baseline",
        "lookahead",
        "expectimax",
        "mdp",
    ]


def test_human_and_all_ai_available():
    available = list_available_agents()
    assert available[0] == "human"
    for name in list_agents():
        assert name in available


def test_planned_slots_listed():
    slots = dict(list_all_agent_slots())
    for name in AGENT_ORDER:
        assert name in slots
        assert slots[name] is True


def test_create_human_and_random_aliases():
    human = create_agent("Human")
    random_agent = create_agent("Random", seed=0)
    core = GameCore()
    obs = core.reset(seed=1)
    assert isinstance(human.act(obs), Action)
    assert isinstance(random_agent.act(obs), Action)
    assert display_name("mdp") == "MDP"


def test_create_lookahead_canonical_api():
    cfg = GameConfig()
    agent = create_agent("lookahead", config=cfg)
    core = GameCore(cfg)
    obs = core.reset(seed=2)
    assert isinstance(agent.act(obs), Action)


def test_missing_agent_raises():
    try:
        create_agent("DefinitelyMissingAgent")
        assert False, "expected KeyError"
    except KeyError:
        pass
