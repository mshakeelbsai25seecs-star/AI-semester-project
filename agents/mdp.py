"""Reduced-state MDP agent solved with value iteration."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from game.actions import Action, BodyStatus
from game.agent import Observation
from game.cells import Cell, CellType
from game.config import GameConfig
from game.core import GameCore

from agents.generator_model import CELL_KINDS, iter_row_distribution


# Reduced-state features (documented for the report / viewer):
#   1. lane            — discrete 0 .. num_lanes-1
#   2. body_status     — ground | jumping | rolling | on_train
#   3. near_rows       — cell-type pattern of the nearest ``horizon_rows``
#                        rows (default 1). Timers are folded into body_status
#                        (accurate when jump/roll duration == 1).
# Value iteration solves this finite MDP offline; act() is a table lookup.


CellCode = int
RowCode = Tuple[CellCode, ...]
NearCode = Tuple[RowCode, ...]
StateKey = Tuple[int, str, NearCode]  # lane, body, near row codes


_CELL_TO_CODE = {kind: i for i, kind in enumerate(CELL_KINDS)}
_CODE_TO_CELL = {i: kind for kind, i in _CELL_TO_CODE.items()}


def encode_cell(cell: Cell) -> CellCode:
    return _CELL_TO_CODE.get(cell.type, 0)


def decode_cell(code: CellCode) -> Cell:
    return Cell(_CODE_TO_CELL.get(code, CellType.EMPTY))


def encode_row(row: Sequence[Cell]) -> RowCode:
    return tuple(encode_cell(c) for c in row)


def decode_row(code: RowCode) -> Tuple[Cell, ...]:
    return tuple(decode_cell(c) for c in code)


def encode_state(
    lane: int,
    body: BodyStatus,
    rows: Sequence[Sequence[Cell]],
    horizon_rows: int,
) -> StateKey:
    near = tuple(encode_row(rows[i]) for i in range(min(horizon_rows, len(rows))))
    # Pad with empty rows if observation shorter than horizon (should be rare).
    while len(near) < horizon_rows:
        n = len(rows[0]) if rows else 3
        near = near + (tuple(0 for _ in range(n)),)
    return (lane, body.value, near)


@dataclass
class MdpSolveStats:
    states: int = 0
    iterations: int = 0
    policy_size: int = 0
    residual: float = 0.0


class MdpAgent:
    """Offline value iteration on a reduced MDP; fast policy lookup at play time.

    State features
    --------------
    - ``lane``
    - ``body_status``
    - cell-type pattern of the nearest ``horizon_rows`` (default 1)

    Transitions use ``GameCore`` for the deterministic effect of an action on
    the known near rows, then the generator probability model for the new row
    that slides into the window.
    """

    name = "mdp"

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        *,
        horizon_rows: int = 1,
        gamma: float = 0.95,
        theta: float = 1e-3,
        max_iterations: int = 80,
        chance_outcomes: int = 48,
        seed: int = 0,
        auto_solve: bool = True,
    ) -> None:
        self.config = config or GameConfig()
        self.horizon_rows = max(1, horizon_rows)
        self.gamma = gamma
        self.theta = theta
        self.max_iterations = max_iterations
        self.chance_outcomes = chance_outcomes
        self.seed = seed
        self.values: Dict[StateKey, float] = {}
        self.policy: Dict[StateKey, Action] = {}
        self.stats = MdpSolveStats()
        self._row_dist = iter_row_distribution(
            self.config, max_outcomes=self.chance_outcomes
        )
        self._all_near: List[NearCode] = []
        # Cache deterministic step outcomes: (lane, body, near, action) → ...
        self._det_cache: Dict[
            Tuple[StateKey, Action], Tuple[float, bool, int, BodyStatus]
        ] = {}
        if auto_solve:
            self.solve()

    def reset(self) -> None:
        # Policy is episode-independent; nothing to clear.
        return None

    # ---------------------------------------------------------------- solve

    def solve(self) -> MdpSolveStats:
        """Run value iteration and rebuild the greedy policy."""
        self._all_near = list(self._enumerate_near_patterns())
        states = list(self._enumerate_states())
        self.values = {s: 0.0 for s in states}
        residual = 0.0
        it = 0
        for it in range(1, self.max_iterations + 1):
            residual = 0.0
            for state in states:
                old = self.values[state]
                best = float("-inf")
                for action in Action:
                    best = max(best, self._q_value(state, action))
                self.values[state] = best
                residual = max(residual, abs(old - best))
            if residual < self.theta:
                break

        self.policy = {}
        for state in states:
            best_a = Action.STAY
            best_q = float("-inf")
            for action in Action:
                q = self._q_value(state, action)
                if q > best_q:
                    best_q = q
                    best_a = action
            self.policy[state] = best_a

        self.stats = MdpSolveStats(
            states=len(states),
            iterations=it,
            policy_size=len(self.policy),
            residual=residual,
        )
        return self.stats

    def _enumerate_near_patterns(self) -> Iterable[NearCode]:
        n = self.config.num_lanes
        codes = list(range(len(CELL_KINDS)))
        single_rows = list(itertools.product(codes, repeat=n))
        if self.horizon_rows == 1:
            for row in single_rows:
                yield (row,)
            return
        # horizon >= 2: full product can explode; cap via chance distribution rows.
        # Build from the approximate row bag for tractability.
        bag_rows = [encode_row(r) for _, r in self._row_dist]
        if not bag_rows:
            bag_rows = [tuple(0 for _ in range(n))]
        for combo in itertools.product(bag_rows, repeat=self.horizon_rows):
            yield combo

    def _enumerate_states(self) -> Iterable[StateKey]:
        bodies = [b.value for b in BodyStatus]
        for lane in range(self.config.num_lanes):
            for body in bodies:
                for near in self._all_near:
                    yield (lane, body, near)

    def _q_value(self, state: StateKey, action: Action) -> float:
        total = 0.0
        for prob, reward, nxt, terminal in self._transitions(state, action):
            if terminal:
                total += prob * reward
            else:
                total += prob * (reward + self.gamma * self.values.get(nxt, 0.0))
        return total

    def _deterministic_step(
        self, state: StateKey, action: Action
    ) -> Tuple[float, bool, int, BodyStatus]:
        cached = self._det_cache.get((state, action))
        if cached is not None:
            return cached
        lane, body, near = state
        rows = [decode_row(code) for code in near]
        obs = Observation(
            lane=lane,
            body_status=BodyStatus(body),
            jump_timer=1 if body == BodyStatus.JUMPING.value else 0,
            roll_timer=1 if body == BodyStatus.ROLLING.value else 0,
            speed=self.config.initial_speed,
            distance=0,
            coins=0,
            score=0.0,
            steps=0,
            rows=tuple(rows),
            train_climbing_enabled=self.config.train_climbing_enabled,
            num_lanes=self.config.num_lanes,
        )
        core = GameCore.from_observation(obs, self.config)
        _, reward, done, _ = core.step(action)
        result = (reward, done, core.state.lane, core.state.body_status)
        self._det_cache[(state, action)] = result
        return result

    def _transitions(
        self, state: StateKey, action: Action
    ) -> List[Tuple[float, float, StateKey, bool]]:
        reward, done, new_lane, new_body = self._deterministic_step(state, action)
        if done:
            return [(1.0, reward, state, True)]

        _, _, near = state
        rows = [decode_row(code) for code in near]
        remaining = list(rows[1:])
        out: List[Tuple[float, float, StateKey, bool]] = []
        for prob, new_row in self._row_dist:
            window = remaining + [new_row]
            while len(window) < self.horizon_rows:
                window.append(new_row)
            window = window[: self.horizon_rows]
            nxt = encode_state(new_lane, new_body, window, self.horizon_rows)
            out.append((prob, reward, nxt, False))
        return out

    # ------------------------------------------------------------------ act

    def act(self, observation: Observation) -> Action:
        if observation.terminal or not observation.rows:
            return Action.STAY
        key = encode_state(
            observation.lane,
            observation.body_status,
            observation.rows,
            self.horizon_rows,
        )
        action = self.policy.get(key)
        if action is not None:
            return action
        # Unseen pattern (e.g. train-top coin encoding differences): reactive fallback.
        return self._reactive_fallback(observation)

    @staticmethod
    def _reactive_fallback(obs: Observation) -> Action:
        cell = obs.rows[0][obs.lane]
        if cell.type is CellType.LOW_BARRIER:
            return Action.JUMP
        if cell.type is CellType.HIGH_BARRIER:
            return Action.ROLL
        if cell.is_train:
            if obs.lane > 0:
                return Action.LEFT
            if obs.lane < obs.num_lanes - 1:
                return Action.RIGHT
        return Action.STAY

    @property
    def policy_size(self) -> int:
        return len(self.policy)
