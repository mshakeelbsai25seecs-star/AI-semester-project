"""Observation window and Agent protocol."""

from agents import RandomAgent
from game.actions import Action
from game.agent import Agent, Observation
from game.config import GameConfig
from game.core import GameCore
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_observe_returns_k_rows():
    core = GameCore()
    obs = core.reset(seed=42)
    assert isinstance(obs, Observation)
    assert obs.k == 8
    assert len(obs.rows) == 8
    assert obs.lane == 1
    assert obs.distance == 0
    assert obs.terminal is False


def test_observe_custom_k():
    core = GameCore()
    core.reset(seed=1)
    obs = core.observe(k=3)
    assert obs.k == 3


def test_observation_advances_with_steps():
    track = pad_rows(
        [
            row("empty", "coin", "empty"),
            row("empty", "empty", "coin"),
            empty_row(),
            empty_row(),
        ]
    )
    core = make_core_with_track(track)
    first = core.observe(k=2)
    assert first.rows[0][1].type.value == "coin"
    core.step(Action.STAY)
    second = core.observe(k=2)
    assert second.distance == 1
    assert second.rows[0][2].type.value == "coin"


def test_seeded_episode_reproducible_with_same_actions():
    def run(seed: int):
        core = GameCore()
        core.reset(seed)
        rewards = []
        for _ in range(30):
            if core.is_terminal:
                break
            _, r, done, _ = core.step(Action.STAY)
            rewards.append((r, done, core.state.lane, core.state.coins, core.state.distance))
        return rewards

    assert run(42) == run(42)
    a = GameCore()
    b = GameCore()
    a.reset(42)
    b.reset(99)
    assert a.observe(k=20).rows != b.observe(k=20).rows


def test_random_agent_satisfies_protocol():
    agent: Agent = RandomAgent(seed=0)
    agent.reset()
    core = GameCore()
    obs = core.reset(seed=3)
    action = agent.act(obs)
    assert isinstance(action, Action)


def test_reset_required_before_step():
    core = GameCore()
    try:
        core.step(Action.STAY)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
