"""Headless game core: rules, scoring, observation."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Sequence, Tuple

from game.actions import Action, BodyStatus
from game.agent import Observation, observation_from_parts
from game.cells import Cell, CellType
from game.config import GameConfig
from game.generator import TrackGenerator
from game.state import GameState


class GameCore:
    """Pure-Python endless runner. No graphics dependency.

    Lifecycle::

        core = GameCore()
        obs = core.reset(seed=42)
        while not core.is_terminal:
            action = agent.act(obs)
            obs, reward, done, info = core.step(action)

    Crash rules (proposal):
    - Low barrier → must be jumping; else crash.
    - High barrier → must be rolling; else crash.
    - Train body / ramp without climb → crash on contact from ground/jump/roll.
    - Train ramp with climbing enabled → climb, ride until train ends, then drop.
    - Coins collected when the cell is entered safely (ground or train top).
    """

    def __init__(self, config: Optional[GameConfig] = None) -> None:
        self.config = config or GameConfig()
        self.config.validate()
        self.generator = TrackGenerator(self.config)
        self.state = GameState()
        self._initialized = False

    # ------------------------------------------------------------------ API

    def reset(self, seed: Optional[int] = None) -> Observation:
        """Start a new episode. Same seed → same track and outcomes."""
        seed = self.config.default_seed if seed is None else seed
        self.config.validate()
        self.generator = TrackGenerator(self.config)
        self.generator.reset(seed)
        self.state = GameState(
            lane=self.config.start_lane,
            body_status=BodyStatus.GROUND,
            jump_timer=0,
            roll_timer=0,
            distance=0,
            coins=0,
            score=0.0,
            speed=self.config.initial_speed,
            seed=seed,
            terminal=False,
            crashed=False,
            steps=0,
            info={},
        )
        self._initialized = True
        return self.observe()

    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        """Apply one action, advance one row, return (obs, reward, done, info)."""
        if not self._initialized:
            raise RuntimeError("Call reset() before step()")
        if self.state.terminal:
            obs = self.observe()
            return obs, 0.0, True, {"already_terminal": True}

        if not isinstance(action, Action):
            action = Action(action)

        info: Dict[str, Any] = {"action": action.value}
        reward = 0.0

        # 1) Horizontal move / posture change (before entering the next row).
        self._apply_action(action, info)

        # 2) Advance one row into the chosen lane.
        next_row_index = self.state.distance
        row = self.generator.get_row(next_row_index)
        cell = row[self.state.lane]
        info["cell"] = cell.type.value
        info["row"] = next_row_index

        # 3) Resolve collision / climbing / coin pickup.
        crashed, coin_delta = self._resolve_cell(cell, info)
        if coin_delta:
            self.state.coins += coin_delta
            reward += coin_delta * self.config.coin_reward
            info["coin_collected"] = True

        self.state.distance += 1
        self.state.steps += 1
        self.state.speed = self._speed_at(self.state.distance)

        # 4) Tick jump/roll timers after the step's collision check.
        self._tick_posture()

        if crashed:
            self.state.crashed = True
            self.state.terminal = True
            reward += self.config.crash_penalty
            info["crash"] = True
            info["crash_reason"] = info.get("crash_reason", "collision")
        else:
            reward += self.config.step_reward
            info["crash"] = False

        self.state.score += reward
        self.state.info = info
        obs = self.observe()
        return obs, reward, self.state.terminal, info

    def observe(self, k: Optional[int] = None) -> Observation:
        """Return the next ``k`` rows (default: ``config.observation_k``)."""
        if not self._initialized:
            raise RuntimeError("Call reset() before observe()")
        k = self.config.observation_k if k is None else k
        if k < 1:
            raise ValueError("k must be >= 1")
        rows = self.generator.get_rows(self.state.distance, k)
        return observation_from_parts(
            lane=self.state.lane,
            body_status=self.state.body_status,
            jump_timer=self.state.jump_timer,
            roll_timer=self.state.roll_timer,
            speed=self.state.speed,
            distance=self.state.distance,
            coins=self.state.coins,
            score=self.state.score,
            steps=self.state.steps,
            rows=rows,
            config=self.config,
            terminal=self.state.terminal,
            crashed=self.state.crashed,
        )

    @property
    def is_terminal(self) -> bool:
        return self.state.terminal

    def load_scripted_track(self, rows, seed: int = 0) -> Observation:
        """Reset onto a fixed track prefix (testing helper)."""
        obs = self.reset(seed=seed)
        self.generator.load_scripted_rows(rows, seed=seed)
        return self.observe()

    def clone(self) -> "GameCore":
        """Deep copy for search / planning without touching the live episode."""
        if not self._initialized:
            raise RuntimeError("Call reset() before clone()")
        twin = GameCore(self.config)
        twin.generator = copy.deepcopy(self.generator)
        twin.state = copy.deepcopy(self.state)
        twin._initialized = True
        return twin

    def apply_observation_state(self, obs: Observation) -> None:
        """Copy runner fields from an observation onto this core (track unchanged)."""
        if not self._initialized:
            raise RuntimeError("Call reset() before apply_observation_state()")
        self.state.lane = obs.lane
        self.state.body_status = obs.body_status
        self.state.jump_timer = obs.jump_timer
        self.state.roll_timer = obs.roll_timer
        self.state.speed = obs.speed
        self.state.distance = obs.distance
        self.state.coins = obs.coins
        self.state.score = obs.score
        self.state.steps = obs.steps
        self.state.terminal = obs.terminal
        self.state.crashed = obs.crashed

    @classmethod
    def from_observation(
        cls,
        obs: Observation,
        config: Optional[GameConfig] = None,
        *,
        future_rows: Sequence[Tuple[Cell, ...]] = (),
        seed: int = 0,
    ) -> "GameCore":
        """Fork a simulator whose row 0 is ``obs.rows[0]``.

        Visible rows (plus optional ``future_rows`` for Expectimax) are loaded as
        a scripted prefix. Runner posture matches ``obs``, but ``distance`` is
        reset to 0 so planning indexes the scripted window from the start.
        Coins/score/steps start at 0 for relative planning rewards.
        """
        cfg = config or GameConfig(
            num_lanes=obs.num_lanes,
            observation_k=max(obs.k, 1),
            train_climbing_enabled=obs.train_climbing_enabled,
        )
        # Preserve timing / reward knobs when a full config is provided.
        core = cls(cfg)
        rows: List[Tuple[Cell, ...]] = list(obs.rows) + list(future_rows)
        if not rows:
            rows = [
                tuple(Cell(CellType.EMPTY) for _ in range(cfg.num_lanes))
            ]
        core.load_scripted_track(rows, seed=seed)
        core.state.lane = obs.lane
        core.state.body_status = obs.body_status
        core.state.jump_timer = obs.jump_timer
        core.state.roll_timer = obs.roll_timer
        core.state.speed = obs.speed
        core.state.distance = 0
        core.state.coins = 0
        core.state.score = 0.0
        core.state.steps = 0
        core.state.terminal = obs.terminal
        core.state.crashed = obs.crashed
        core.state.seed = seed
        return core

    # ------------------------------------------------------------- mechanics

    def _speed_at(self, distance: int) -> float:
        cfg = self.config
        levels = distance // cfg.speed_interval_rows
        return cfg.initial_speed + levels * cfg.speed_increment

    def _apply_action(self, action: Action, info: Dict[str, Any]) -> None:
        st = self.state
        cfg = self.config

        if action is Action.LEFT:
            if st.lane > 0:
                st.lane -= 1
            info["lane_change"] = "left"
        elif action is Action.RIGHT:
            if st.lane < cfg.num_lanes - 1:
                st.lane += 1
            info["lane_change"] = "right"
        elif action is Action.JUMP:
            if st.body_status is BodyStatus.ON_TRAIN:
                # Jumping while riding keeps you on the train (no mid-air drop).
                info["ignored"] = "jump_on_train"
            elif st.body_status in (BodyStatus.GROUND, BodyStatus.ROLLING):
                st.body_status = BodyStatus.JUMPING
                st.jump_timer = cfg.jump_duration
                st.roll_timer = 0
                info["started"] = "jump"
        elif action is Action.ROLL:
            if st.body_status is BodyStatus.ON_TRAIN:
                info["ignored"] = "roll_on_train"
            elif st.body_status in (BodyStatus.GROUND, BodyStatus.JUMPING):
                st.body_status = BodyStatus.ROLLING
                st.roll_timer = cfg.roll_duration
                st.jump_timer = 0
                info["started"] = "roll"
        else:
            info["lane_change"] = "stay"

    def _tick_posture(self) -> None:
        st = self.state
        if st.body_status is BodyStatus.JUMPING:
            st.jump_timer -= 1
            if st.jump_timer <= 0:
                st.jump_timer = 0
                st.body_status = BodyStatus.GROUND
        elif st.body_status is BodyStatus.ROLLING:
            st.roll_timer -= 1
            if st.roll_timer <= 0:
                st.roll_timer = 0
                st.body_status = BodyStatus.GROUND

    def _resolve_cell(self, cell: Cell, info: Dict[str, Any]) -> Tuple[bool, int]:
        """Return (crashed, coins_gained)."""
        st = self.state

        if st.body_status is BodyStatus.ON_TRAIN:
            return self._resolve_on_train(cell, info)

        if st.body_status is BodyStatus.JUMPING:
            return self._resolve_jumping(cell, info)

        if st.body_status is BodyStatus.ROLLING:
            return self._resolve_rolling(cell, info)

        return self._resolve_ground(cell, info)

    def _resolve_on_train(self, cell: Cell, info: Dict[str, Any]) -> Tuple[bool, int]:
        if cell.is_train:
            coins = 1 if cell.has_coin else 0
            info["on_train"] = True
            return False, coins
        # Train ended → drop onto whatever occupies this cell.
        self.state.body_status = BodyStatus.GROUND
        info["dropped_from_train"] = True
        return self._resolve_ground(cell, info)

    def _resolve_jumping(self, cell: Cell, info: Dict[str, Any]) -> Tuple[bool, int]:
        if cell.is_train:
            info["crash_reason"] = "jumped_into_train"
            return True, 0
        if cell.type is CellType.HIGH_BARRIER:
            info["crash_reason"] = "jumped_into_high_barrier"
            return True, 0
        if cell.type is CellType.LOW_BARRIER:
            info["cleared"] = "low_barrier"
            return False, 0
        return False, (1 if cell.has_coin or cell.type is CellType.COIN else 0)

    def _resolve_rolling(self, cell: Cell, info: Dict[str, Any]) -> Tuple[bool, int]:
        if cell.is_train:
            info["crash_reason"] = "rolled_into_train"
            return True, 0
        if cell.type is CellType.LOW_BARRIER:
            info["crash_reason"] = "rolled_into_low_barrier"
            return True, 0
        if cell.type is CellType.HIGH_BARRIER:
            info["cleared"] = "high_barrier"
            return False, 0
        return False, (1 if cell.has_coin or cell.type is CellType.COIN else 0)

    def _resolve_ground(self, cell: Cell, info: Dict[str, Any]) -> Tuple[bool, int]:
        if cell.type is CellType.TRAIN_RAMP:
            if self.config.train_climbing_enabled:
                self.state.body_status = BodyStatus.ON_TRAIN
                self.state.jump_timer = 0
                self.state.roll_timer = 0
                info["climbed_ramp"] = True
                coins = 1 if cell.has_coin else 0
                return False, coins
            info["crash_reason"] = "hit_train_ramp_climbing_disabled"
            return True, 0

        if cell.type is CellType.TRAIN:
            info["crash_reason"] = "hit_train"
            return True, 0

        if cell.type is CellType.LOW_BARRIER:
            info["crash_reason"] = "hit_low_barrier"
            return True, 0

        if cell.type is CellType.HIGH_BARRIER:
            info["crash_reason"] = "hit_high_barrier"
            return True, 0

        return False, (1 if cell.has_coin or cell.type is CellType.COIN else 0)
