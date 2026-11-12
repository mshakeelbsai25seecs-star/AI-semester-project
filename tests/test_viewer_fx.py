"""Viewer visual helpers: coin despawn tracking + hop arc (no Panda3D)."""

from game.cells import Cell, CellType
from viewer.fx import CollectedCoins, hop_height


def test_collected_coin_hidden_while_cell_still_in_view():
    track = CollectedCoins()
    ground = Cell(CellType.COIN)
    train = Cell(CellType.TRAIN, has_coin=True)

    assert track.should_draw_coin(3, 1, ground)
    assert track.should_draw_coin(4, 0, train)

    track.mark(3, 1)
    assert not track.should_draw_coin(3, 1, ground)
    # Other cells unaffected
    assert track.should_draw_coin(4, 0, train)

    track.mark(4, 0)
    assert not track.should_draw_coin(4, 0, train)

    track.reset()
    assert track.should_draw_coin(3, 1, ground)


def test_hop_height_peaks_midway():
    assert hop_height(0.0) == 0.0
    assert hop_height(1.0) == 0.0
    mid = hop_height(0.5, peak=1.35)
    assert abs(mid - 1.35) < 1e-9
    assert hop_height(0.25) > 0.5
    assert hop_height(0.75) > 0.5
