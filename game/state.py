"""Mutable runtime game state (owned by GameCore)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game.actions import BodyStatus


@dataclass
class GameState:
    """Full internal state; agents should use Observation instead."""

    lane: int = 1
    body_status: BodyStatus = BodyStatus.GROUND
    jump_timer: int = 0
    roll_timer: int = 0
    distance: int = 0
    coins: int = 0
    score: float = 0.0
    speed: float = 1.0
    seed: int = 42
    terminal: bool = False
    crashed: bool = False
    steps: int = 0
    # Rows already resolved by the runner (exclusive upper bound of current row).
    # Runner sits just before row ``distance``; next cell is row ``distance``.
    info: dict = field(default_factory=dict)
