"""GameCore clone / from_observation helpers used by search agents."""

from game.actions import Action
from game.cells import Cell, CellType
from game.config import GameConfig
from game.core import GameCore
from tests.helpers import empty_row, make_core_with_track, pad_rows, row


def test_clone_is_independent():
    core = GameCore()
    core.reset(5)
    twin = core.clone()
    twin.step(Action.LEFT)
    assert core.state.lane == 1
    assert twin.state.lane == 0


def test_from_observation_replays_visible_rows():
    cfg = GameConfig(observation_k=3)
    track = pad_rows(
        [
            row("empty", "coin", "empty"),
            row("empty", "low_barrier", "empty"),
            empty_row(),
        ]
    )
    live = make_core_with_track(track, config=cfg)
    obs = live.observe()
    sim = GameCore.from_observation(obs, cfg)
    _, reward, done, info = sim.step(Action.STAY)
    assert not done
    assert info.get("coin_collected")
    assert reward > 0
