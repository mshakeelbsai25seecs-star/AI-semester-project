"""ASP-7 experiment suite (proposal E1–E4).

Run from the repo root::

    python -m experiments --smoke
    python -m experiments --experiment e1
    run_experiments.bat
"""

from __future__ import annotations

from experiments.episode import EpisodeResult, run_episode
from experiments.suite import EXPERIMENT_IDS, run_experiments

__all__ = [
    "EpisodeResult",
    "EXPERIMENT_IDS",
    "run_episode",
    "run_experiments",
]
