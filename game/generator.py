"""Seeded endless track generator. Same seed → same infinite track."""

from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

from game.cells import Cell, CellType
from game.config import GameConfig


Row = Tuple[Cell, ...]


class TrackGenerator:
    """Deterministic, lazily extended multi-lane track.

    Rows are generated in order and cached. After ``reset(seed)``, row ``i``
    is always identical for that seed.
    """

    def __init__(self, config: GameConfig) -> None:
        self.config = config
        self._rng = random.Random()
        self._rows: List[Row] = []
        # Remaining body cells after the already-emitted train head.
        self._train_remaining: List[int] = [0] * config.num_lanes
        self.seed: int | None = None

    def reset(self, seed: int) -> None:
        self.seed = seed
        self._rng.seed(seed)
        self._rows.clear()
        self._train_remaining = [0] * self.config.num_lanes

    def get_row(self, row_index: int) -> Row:
        if row_index < 0:
            raise IndexError("row_index must be >= 0")
        while len(self._rows) <= row_index:
            self._rows.append(self._generate_next_row())
        return self._rows[row_index]

    def get_rows(self, start: int, count: int) -> List[Row]:
        return [self.get_row(start + i) for i in range(count)]

    def load_scripted_rows(self, rows: Sequence[Row], seed: int = 0) -> None:
        """Replace the track with fixed rows (for unit tests).

        After the scripted prefix is exhausted, generation continues from the
        given seed so episodes can still run past the fixture.
        """
        self.reset(seed)
        self._rows = [tuple(row) for row in rows]
        self._train_remaining = [0] * self.config.num_lanes
        # Advance RNG deterministically so later generated rows are stable.
        # (No-op beyond seeding; scripted rows are authoritative for tests.)

    def _generate_next_row(self) -> Row:
        cfg = self.config
        n = cfg.num_lanes
        cells: List[Cell | None] = [None] * n

        for lane in range(n):
            if self._train_remaining[lane] > 0:
                has_coin = self._rng.random() < cfg.p_coin_on_train
                cells[lane] = Cell(CellType.TRAIN, has_coin=has_coin)
                self._train_remaining[lane] -= 1

        free_lanes = [i for i in range(n) if cells[i] is None]
        hard_count = sum(1 for c in cells if c is not None and _is_hard(c))

        for lane in free_lanes:
            cell = self._sample_free_lane_cell(hard_count)
            if cell.type is CellType.TRAIN:
                length = self._rng.randint(cfg.train_min_length, cfg.train_max_length)
                use_ramp = self._rng.random() < cfg.p_train_has_ramp
                head = CellType.TRAIN_RAMP if use_ramp else CellType.TRAIN
                has_coin = self._rng.random() < cfg.p_coin_on_train
                cells[lane] = Cell(head, has_coin=has_coin)
                self._train_remaining[lane] = length - 1
                hard_count += 1
            else:
                cells[lane] = cell
                if _is_hard(cell):
                    hard_count += 1

            if cfg.avoid_triple_hard_block and hard_count >= n and n >= 2:
                cells[lane] = self._safe_fill()
                hard_count = sum(1 for c in cells if c is not None and _is_hard(c))

        return tuple(cells)  # type: ignore[return-value]

    def _sample_free_lane_cell(self, hard_count: int) -> Cell:
        cfg = self.config
        weights = {
            "empty": cfg.p_empty_bias,
            "coin": cfg.p_coin,
            "low": cfg.p_low_barrier,
            "high": cfg.p_high_barrier,
            "train": cfg.p_train_start,
        }
        if hard_count >= cfg.num_lanes - 1 and cfg.avoid_triple_hard_block:
            weights["low"] *= 0.15
            weights["high"] *= 0.15
            weights["train"] *= 0.15
            weights["empty"] += 0.4
            weights["coin"] += 0.2

        choice = self._weighted_choice(weights)
        if choice == "empty":
            return Cell(CellType.EMPTY)
        if choice == "coin":
            return Cell(CellType.COIN)
        if choice == "low":
            return Cell(CellType.LOW_BARRIER)
        if choice == "high":
            return Cell(CellType.HIGH_BARRIER)
        return Cell(CellType.TRAIN)  # placeholder → expanded by caller

    def _safe_fill(self) -> Cell:
        if self._rng.random() < 0.55:
            return Cell(CellType.COIN)
        return Cell(CellType.EMPTY)

    def _weighted_choice(self, weights: Dict[str, float]) -> str:
        total = sum(weights.values())
        r = self._rng.random() * total
        acc = 0.0
        last = next(iter(weights))
        for key, w in weights.items():
            last = key
            acc += w
            if r <= acc:
                return key
        return last


def _is_hard(cell: Cell) -> bool:
    return cell.is_train or cell.type in (CellType.LOW_BARRIER, CellType.HIGH_BARRIER)


def rows_as_types(rows: Sequence[Row]) -> List[Tuple[CellType, ...]]:
    """Helper for tests / debugging."""
    return [tuple(cell.type for cell in row) for row in rows]
