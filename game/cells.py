"""Track cell types and cell values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CellType(Enum):
    """Contents of one lane cell on the track."""

    EMPTY = "empty"
    COIN = "coin"
    LOW_BARRIER = "low_barrier"
    HIGH_BARRIER = "high_barrier"
    TRAIN = "train"
    TRAIN_RAMP = "train_ramp"


@dataclass(frozen=True)
class Cell:
    """One lane cell.

    Ground coins use ``CellType.COIN``. Coins on top of trains use
    ``CellType.TRAIN`` / ``TRAIN_RAMP`` with ``has_coin=True``.
    """

    type: CellType
    has_coin: bool = False

    def __post_init__(self) -> None:
        if self.type is CellType.COIN and not self.has_coin:
            object.__setattr__(self, "has_coin", True)

    @property
    def is_train(self) -> bool:
        return self.type in (CellType.TRAIN, CellType.TRAIN_RAMP)

    @property
    def is_empty_ground(self) -> bool:
        return self.type in (CellType.EMPTY, CellType.COIN)
