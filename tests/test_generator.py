"""Seeded track generator tests."""

from game.cells import CellType
from game.config import GameConfig
from game.generator import TrackGenerator, rows_as_types


def test_same_seed_same_track():
    cfg = GameConfig()
    a = TrackGenerator(cfg)
    b = TrackGenerator(cfg)
    a.reset(42)
    b.reset(42)
    rows_a = a.get_rows(0, 100)
    rows_b = b.get_rows(0, 100)
    assert rows_as_types(rows_a) == rows_as_types(rows_b)
    assert rows_a == rows_b


def test_different_seeds_diverge():
    cfg = GameConfig()
    a = TrackGenerator(cfg)
    b = TrackGenerator(cfg)
    a.reset(1)
    b.reset(2)
    assert a.get_rows(0, 40) != b.get_rows(0, 40)


def test_lazy_extension_is_stable():
    cfg = GameConfig()
    gen = TrackGenerator(cfg)
    gen.reset(7)
    first = gen.get_row(0)
    later = gen.get_rows(0, 25)
    assert later[0] == first
    assert gen.get_row(0) == first


def test_rows_have_three_lanes():
    gen = TrackGenerator(GameConfig())
    gen.reset(0)
    for row in gen.get_rows(0, 30):
        assert len(row) == 3
        for cell in row:
            assert isinstance(cell.type, CellType)


def test_scripted_rows_override_prefix():
    from game.cells import Cell

    gen = TrackGenerator(GameConfig())
    scripted = [
        (Cell(CellType.EMPTY), Cell(CellType.COIN), Cell(CellType.EMPTY)),
        (Cell(CellType.LOW_BARRIER), Cell(CellType.EMPTY), Cell(CellType.EMPTY)),
    ]
    gen.load_scripted_rows(scripted, seed=99)
    assert gen.get_row(0)[1].type is CellType.COIN
    assert gen.get_row(1)[0].type is CellType.LOW_BARRIER
