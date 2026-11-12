# Subway Surfers Lite Agent

CS272 Artificial Intelligence (BSAI-2k25, Fall 2026) — Project P12.

Endless 3-lane runner with a **headless pure-Python game core**, **five AI agents**, and a **Panda3D Layer 2 viewer** for human play and Windows demos.

> **Demo OS:** Windows. Short viva walkthrough: see [`DEMO.md`](DEMO.md).

## Status

| Layer | Status |
|-------|--------|
| `game/` headless core | Done |
| `agents/` AI players | Random, baseline, lookahead (A*), Expectimax, MDP |
| `viewer/` Panda3D UI | Done — reads core only; never owns rules |
| `experiments/` E1–E4 | Done — smoke + full presets, plots under `experiments/results/` |

## Windows setup (recommended)

From the repo root in **Command Prompt** or **PowerShell**:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Requirements: **Python 3.10+**, a working display/GPU for the 3D window. Core + agent tests run without a GPU.

Then either:

```bat
run_game.bat
```

or (with venv active):

```bat
python -m viewer
```

`run_game.bat` prefers `.venv\Scripts\python.exe` when present, then `python` / `py -3` on PATH. It checks that Panda3D imports before opening the window.

### Optional launch flags

```bat
python -m viewer --agent lookahead --seed 42
python -m viewer --agent mdp
python -m viewer --offscreen --seconds 2
```

### macOS / Linux (dev)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m viewer
```

## Controls

| Input | Action |
|-------|--------|
| A / Left | Lane left |
| D / Right | Lane right |
| W / Up | Jump |
| S / Down | Roll |
| P / Space | Pause (or **restart after a crash**) |
| R | Restart (applies current panel settings) |
| Esc | Quit |

### Right-hand panel

1. **Agent** — Human (You), Random, Baseline, Lookahead (A*), Expectimax, MDP  
   Changing agent **restarts** the episode so comparisons stay clean.
2. **K / Seed** — observation horizon and track seed (±10)
3. **Playback rate / Start speed / Train climbing** — demo feel + config
4. **Apply settings & Restart** — rebuild `GameConfig` and reset  
   **Restart (R)** after a crash for a fast loop

HUD: coins, distance, speed, score, seed, K, active agent. Crash banner prompts R / Space / Restart.

## Run experiments (E1–E4)

Proposal evaluation suite: agent comparison (E1), effect of K (E2), speed schedule (E3), train climbing on/off (E4).

Metrics per seeded episode: survival steps, coins, nodes expanded, decision time, MDP policy size (where relevant). Seeds and config are logged to `*_meta.json`; summaries include mean and sample variance/std.

```bat
REM Short CI / smoke mode (few seeds, short episodes, light agent kwargs)
python -m experiments --smoke

REM Full report presets (10 seeds, longer caps) — can be slow for Expectimax/MDP
python -m experiments --mode full

REM One experiment only
python -m experiments --smoke --experiment e1
```

Windows helper:

```bat
run_experiments.bat smoke
run_experiments.bat
```

Outputs land in `experiments/results/`:

| File | Contents |
|------|----------|
| `e1_episodes.csv` … `e4_episodes.csv` | Per-seed raw metrics |
| `e1_summary.csv` … `e4_summary.csv` | Mean / variance / std by group |
| `e*_*.png` | Matplotlib plots |
| `run_meta.json` / `e*_meta.json` | Seeds, config, Python/platform versions |

Reproduce the checked-in smoke sample:

```bat
python -m experiments --smoke --results-dir experiments/results
python -m pytest -q tests/test_experiments_plumbing.py
```

## Tests & smoke

```bat
run_tests.bat
```

or:

```bat
python -m pytest -q
```

Headless agent smoke (one short episode each):

```bat
scripts\smoke_agents.bat
```

or `python scripts\smoke_agents.py`

## Troubleshooting (Panda3D / GPU)

| Symptom | What to try |
|---------|-------------|
| `run_game.bat` says Panda3D missing | Activate `.venv`, then `python -m pip install -r requirements.txt` |
| Window never opens / black screen | Update GPU drivers; try another monitor; close apps that lock the GPU |
| Import works but crash on start | Reinstall: `python -m pip install --force-reinstall "panda3d>=1.10.14"` |
| Need proof without a display | `python -m pytest -q` and `scripts\smoke_agents.bat` (core + agents are headless) |
| Wrong Python picked | Use `.venv\Scripts\activate` or delete other `python` entries ahead on PATH |

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
experiments/       E1–E4 runners, metrics, plots → results/
tests/             unit tests (core + agents + viewer + experiments plumbing)
scripts/           smoke_agents.py / .bat
DEMO.md            2–3 min viva / demo script
requirements.txt
run_game.bat
run_tests.bat
run_experiments.bat
```

## Architecture note

The viewer **never owns rules**. It reads `GameCore` state each frame, sends `Action`s into `core.step`, and renders procedural track / trains / barriers / coins / city atmosphere.
