# Subway Surfers Lite Agent

CS272 Artificial Intelligence (BSAI-2k25, Fall 2026) — Project P12.

Endless 3-lane runner with a **headless pure-Python game core**, **five AI agents**, and a **Panda3D Layer 2 viewer** for human play and demos.

## Status

| Layer | Status |
|-------|--------|
| `game/` headless core | Done |
| `agents/` AI players | Random, baseline, lookahead (A*), Expectimax, MDP |
| `viewer/` Panda3D UI | Done — reads core only; never owns rules |
| `experiments/` E1–E4 | Not yet |

## Setup (Windows)

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Panda3D comes from `requirements.txt` (`panda3d>=1.10.14`). A GPU/display is needed for the on-screen window; core + agent tests run without one.

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

- **Agent** — Human, Random, Baseline, Lookahead, Expectimax, MDP
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

Windows helpers: `run_tests.bat`

Light smoke (one short episode per AI agent):

```bat
python scripts\smoke_agents.py
```

## Agent selection API

```python
from agents import create_agent, list_agents, list_available_agents
from game import GameConfig, GameCore

print(list_agents())
# ['random', 'baseline', 'lookahead', 'expectimax', 'mdp']

print(list_available_agents())
# ['human', 'random', 'baseline', 'lookahead', 'expectimax', 'mdp']

cfg = GameConfig()
agent = create_agent("lookahead", config=cfg)   # also: baseline / expectimax / mdp / random / human
core = GameCore(cfg)
obs = core.reset(seed=42)
while not core.is_terminal:
    action = agent.act(obs)
    obs, reward, done, info = core.step(action)
```

| Name | Class | Notes |
|------|--------|--------|
| `human` | `HumanAgent` | Viewer keyboard; `act` returns STAY |
| `random` | `RandomAgent` | Seeded uniform actions |
| `baseline` | `BaselineAgent` | Proposal §4 one-row reactive rules |
| `lookahead` | `LookaheadAgent` | A* over visible K; `nodes_expanded`, `last_plan` |
| `expectimax` | `ExpectimaxAgent` | Chance nodes beyond K; `nodes_expanded` |
| `mdp` | `MdpAgent` | Offline VI on reduced state; `policy` / `stats` |

Capitalized aliases (`Human`, `Lookahead`, `MDP`, …) are accepted by `create_agent`.

### MDP reduced state (for report / UI)

1. `lane`
2. `body_status` (ground / jumping / rolling / on_train)
3. Cell-type pattern of the nearest `horizon_rows` (default 1)

Jump/roll timers are folded into `body_status` (exact when duration = 1).

## Game core API

```python
from game import Action, GameConfig, GameCore

core = GameCore(GameConfig())          # defaults: K=8, seed=42, climb on
obs = core.reset(seed=42)              # same seed → same track
while not core.is_terminal:
    action = Action.STAY               # or agent.act(obs)
    obs, reward, done, info = core.step(action)
    # obs.rows = next K cells
```

Search agents plan via `GameCore.clone()` / `GameCore.from_observation(...)` so rules stay in `game/` only.

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
game/              headless core (no Panda3D)
agents/            AI players + create_agent registry (+ human for viewer)
viewer/            Panda3D Layer 2 (reads core only)
tests/             unit tests (core + agents + viewer smoke)
scripts/           smoke_agents.py
requirements.txt
run_game.bat
run_tests.bat
```

## Architecture note

The viewer **never owns rules**. It reads `GameCore` state each frame, sends `Action`s into `core.step`, and renders procedural track / trains / barriers / coins / city atmosphere.
