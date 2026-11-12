# Subway Surfers Lite Agent

CS272 Artificial Intelligence (BSAI-2k25, Fall 2026) — Project P12.

Endless 3-lane runner with a **headless pure-Python game core** and **five AI agents**. Panda3D viewer and experiment harness come next.

## Status

- `game/` — headless core (seeded track, rules, scoring, K-row observations)
- `agents/` — random, baseline, lookahead (A*), Expectimax, MDP (value iteration)
- Panda3D UI / full experiments — not in this branch yet

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

```bat
python -m pytest -q
```

Windows helper: `run_tests.bat`

Light smoke (one short episode per agent):

```bat
python scripts\smoke_agents.py
```

## Agent selection API (for the viewer)

```python
from agents import create_agent, list_agents
from game import GameConfig, GameCore

print(list_agents())
# ['random', 'baseline', 'lookahead', 'expectimax', 'mdp']

cfg = GameConfig()
agent = create_agent("lookahead", config=cfg)   # or baseline / expectimax / mdp / random
core = GameCore(cfg)
obs = core.reset(seed=42)
while not core.is_terminal:
    action = agent.act(obs)
    obs, reward, done, info = core.step(action)
```

| Name | Class | Notes |
|------|--------|--------|
| `random` | `RandomAgent` | Seeded uniform actions |
| `baseline` | `BaselineAgent` | Proposal §4 one-row reactive rules |
| `lookahead` | `LookaheadAgent` | A* over visible K; `nodes_expanded`, `last_plan` |
| `expectimax` | `ExpectimaxAgent` | Chance nodes beyond K; `nodes_expanded` |
| `mdp` | `MdpAgent` | Offline VI on reduced state; `policy` / `stats` |

### MDP reduced state (for report / UI)

1. `lane`
2. `body_status` (ground / jumping / rolling / on_train)
3. Cell-type pattern of the nearest `horizon_rows` (default 1)

Jump/roll timers are folded into `body_status` (exact when duration = 1).

## Game core API

```python
from game import Action, GameConfig, GameCore

core = GameCore(GameConfig())
obs = core.reset(seed=42)
obs, reward, done, info = core.step(Action.JUMP)
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
agents/            AI players + create_agent registry
tests/             unit tests (core + agents)
scripts/           smoke_agents.py
requirements.txt
run_tests.bat
```
