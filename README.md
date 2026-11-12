# Subway Surfers Lite Agent

CS272 Artificial Intelligence (BSAI-2k25, Fall 2026) — Project P12.

Endless 3-lane runner with a **headless pure-Python game core** for seeded AI experiments and a **Panda3D Layer 2 viewer** for human play and demos.

## Status

| Layer | Status |
|-------|--------|
| `game/` headless core | Done |
| `viewer/` Panda3D UI | Done (this branch) |
| `agents/` AI players | Human + Random now; Baseline / Lookahead / Expectimax / MDP plug in when modules land |
| `experiments/` E1–E4 | Not in this PR |

## Setup (Windows)

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Panda3D is pulled in via `requirements.txt` (`panda3d>=1.10.14`). A working GPU/display is needed for the on-screen window. On machines without a display, the core and most tests still run; the offscreen viewer smoke test skips if GL is unavailable.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Play the game

```bat
python -m viewer
```

Or:

```bat
run_game.bat
```

### Controls

| Input | Action |
|-------|--------|
| A / Left | Lane left |
| D / Right | Lane right |
| W / Up | Jump |
| S / Down | Roll |
| P / Space | Pause |
| R | Restart (applies UI tunables) |
| Esc | Quit |

### Runtime UI (right panel)

- **Agent** — Human, Random, and any AI agents discovered in `agents/`
- **K** — observation horizon (look-ahead rows)
- **Seed** — track seed (±10 buttons)
- **Playback rate** — demo step timing (visual)
- **Start speed** — `GameConfig.initial_speed`
- **Train climbing** — on/off
- **Apply & Restart** — rebuild config and reset episode

HUD shows coins, distance, speed, score, seed, K, and the active agent name.

## Run tests

```bat
python -m pytest -q
```

Or `run_tests.bat`.

## Game core API (agents / experiments)

```python
from game import Action, GameConfig, GameCore

core = GameCore(GameConfig())          # defaults: K=8, seed=42, climb on
obs = core.reset(seed=42)              # same seed → same track
while not core.is_terminal:
    action = Action.STAY               # or agent.act(obs)
    obs, reward, done, info = core.step(action)
```

Agents implement `game.agent.Agent` (`act(observation) -> Action`). Register new agents under `agents/` using names expected by `agents.registry` (`BaselineAgent`, `LookaheadAgent`, `ExpectimaxAgent`, `MDPAgent`).

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
viewer/         Panda3D Layer 2 (reads core only)
agents/         agent registry + future AI modules
tests/
requirements.txt
run_game.bat
run_tests.bat
```

## Architecture note

The viewer **never owns rules**. It reads `GameCore` state each frame, sends `Action`s into `core.step`, and renders procedural track / trains / barriers / coins / city atmosphere.
