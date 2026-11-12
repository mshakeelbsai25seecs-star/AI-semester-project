"""Shared helpers for building scripted tracks."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from game.cells import Cell, CellType
from game.config import GameConfig
from game.core import GameCore


def C(kind: str, has_coin: bool = False) -> Cell:
    return Cell(CellType(kind), has_coin=has_coin)


def row(*kinds: str) -> Tuple[Cell, Cell, Cell]:
    cells = [C(k) for k in kinds]
    while len(cells) < 3:
        cells.append(C("empty"))
    return cells[0], cells[1], cells[2]


def empty_row() -> Tuple[Cell, Cell, Cell]:
    return row("empty", "empty", "empty")


def make_core_with_track(
    rows: Sequence[Tuple[Cell, ...]],
    *,
    config: GameConfig | None = None,
    seed: int = 0,
) -> GameCore:
    core = GameCore(config or GameConfig())
    core.load_scripted_track(list(rows), seed=seed)
    return core


def pad_rows(rows: Iterable[Tuple[Cell, ...]], n: int = 20) -> List[Tuple[Cell, ...]]:
    out = list(rows)
    while len(out) < n:
        out.append(empty_row())
    return out
