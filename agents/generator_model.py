"""Approximate track-row distribution for Expectimax / MDP (config probs only)."""

from __future__ import annotations

import itertools
import random
from typing import Dict, Iterable, List, Sequence, Tuple

from game.cells import Cell, CellType
from game.config import GameConfig

Row = Tuple[Cell, ...]

# Discrete cell kinds used in chance models (ignore train-top coins for sparsity).
CELL_KINDS: Tuple[CellType, ...] = (
    CellType.EMPTY,
    CellType.COIN,
    CellType.LOW_BARRIER,
    CellType.HIGH_BARRIER,
    CellType.TRAIN,
    CellType.TRAIN_RAMP,
)


def cell_kind_weights(config: GameConfig) -> Dict[CellType, float]:
    """Per-lane categorical weights mirroring ``TrackGenerator`` free-lane mix."""
    return {
        CellType.EMPTY: config.p_empty_bias,
        CellType.COIN: config.p_coin,
        CellType.LOW_BARRIER: config.p_low_barrier,
        CellType.HIGH_BARRIER: config.p_high_barrier,
        # Split train-start mass between body and ramp.
        CellType.TRAIN: config.p_train_start * (1.0 - config.p_train_has_ramp),
        CellType.TRAIN_RAMP: config.p_train_start * config.p_train_has_ramp,
    }


def normalize(weights: Dict[CellType, float]) -> Dict[CellType, float]:
    total = sum(weights.values())
    if total <= 0:
        n = len(weights)
        return {k: 1.0 / n for k in weights}
    return {k: v / total for k, v in weights.items()}


def sample_cell(rng: random.Random, config: GameConfig) -> Cell:
    weights = normalize(cell_kind_weights(config))
    r = rng.random()
    acc = 0.0
    last = CellType.EMPTY
    for kind, w in weights.items():
        last = kind
        acc += w
        if r <= acc:
            return Cell(kind)
    return Cell(last)


def sample_row(rng: random.Random, config: GameConfig) -> Row:
    cells = [sample_cell(rng, config) for _ in range(config.num_lanes)]
    if config.avoid_triple_hard_block and config.num_lanes >= 2:
        if all(_is_hard(c) for c in cells):
            cells[-1] = Cell(CellType.EMPTY if rng.random() < 0.5 else CellType.COIN)
    return tuple(cells)


def _is_hard(cell: Cell) -> bool:
    return cell.is_train or cell.type in (CellType.LOW_BARRIER, CellType.HIGH_BARRIER)


def iter_row_distribution(
    config: GameConfig,
    *,
    max_outcomes: int = 64,
) -> List[Tuple[float, Row]]:
    """Enumerate (approx) independent per-lane outcomes, pruned to ``max_outcomes``.

    Used by Expectimax chance nodes and MDP transition estimates. When the full
    6**num_lanes grid is larger than ``max_outcomes``, outcomes are sampled with
    replacement from the categorical model and renormalized.
    """
    weights = normalize(cell_kind_weights(config))
    kinds = list(weights.keys())
    n = config.num_lanes
    full = len(kinds) ** n
    if full <= max_outcomes:
        out: List[Tuple[float, Row]] = []
        for combo in itertools.product(kinds, repeat=n):
            p = 1.0
            for k in combo:
                p *= weights[k]
            row = tuple(Cell(k) for k in combo)
            if config.avoid_triple_hard_block and all(_is_hard(c) for c in row):
                continue
            out.append((p, row))
        total = sum(p for p, _ in out) or 1.0
        return [(p / total, row) for p, row in out]

    rng = random.Random(0)
    bag: Dict[Row, float] = {}
    for _ in range(max_outcomes):
        row = sample_row(rng, config)
        bag[row] = bag.get(row, 0.0) + 1.0
    total = sum(bag.values())
    return [(c / total, row) for row, c in bag.items()]


def encode_cell(cell: Cell) -> str:
    if cell.has_coin and cell.is_train:
        return f"{cell.type.value}+coin"
    return cell.type.value


def encode_row(row: Sequence[Cell]) -> Tuple[str, ...]:
    return tuple(encode_cell(c) for c in row)
