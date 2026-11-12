"""Reactive baseline agent (proposal §4 rule order)."""

from __future__ import annotations

from typing import Optional

from game.actions import Action, BodyStatus
from game.agent import Observation
from game.cells import Cell, CellType


class BaselineAgent:
    """One-row reactive rules, checked in proposal order.

    1. Low barrier ahead → JUMP; high barrier → ROLL.
    2. Train ahead → move to a neighbouring free lane (else STAY).
    3. Else, if a neighbouring next-row cell has a coin and is safe, move there.
    4. Else STAY.
    """

    name = "baseline"

    def reset(self) -> None:
        return None

    def act(self, observation: Observation) -> Action:
        if observation.terminal or not observation.rows:
            return Action.STAY

        lane = observation.lane
        nxt = observation.rows[0]
        cell = nxt[lane]

        # 1) Immediate barrier response in current lane.
        if cell.type is CellType.LOW_BARRIER:
            return Action.JUMP
        if cell.type is CellType.HIGH_BARRIER:
            return Action.ROLL

        # 2) Train in current lane → flee to a free neighbour.
        if cell.is_train:
            for action, other in self._neighbour_lanes(observation, lane):
                if self._is_free(nxt[other], observation):
                    return action
            return Action.STAY

        # 3) Coin chase into a safe neighbour.
        for action, other in self._neighbour_lanes(observation, lane):
            other_cell = nxt[other]
            if other_cell.type is CellType.COIN or other_cell.has_coin:
                if self._is_safe_entry(other_cell, observation):
                    return action

        # 4) Default.
        return Action.STAY

    @staticmethod
    def _neighbour_lanes(obs: Observation, lane: int):
        if lane > 0:
            yield Action.LEFT, lane - 1
        if lane < obs.num_lanes - 1:
            yield Action.RIGHT, lane + 1

    @staticmethod
    def _is_free(cell: Cell, obs: Observation) -> bool:
        """Lane is free if we can enter it without an unavoidable crash."""
        if cell.type in (CellType.EMPTY, CellType.COIN):
            return True
        if cell.type is CellType.TRAIN_RAMP and obs.train_climbing_enabled:
            return True
        return False

    @staticmethod
    def _is_safe_entry(cell: Cell, obs: Observation) -> bool:
        if cell.is_train and not (
            cell.type is CellType.TRAIN_RAMP and obs.train_climbing_enabled
        ):
            return False
        if cell.type in (CellType.LOW_BARRIER, CellType.HIGH_BARRIER):
            return False
        return True
