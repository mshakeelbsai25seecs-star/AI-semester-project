"""Scoring and speed schedule."""

from game.actions import Action
from game.config import GameConfig
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_coin_and_step_rewards():
    cfg = GameConfig()
    track = pad_rows([row("empty", "coin", "empty"), empty_row()])
    core = make_core_with_track(track, config=cfg)

    obs, reward, done, info = core.step(Action.STAY)
    assert not done
    assert info.get("coin_collected")
    assert abs(reward - (cfg.coin_reward + cfg.step_reward)) < 1e-9
    assert core.state.coins == 1
    assert abs(core.state.score - reward) < 1e-9


def test_crash_penalty_no_step_reward():
    cfg = GameConfig()
    track = pad_rows([row("empty", "train", "empty")])
    core = make_core_with_track(track, config=cfg)
    _, reward, done, _ = core.step(Action.STAY)
    assert done
    assert reward == cfg.crash_penalty


def test_speed_increases_every_interval():
    cfg = GameConfig(
        initial_speed=1.0,
        speed_increment=0.05,
        speed_interval_rows=50,
    )
    track = pad_rows([empty_row() for _ in range(55)], n=55)
    core = make_core_with_track(track, config=cfg)
    assert core.state.speed == 1.0

    for _ in range(49):
        core.step(Action.STAY)
    assert abs(core.state.speed - 1.0) < 1e-9

    core.step(Action.STAY)  # distance becomes 50
    assert abs(core.state.speed - 1.05) < 1e-9


def test_terminal_step_is_noop():
    track = pad_rows([row("empty", "train", "empty")])
    core = make_core_with_track(track)
    core.step(Action.STAY)
    assert core.is_terminal
    obs, reward, done, info = core.step(Action.JUMP)
    assert done and reward == 0.0
    assert info.get("already_terminal")
