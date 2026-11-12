"""Lookahead and Expectimax agents."""

from agents import ExpectimaxAgent, LookaheadAgent, create_agent
from game.actions import Action
from game.config import GameConfig
from game.core import GameCore
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_lookahead_jumps_imminent_low_barrier():
    cfg = GameConfig(observation_k=4)
    # Side lanes blocked by trains → only JUMP clears the mid low barrier.
    track = pad_rows(
        [row("train", "low_barrier", "train"), empty_row(), empty_row()]
    )
    core = make_core_with_track(track, config=cfg)
    agent = LookaheadAgent(cfg)
    action = agent.act(core.observe())
    assert action is Action.JUMP
    assert agent.nodes_expanded > 0


def test_lookahead_avoids_train_front():
    cfg = GameConfig(observation_k=4)
    track = pad_rows([row("empty", "train", "empty"), empty_row()])
    core = make_core_with_track(track, config=cfg)
    action = LookaheadAgent(cfg).act(core.observe())
    assert action in (Action.LEFT, Action.RIGHT)


def test_lookahead_survives_visible_window():
    cfg = GameConfig(observation_k=5, jump_duration=1, roll_duration=1)
    track = pad_rows(
        [
            row("empty", "low_barrier", "empty"),
            row("empty", "high_barrier", "empty"),
            row("train", "empty", "empty"),
            empty_row(),
            empty_row(),
        ]
    )
    core = make_core_with_track(track, config=cfg)
    agent = LookaheadAgent(cfg)
    obs = core.observe()
    for _ in range(5):
        if core.is_terminal:
            break
        obs, _, _, _ = core.step(agent.act(obs))
    assert not core.state.crashed


def test_lookahead_exposes_plan_metrics():
    cfg = GameConfig(observation_k=3)
    core = make_core_with_track(pad_rows([empty_row(), empty_row(), empty_row()]), config=cfg)
    agent = LookaheadAgent(cfg)
    agent.act(core.observe())
    assert isinstance(agent.last_plan, list)
    assert agent.nodes_expanded >= 1


def test_expectimax_returns_valid_action():
    cfg = GameConfig(observation_k=3)
    core = GameCore(cfg)
    obs = core.reset(7)
    agent = ExpectimaxAgent(cfg, extra_depth=1, chance_outcomes=8)
    action = agent.act(obs)
    assert isinstance(action, Action)
    assert agent.nodes_expanded > 0


def test_expectimax_prefers_safe_over_crash():
    cfg = GameConfig(observation_k=2)
    track = pad_rows([row("empty", "train", "empty"), empty_row()])
    core = make_core_with_track(track, config=cfg)
    agent = ExpectimaxAgent(cfg, extra_depth=0, chance_outcomes=6)
    action = agent.act(core.observe())
    assert action in (Action.LEFT, Action.RIGHT, Action.STAY)
    # STAY would crash; search should dodge when a free lane exists.
    assert action != Action.STAY


def test_create_search_agents_via_registry():
    cfg = GameConfig(observation_k=2)
    la = create_agent("lookahead", config=cfg)
    ex = create_agent("expectimax", config=cfg, extra_depth=1, chance_outcomes=6)
    core = GameCore(cfg)
    obs = core.reset(1)
    assert isinstance(la.act(obs), Action)
    assert isinstance(ex.act(obs), Action)
