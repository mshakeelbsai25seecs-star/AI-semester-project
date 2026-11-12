"""Player actions and runner body status."""

from __future__ import annotations

from enum import Enum


class Action(Enum):
    """One discrete action chosen each step."""

    STAY = "stay"
    LEFT = "left"
    RIGHT = "right"
    JUMP = "jump"
    ROLL = "roll"


class BodyStatus(Enum):
    """How the runner occupies the lane vertically."""

    GROUND = "ground"
    JUMPING = "jumping"
    ROLLING = "rolling"
    ON_TRAIN = "on_train"
