"""Agent observation API and protocol for later AI players."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Sequence, Tuple, runtime_checkable

from game.actions import Action, BodyStatus
from game.cells import Cell
from game.config import GameConfig


Row = Tuple[Cell, ...]


@dataclass(frozen=True)
class Observation:
    """What an agent (or human UI) may see each step.

    ``rows`` is exactly the next ``k`` upcoming rows (index 0 = imminent).
    Rows beyond ``k`` are intentionally hidden.
    """

    lane: int
    body_status: BodyStatus
    jump_timer: int
    roll_timer: int
    speed: float
    distance: int
    coins: int
    score: float
    steps: int
    rows: Tuple[Row, ...]
    train_climbing_enabled: bool
    num_lanes: int
    terminal: bool = False
    crashed: bool = False

    @property
    def k(self) -> int:
        return len(self.rows)

    def row_types(self) -> List[Tuple[str, ...]]:
        """Convenience: cell type names for debugging / baselines."""
        return [tuple(cell.type.value for cell in row) for row in self.rows]


@runtime_checkable
class Agent(Protocol):
    """Shared interface for random, baseline, search, Expectimax, and MDP agents.

    Implementations must be pure with respect to the game core: they choose an
    action from an observation and must not mutate ``GameCore`` internals.
    """

    def act(self, observation: Observation) -> Action:
        """Return the action to take given the current observation."""
        ...

    def reset(self) -> None:
        """Optional hook called when a new episode starts."""
        ...


def observation_from_parts(
    *,
    lane: int,
    body_status: BodyStatus,
    jump_timer: int,
    roll_timer: int,
    speed: float,
    distance: int,
    coins: int,
    score: float,
    steps: int,
    rows: Sequence[Row],
    config: GameConfig,
    terminal: bool = False,
    crashed: bool = False,
) -> Observation:
    return Observation(
        lane=lane,
        body_status=body_status,
        jump_timer=jump_timer,
        roll_timer=roll_timer,
        speed=speed,
        distance=distance,
        coins=coins,
        score=score,
        steps=steps,
        rows=tuple(rows),
        train_climbing_enabled=config.train_climbing_enabled,
        num_lanes=config.num_lanes,
        terminal=terminal,
        crashed=crashed,
    )
