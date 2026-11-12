"""Tunable game defaults (UI / experiments may override)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    """All headless-core parameters with proposal / build-plan defaults."""

    num_lanes: int = 3
    observation_k: int = 8
    jump_duration: int = 1
    roll_duration: int = 1
    coin_reward: float = 1.0
    step_reward: float = 0.01
    crash_penalty: float = -100.0
    initial_speed: float = 1.0
    speed_increment: float = 0.05
    speed_interval_rows: int = 50
    default_seed: int = 42
    train_climbing_enabled: bool = True
    # Track generator probabilities / shapes (seeded RNG still decides).
    p_empty_bias: float = 0.35
    p_coin: float = 0.22
    p_low_barrier: float = 0.14
    p_high_barrier: float = 0.12
    p_train_start: float = 0.10
    train_min_length: int = 3
    train_max_length: int = 8
    p_train_has_ramp: float = 0.55
    p_coin_on_train: float = 0.25
    # Soft safety: avoid filling every lane with hard blocks too often.
    avoid_triple_hard_block: bool = True
    # Mid lane index when num_lanes == 3.
    start_lane: int = 1

    def validate(self) -> None:
        if self.num_lanes < 1:
            raise ValueError("num_lanes must be >= 1")
        if not (0 <= self.start_lane < self.num_lanes):
            raise ValueError("start_lane out of range")
        if self.observation_k < 1:
            raise ValueError("observation_k must be >= 1")
        if self.jump_duration < 1 or self.roll_duration < 1:
            raise ValueError("jump/roll duration must be >= 1")
        if self.train_min_length < 1 or self.train_max_length < self.train_min_length:
            raise ValueError("invalid train length range")
        if self.speed_interval_rows < 1:
            raise ValueError("speed_interval_rows must be >= 1")


DEFAULT_CONFIG = GameConfig()
