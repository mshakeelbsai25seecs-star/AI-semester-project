"""Crash / clear / climb rules."""

from game.actions import Action, BodyStatus
from game.cells import Cell, CellType
from game.config import GameConfig
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_low_barrier_requires_jump():
    track = pad_rows([row("empty", "low_barrier", "empty")])
    core = make_core_with_track(track)
    assert core.state.lane == 1

    _, reward, done, info = core.step(Action.STAY)
    assert done and core.state.crashed
    assert info["crash_reason"] == "hit_low_barrier"
    assert reward == GameConfig().crash_penalty


def test_low_barrier_cleared_by_jump():
    track = pad_rows([row("empty", "low_barrier", "empty"), empty_row()])
    core = make_core_with_track(track)
    obs, reward, done, info = core.step(Action.JUMP)
    assert not done
    assert info.get("cleared") == "low_barrier"
    assert core.state.body_status is BodyStatus.GROUND  # duration 1 → landed


def test_high_barrier_requires_roll():
    track = pad_rows([row("empty", "high_barrier", "empty")])
    core = make_core_with_track(track)
    _, _, done, info = core.step(Action.STAY)
    assert done
    assert info["crash_reason"] == "hit_high_barrier"


def test_high_barrier_cleared_by_roll():
    track = pad_rows([row("empty", "high_barrier", "empty"), empty_row()])
    core = make_core_with_track(track)
    _, _, done, info = core.step(Action.ROLL)
    assert not done
    assert info.get("cleared") == "high_barrier"


def test_jump_into_high_barrier_crashes():
    track = pad_rows([row("empty", "high_barrier", "empty")])
    core = make_core_with_track(track)
    _, _, done, info = core.step(Action.JUMP)
    assert done
    assert info["crash_reason"] == "jumped_into_high_barrier"


def test_roll_into_low_barrier_crashes():
    track = pad_rows([row("empty", "low_barrier", "empty")])
    core = make_core_with_track(track)
    _, _, done, info = core.step(Action.ROLL)
    assert done
    assert info["crash_reason"] == "rolled_into_low_barrier"


def test_train_front_crash():
    track = pad_rows([row("empty", "train", "empty")])
    core = make_core_with_track(track)
    _, _, done, info = core.step(Action.STAY)
    assert done
    assert info["crash_reason"] == "hit_train"


def test_train_side_via_lane_change_crashes():
    track = pad_rows([row("train", "empty", "empty")])
    core = make_core_with_track(track)  # start mid lane
    _, _, done, info = core.step(Action.LEFT)
    assert done
    assert info["crash_reason"] == "hit_train"


def test_ramp_climb_ride_and_drop():
    # mid lane: ramp, train, train, then low barrier on drop (must jump after drop)
    track = pad_rows(
        [
            row("empty", "train_ramp", "empty"),
            row("empty", "train", "empty"),
            row("empty", "train", "empty"),
            row("empty", "empty", "empty"),
            row("empty", "low_barrier", "empty"),
        ]
    )
    core = make_core_with_track(track)

    _, _, done, info = core.step(Action.STAY)
    assert not done and info.get("climbed_ramp")
    assert core.state.body_status is BodyStatus.ON_TRAIN

    _, _, done, info = core.step(Action.STAY)
    assert not done and core.state.body_status is BodyStatus.ON_TRAIN

    _, _, done, info = core.step(Action.STAY)
    assert not done and core.state.body_status is BodyStatus.ON_TRAIN

    _, _, done, info = core.step(Action.STAY)
    assert not done
    assert info.get("dropped_from_train")
    assert core.state.body_status is BodyStatus.GROUND

    _, _, done, info = core.step(Action.STAY)
    assert done
    assert info["crash_reason"] == "hit_low_barrier"


def test_ramp_with_climbing_disabled_crashes():
    cfg = GameConfig(train_climbing_enabled=False)
    track = pad_rows([row("empty", "train_ramp", "empty")])
    core = make_core_with_track(track, config=cfg)
    _, _, done, info = core.step(Action.STAY)
    assert done
    assert info["crash_reason"] == "hit_train_ramp_climbing_disabled"


def test_lane_bounds_clamped():
    track = pad_rows([empty_row(), empty_row()])
    core = make_core_with_track(track)
    core.step(Action.LEFT)  # mid -> left
    assert core.state.lane == 0
    core.step(Action.LEFT)  # clamp
    assert core.state.lane == 0


def test_coin_on_train_collected_while_riding():
    track = pad_rows(
        [
            (
                Cell(CellType.EMPTY),
                Cell(CellType.TRAIN_RAMP, has_coin=True),
                Cell(CellType.EMPTY),
            ),
            (
                Cell(CellType.EMPTY),
                Cell(CellType.TRAIN, has_coin=True),
                Cell(CellType.EMPTY),
            ),
            empty_row(),
        ]
    )
    core = make_core_with_track(track)
    core.step(Action.STAY)
    assert core.state.coins == 1
    core.step(Action.STAY)
    assert core.state.coins == 2
    assert not core.is_terminal
