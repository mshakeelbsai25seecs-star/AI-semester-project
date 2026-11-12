"""Uniform random action agent (comparison floor)."""

from __future__ import annotations

import random
from typing import Optional

from game.actions import Action
from game.agent import Observation


class RandomAgent:
    """Chooses uniformly among the five actions each step."""

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._rng = random.Random(seed)
        self._actions = list(Action)
        self.last_action: Optional[Action] = None

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.seed = seed
        self._rng.seed(self.seed)
        self.last_action = None

    def act(self, observation: Observation) -> Action:
        if observation.terminal:
            self.last_action = Action.STAY
            return self.last_action
        action = self._rng.choice(self._actions)
        self.last_action = action
        return action
