"""A*-style lookahead over the visible K rows."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from game.actions import Action
from game.agent import Observation
from game.cells import CellType
from game.config import GameConfig
from game.core import GameCore


@dataclass(frozen=True)
class _SearchKey:
    lane: int
    body: str
    jump_timer: int
    roll_timer: int
    depth: int


class LookaheadAgent:
    """Best-first (A*) search through the observed window.

    Maximises estimated return inside the visible K rows using ``GameCore``
    clones for transitions (no duplicated crash rules). The heuristic never
    overestimates remaining return: remaining step rewards + all still-visible
    coins (optimistic).

    ``nodes_expanded`` is updated every ``act`` call for metrics / UI.
    """

    name = "lookahead"

    def __init__(self, config: Optional[GameConfig] = None) -> None:
        self.config = config or GameConfig()
        self.nodes_expanded: int = 0
        self.last_plan: List[Action] = []
        self.last_value: float = 0.0

    def reset(self) -> None:
        self.nodes_expanded = 0
        self.last_plan = []
        self.last_value = 0.0

    def act(self, observation: Observation) -> Action:
        self.nodes_expanded = 0
        self.last_plan = []
        self.last_value = 0.0
        if observation.terminal or not observation.rows:
            return Action.STAY

        action, plan, value = self._search(observation)
        self.last_plan = plan
        self.last_value = value
        return action

    def _search(self, obs: Observation) -> Tuple[Action, List[Action], float]:
        horizon = obs.k
        # Max-heap via negated f; tie-break by insertion order.
        counter = 0
        # entry: (-f, -g, counter, action_seq, core_clone)
        root = GameCore.from_observation(obs, self.config)
        start_g = 0.0
        start_h = self._heuristic(root, horizon)
        heap: List[Tuple[float, float, int, Tuple[Action, ...], GameCore]] = []
        heapq.heappush(heap, (-(start_g + start_h), -start_g, counter, tuple(), root))
        counter += 1

        best_safe: Optional[Tuple[float, Tuple[Action, ...]]] = None
        best_any: Optional[Tuple[float, Tuple[Action, ...]]] = None
        visited: Dict[_SearchKey, float] = {}

        while heap:
            neg_f, neg_g, _, path, core = heapq.heappop(heap)
            g = -neg_g
            self.nodes_expanded += 1

            key = _SearchKey(
                lane=core.state.lane,
                body=core.state.body_status.value,
                jump_timer=core.state.jump_timer,
                roll_timer=core.state.roll_timer,
                depth=core.state.distance,
            )
            prev = visited.get(key)
            if prev is not None and prev >= g:
                continue
            visited[key] = g

            if best_any is None or g > best_any[0]:
                best_any = (g, path)

            if core.state.terminal:
                continue

            if core.state.distance >= horizon:
                if best_safe is None or g > best_safe[0]:
                    best_safe = (g, path)
                continue

            for action in Action:
                twin = core.clone()
                _, reward, done, _ = twin.step(action)
                new_g = g + reward
                if done and twin.state.crashed:
                    # Record crash path quality but do not expand further.
                    if best_any is None or new_g > best_any[0]:
                        best_any = (new_g, path + (action,))
                    continue
                h = self._heuristic(twin, horizon)
                counter += 1
                heapq.heappush(
                    heap,
                    (-(new_g + h), -new_g, counter, path + (action,), twin),
                )

            # Soft cap to keep UI responsive on large K.
            if self.nodes_expanded > 50_000:
                break

        chosen = best_safe if best_safe is not None else best_any
        if not chosen or not chosen[1]:
            return Action.STAY, [], chosen[0] if chosen else 0.0
        plan = list(chosen[1])
        return plan[0], plan, chosen[0]

    def _heuristic(self, core: GameCore, horizon: int) -> float:
        """Admissible-ish optimistic remaining return inside the window."""
        remaining = max(0, horizon - core.state.distance)
        if remaining == 0 or core.state.terminal:
            return 0.0
        cfg = self.config
        # Optimistic: survive all remaining rows and collect every visible coin.
        step_part = remaining * cfg.step_reward
        coin_part = 0.0
        start = core.state.distance
        for offset in range(remaining):
            row = core.generator.get_row(start + offset)
            for cell in row:
                if cell.type is CellType.COIN or cell.has_coin:
                    coin_part += cfg.coin_reward
        return step_part + coin_part
