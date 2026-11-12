"""Random + baseline agent behaviour."""

from agents import BaselineAgent, RandomAgent, create_agent, list_agents
from game.actions import Action
from game.agent import Agent
from game.cells import Cell, CellType
from game.config import GameConfig
from game.core import GameCore
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_registry_lists_all_five():
    names = list_agents()
    assert names == ["random", "baseline", "lookahead", "expectimax", "mdp"]


def test_create_agent_factory():
    cfg = GameConfig()
    for name in ("random", "baseline", "lookahead"):
        agent = create_agent(name, config=cfg, seed=1)
        assert isinstance(agent, Agent)


def test_random_agent_is_seeded_and_varies():
    a = RandomAgent(seed=0)
    b = RandomAgent(seed=0)
    c = RandomAgent(seed=1)
    core = GameCore()
    obs = core.reset(42)
    seq_a = [a.act(obs) for _ in range(20)]
    seq_b = [b.act(obs) for _ in range(20)]
    c.reset(1)
    seq_c = [c.act(obs) for _ in range(20)]
    assert seq_a == seq_b
    assert seq_a != seq_c


def test_baseline_jumps_low_barrier():
    track = pad_rows([row("empty", "low_barrier", "empty")])
    core = make_core_with_track(track)
    obs = core.observe()
    assert BaselineAgent().act(obs) is Action.JUMP


def test_baseline_rolls_high_barrier():
    track = pad_rows([row("empty", "high_barrier", "empty")])
    core = make_core_with_track(track)
    assert BaselineAgent().act(core.observe()) is Action.ROLL


def test_baseline_dodges_train():
    track = pad_rows([row("empty", "train", "empty")])
    core = make_core_with_track(track)
    action = BaselineAgent().act(core.observe())
    assert action in (Action.LEFT, Action.RIGHT)


def test_baseline_chases_neighbour_coin():
    track = pad_rows([row("coin", "empty", "empty")])
    core = make_core_with_track(track)
    assert BaselineAgent().act(core.observe()) is Action.LEFT


def test_baseline_survives_scripted_barriers():
    track = pad_rows(
        [
            row("empty", "low_barrier", "empty"),
            row("empty", "high_barrier", "empty"),
            empty_row(),
        ]
    )
    core = make_core_with_track(track)
    agent = BaselineAgent()
    obs = core.observe()
    for _ in range(3):
        if core.is_terminal:
            break
        obs, _, done, _ = core.step(agent.act(obs))
    assert not core.state.crashed or core.state.distance >= 2
