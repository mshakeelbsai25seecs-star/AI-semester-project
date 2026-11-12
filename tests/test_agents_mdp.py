"""MDP value-iteration agent."""

from agents import MdpAgent, create_agent
from agents.mdp import encode_state
from game.actions import Action, BodyStatus
from game.config import GameConfig
from game.core import GameCore
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def _fast_mdp(cfg: GameConfig | None = None) -> MdpAgent:
    cfg = cfg or GameConfig(observation_k=3)
    return MdpAgent(
        cfg,
        horizon_rows=1,
        gamma=0.9,
        theta=1e-2,
        max_iterations=25,
        chance_outcomes=8,
        auto_solve=True,
    )


def test_mdp_solve_builds_policy():
    agent = _fast_mdp()
    assert agent.stats.states > 0
    assert agent.policy_size == agent.stats.states
    assert agent.stats.iterations >= 1


def test_mdp_act_on_low_barrier():
    cfg = GameConfig(observation_k=3)
    agent = _fast_mdp(cfg)
    # Trains on both sides → lane change crashes; JUMP is required.
    track = pad_rows([row("train", "low_barrier", "train"), empty_row()])
    core = make_core_with_track(track, config=cfg)
    action = agent.act(core.observe())
    assert action is Action.JUMP


def test_mdp_act_dodges_train():
    cfg = GameConfig(observation_k=3)
    agent = _fast_mdp(cfg)
    track = pad_rows([row("empty", "train", "empty"), empty_row()])
    core = make_core_with_track(track, config=cfg)
    action = agent.act(core.observe())
    assert action in (Action.LEFT, Action.RIGHT)


def test_mdp_plays_without_crash_short_script():
    cfg = GameConfig(observation_k=4)
    agent = _fast_mdp(cfg)
    track = pad_rows(
        [
            row("empty", "low_barrier", "empty"),
            row("empty", "high_barrier", "empty"),
            empty_row(),
            empty_row(),
        ]
    )
    core = make_core_with_track(track, config=cfg)
    obs = core.observe()
    for _ in range(4):
        if core.is_terminal:
            break
        obs, _, _, _ = core.step(agent.act(obs))
    assert not core.state.crashed


def test_mdp_state_encoding_stable():
    cfg = GameConfig()
    core = GameCore(cfg)
    obs = core.reset(0)
    key1 = encode_state(obs.lane, obs.body_status, obs.rows, 1)
    key2 = encode_state(obs.lane, BodyStatus.GROUND, obs.rows, 1)
    assert key1 == key2
    assert key1[0] == obs.lane
    assert key1[1] == BodyStatus.GROUND.value


def test_create_mdp_via_registry():
    cfg = GameConfig()
    agent = create_agent(
        "mdp",
        config=cfg,
        horizon_rows=1,
        max_iterations=15,
        chance_outcomes=6,
        theta=1e-2,
    )
    assert isinstance(agent, MdpAgent)
    assert agent.policy_size > 0
