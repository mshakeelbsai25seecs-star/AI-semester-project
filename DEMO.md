# Demo script (Windows, ~2–3 minutes)

Use this for a viva or classroom walkthrough. Prep once; then follow the beats.

## Prep (before you present)

1. Open the repo in File Explorer.
2. If needed, create the venv once:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```

3. Double-click **`run_game.bat`** (or run it from an activated venv) and confirm the window opens.
4. Optional backup slide: keep a terminal ready with `run_tests.bat` / `scripts\smoke_agents.bat` if the GPU path fails.

## Walkthrough

### 0:00–0:30 — Human play

- Start on **Human (You)**.
- Show WASD / arrows: lane change, jump, roll.
- Point at the HUD (coins, distance, speed, score, seed, K).
- Crash on purpose → banner shows **CRASHED** → press **R** (or Space) to restart.

### 0:30–1:15 — Agent selector

- Right panel → **Agent** → **Baseline**. Episode restarts automatically.
- Let it run ~10–15 seconds; narrate “reactive one-row rules from the proposal.”
- Switch to **Lookahead (A*)**. Mention K in the panel = observation horizon.
- Optional: bump **K** with the slider, click **Apply settings & Restart**, note planning uses visible rows only.

### 1:15–2:00 — Stronger planners

- Switch to **Expectimax** (chance beyond K) — keep playback around 1.0x so it is watchable.
- Switch to **MDP** — “offline value iteration on a reduced state (lane, body, nearest cells).”
- If an agent looks slow, raise **Playback rate** slightly (visual only; does not change core rules).

### 2:00–2:30 — Architecture one-liner

- “Rules live in `game/` only. The Panda3D viewer is Layer 2: it never owns collisions or scoring.”
- “Same agents run headless in tests and experiments.”

### 2:30–3:00 — Close

- Restart once more on **Human** or **Baseline**.
- Esc to quit. Point reviewers at `README.md` troubleshooting if they clone on another machine.

## Quick commands (if asked)

```bat
run_game.bat
python -m viewer --agent lookahead --seed 42
run_tests.bat
scripts\smoke_agents.bat
```
