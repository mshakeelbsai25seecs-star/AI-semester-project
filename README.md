# Subway Surfers Lite Agent

CS272 Artificial Intelligence (BSAI-2k25, Fall 2026) — Project P12.

Endless 3-lane runner with a **headless pure-Python game core** for seeded AI experiments, plus (upcoming) a Panda3D viewer and search / Expectimax / MDP agents.

## Status

This repository currently ships the **headless game core** (`game/`) and unit tests (`tests/`). Agents, Panda3D UI, and experiments land in follow-up work.

## Setup (Windows / any platform)

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

On macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run tests

From the repo root:

```bat
python -m pytest -q
```

Or on Windows double-click / run:

```bat
run_tests.bat
```

## Game core API (for agents / viewer)

```python
from game import Action, GameConfig, GameCore

core = GameCore(GameConfig())          # defaults: K=8, seed=42, climb on
obs = core.reset(seed=42)              # same seed → same track
while not core.is_terminal:
    action = Action.STAY               # or agent.act(obs)
    obs, reward, done, info = core.step(action)
    # obs.rows = next K cells; each cell is EMPTY/COIN/LOW/HIGH/TRAIN/TRAIN_RAMP
```

Agents implement `game.agent.Agent` (`act(observation) -> Action`). See `game/agent.py`.

### Defaults (`GameConfig`)

| Parameter | Default |
|-----------|---------|
| `observation_k` | 8 |
| `jump_duration` / `roll_duration` | 1 step |
| `coin_reward` | 1.0 |
| `step_reward` | 0.01 |
| `crash_penalty` | -100.0 |
| Speed | 1.0, +0.05 every 50 rows |
| `train_climbing_enabled` | True |
| `default_seed` | 42 |

## Layout

```
game/           headless core (no Panda3D)
tests/          unit tests
requirements.txt
run_tests.bat
```
