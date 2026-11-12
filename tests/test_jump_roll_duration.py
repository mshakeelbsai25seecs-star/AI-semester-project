"""Jump / roll duration config."""

from game.actions import Action, BodyStatus
from game.config import GameConfig
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_jump_duration_two_steps():
    cfg = GameConfig(jump_duration=2)
    track = pad_rows(
        [
            row("empty", "low_barrier", "empty"),
            row("empty", "low_barrier", "empty"),
            row("empty", "low_barrier", "empty"),
        ]
    )
    core = make_core_with_track(track, config=cfg)

    _, _, done, _ = core.step(Action.JUMP)
    assert not done
    assert core.state.body_status is BodyStatus.JUMPING
    assert core.state.jump_timer == 1

    _, _, done, _ = core.step(Action.STAY)
    assert not done
    assert core.state.body_status is BodyStatus.GROUND

    _, _, done, info = core.step(Action.STAY)
    assert done
    assert info["crash_reason"] == "hit_low_barrier"


def test_roll_duration_two_steps():
    cfg = GameConfig(roll_duration=2)
    track = pad_rows(
        [
            row("empty", "high_barrier", "empty"),
            row("empty", "high_barrier", "empty"),
            empty_row(),
        ]
    )
    core = make_core_with_track(track, config=cfg)
    core.step(Action.ROLL)
    assert core.state.body_status is BodyStatus.ROLLING
    core.step(Action.STAY)
    assert core.state.body_status is BodyStatus.GROUND
