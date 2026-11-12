"""Expectimax agent with chance nodes beyond the visible window."""

from __future__ import annotations

from typing import List, Optional, Tuple

from game.actions import Action
from game.agent import Observation
from game.cells import Cell, CellType
from game.config import GameConfig
from game.core import GameCore

from agents.generator_model import iter_row_distribution


class ExpectimaxAgent:
    """Expectimax over visible rows, then chance nodes for unseen rows.

    - Max nodes: pick the action with the best expected value.
    - Chance nodes: average over approximate generator row outcomes.
    - At the depth limit, use a static evaluation of the remaining visible
      coins / posture.

    Uses ``GameCore`` clones for every deterministic transition.
    """

    name = "expectimax"

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        *,
        extra_depth: int = 2,
        chance_outcomes: int = 24,
        eval_coin_weight: float = 0.5,
    ) -> None:
        self.config = config or GameConfig()
        self.extra_depth = max(0, extra_depth)
        self.chance_outcomes = max(1, chance_outcomes)
        self.eval_coin_weight = eval_coin_weight
        self.nodes_expanded: int = 0
        self.last_value: float = 0.0
        self._chance_rows: List[Tuple[float, Tuple[Cell, ...]]] = []

    def reset(self) -> None:
        self.nodes_expanded = 0
        self.last_value = 0.0
        self._chance_rows = []

    def act(self, observation: Observation) -> Action:
        self.nodes_expanded = 0
        self.last_value = 0.0
        if observation.terminal or not observation.rows:
            return Action.STAY

        self._chance_rows = iter_row_distribution(
            self.config, max_outcomes=self.chance_outcomes
        )
        depth_limit = observation.k + self.extra_depth
        best_action = Action.STAY
        best_value = float("-inf")

        root = GameCore.from_observation(observation, self.config)
        for action in Action:
            twin = root.clone()
            _, reward, done, _ = twin.step(action)
            self.nodes_expanded += 1
            if done:
                value = reward
            else:
                value = reward + self._expectimax(twin, depth_limit)
            if value > best_value:
                best_value = value
                best_action = action

        self.last_value = best_value
        return best_action

    def _expectimax(self, core: GameCore, depth_limit: int) -> float:
        if core.state.terminal:
            return 0.0
        if core.state.distance >= depth_limit:
            return self._evaluate(core, depth_limit)

        # Still inside the scripted / known prefix?
        known_len = len(core.generator._rows)
        if core.state.distance < known_len:
            return self._max_value(core, depth_limit)

        # Unseen row → chance node.
        return self._chance_value(core, depth_limit)

    def _max_value(self, core: GameCore, depth_limit: int) -> float:
        best = float("-inf")
        for action in Action:
            twin = core.clone()
            _, reward, done, _ = twin.step(action)
            self.nodes_expanded += 1
            if done:
                val = reward
            else:
                val = reward + self._expectimax(twin, depth_limit)
            if val > best:
                best = val
        return best

    def _chance_value(self, core: GameCore, depth_limit: int) -> float:
        total = 0.0
        for prob, row in self._chance_rows:
            # Temporarily append sampled row as the next scripted cell.
            twin = core.clone()
            # Ensure the next get_row index returns our sampled row.
            idx = twin.state.distance
            rows = list(twin.generator._rows)
            while len(rows) < idx:
                # Should not happen; pad empties.
                rows.append(
                    tuple(Cell(CellType.EMPTY) for _ in range(self.config.num_lanes))
                )
            if len(rows) == idx:
                rows.append(row)
            else:
                rows[idx] = row
            twin.generator._rows = rows
            twin.generator._train_remaining = [0] * self.config.num_lanes
            total += prob * self._max_value(twin, depth_limit)
        return total

    def _evaluate(self, core: GameCore, depth_limit: int) -> float:
        """Leaf evaluation: optimistic fraction of remaining known coins + posture."""
        cfg = self.config
        remaining = max(0, depth_limit - core.state.distance)
        value = remaining * cfg.step_reward * 0.5
        known = len(core.generator._rows)
        for offset in range(core.state.distance, min(known, depth_limit)):
            row = core.generator.get_row(offset)
            for cell in row:
                if cell.type is CellType.COIN or cell.has_coin:
                    value += self.eval_coin_weight * cfg.coin_reward
        # Mild penalty if currently mid-air with little timer left near unknowns.
        if core.state.body_status.value in ("jumping", "rolling"):
            value += 0.01
        return value
