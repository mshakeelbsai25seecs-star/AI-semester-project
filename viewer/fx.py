"""Pure visual helpers (no Panda3D) for coin despawn + jump hop."""

from __future__ import annotations

import math
from typing import Set, Tuple

from game.cells import Cell, CellType


CellKey = Tuple[int, int]


class CollectedCoins:
    """Track world cells whose coin was already awarded by the core."""

    def __init__(self) -> None:
        self._keys: Set[CellKey] = set()

    def reset(self) -> None:
        self._keys.clear()

    def mark(self, row: int, lane: int) -> None:
        self._keys.add((int(row), int(lane)))

    def __contains__(self, key: CellKey) -> bool:
        return key in self._keys

    def should_draw_coin(self, row: int, lane: int, cell: Cell) -> bool:
        """True if this cell still has a visible coin mesh."""
        if (int(row), int(lane)) in self._keys:
            return False
        if cell.type is CellType.COIN:
            return True
        return bool(cell.has_coin)


def hop_height(progress: float, peak: float = 1.35) -> float:
    """Smooth up-then-down hop. ``progress`` in [0, 1] → height ≥ 0."""
    t = max(0.0, min(1.0, float(progress)))
    if t <= 0.0 or t >= 1.0:
        return 0.0
    return float(peak) * math.sin(math.pi * t)
