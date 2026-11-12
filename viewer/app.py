"""Panda3D application: human play + runtime controls over GameCore."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from direct.gui.DirectGui import (
    DirectButton,
    DirectCheckButton,
    DirectFrame,
    DirectLabel,
    DirectOptionMenu,
    DirectSlider,
)
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AntialiasAttrib,
    ClockObject,
    TextNode,
    WindowProperties,
    loadPrcFileData,
)

from agents.registry import (
    create_agent,
    display_name,
    list_all_agent_slots,
    list_available_agents,
    normalize_agent_name,
    refresh_registry,
)
from game.actions import Action
from game.config import GameConfig
from game.core import GameCore
from viewer.hud import HUD
from viewer.scene import GameScene


def _configure_prc(window_type: str = "onscreen") -> None:
    loadPrcFileData("", "window-title Subway Surfers Lite")
    loadPrcFileData("", "sync-video true")
    loadPrcFileData("", "show-frame-rate-meter false")
    loadPrcFileData("", f"window-type {window_type}")
    loadPrcFileData("", "audio-library-name null")
    loadPrcFileData("", "framebuffer-multisample 1")
    loadPrcFileData("", "multisamples 2")


def _section_label(parent, text: str, y: float) -> float:
    DirectLabel(
        parent=parent,
        text=text,
        scale=0.038,
        pos=(0, 0, y),
        text_fg=(1.0, 0.86, 0.28, 1),
        text_align=TextNode.ACenter,
        frameColor=(0, 0, 0, 0),
    )
    return y - 0.07


class ViewerApp(ShowBase):
    """Layer 2 viewer. All rules come from ``GameCore``."""

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        *,
        window_type: str = "onscreen",
        auto_quit_after: Optional[float] = None,
        agent_name: str = "human",
        seed: Optional[int] = None,
    ) -> None:
        _configure_prc(window_type)
        ShowBase.__init__(self)
        self.disableMouse()
        self.render.setAntialias(AntialiasAttrib.MAuto)
        self.setBackgroundColor(0.45, 0.72, 0.98, 1)

        props = WindowProperties()
        props.setTitle("Subway Surfers Lite — CS272")
        props.setSize(1280, 720)
        if self.win is not None and hasattr(self.win, "requestProperties"):
            try:
                self.win.requestProperties(props)
            except Exception:
                pass

        base_cfg = config or GameConfig()
        self.ui_seed = int(seed if seed is not None else base_cfg.default_seed)
        self.ui_k = base_cfg.observation_k
        self.ui_climb = base_cfg.train_climbing_enabled
        self.ui_initial_speed = base_cfg.initial_speed
        self.ui_speed_increment = base_cfg.speed_increment
        self.playback_rate = 1.0
        try:
            self.agent_name = normalize_agent_name(agent_name)
        except KeyError:
            self.agent_name = "human"
        self.paused = False
        self._pending_action: Action = Action.STAY
        self._step_timer = 0.0
        self._step_alpha = 1.0
        self._auto_quit_after = auto_quit_after
        self._elapsed = 0.0
        self._smoke_done = False

        self.core = GameCore(self._make_config())
        self.core.reset(seed=self.ui_seed)
        self._agent = create_agent(
            self.agent_name, config=self.core.config, seed=int(self.ui_seed)
        )

        self.scene = GameScene(self.render, self.render, self.loader)
        self.hud = HUD()
        self._build_camera()
        self._build_control_panel()
        self._bind_keys()

        self.taskMgr.add(self._update, "game_update")
        self.accept("escape", sys.exit)

    # ---------------------------------------------------------------- config

    def _make_config(self) -> GameConfig:
        return GameConfig(
            observation_k=max(1, int(self.ui_k)),
            default_seed=int(self.ui_seed),
            train_climbing_enabled=bool(self.ui_climb),
            initial_speed=float(self.ui_initial_speed),
            speed_increment=float(self.ui_speed_increment),
        )

    def _apply_config_and_restart(self) -> None:
        self.core = GameCore(self._make_config())
        self.core.reset(seed=int(self.ui_seed))
        self.scene.reset_visuals()
        self._pending_action = Action.STAY
        self._step_timer = 0.0
        self._step_alpha = 1.0
        self.paused = False
        self._agent = create_agent(
            self.agent_name, config=self.core.config, seed=int(self.ui_seed)
        )
        if hasattr(self._agent, "reset"):
            try:
                self._agent.reset(seed=int(self.ui_seed))
            except TypeError:
                self._agent.reset()

    # ---------------------------------------------------------------- camera

    def _build_camera(self) -> None:
        self.camera.setPos(0, -11.5, 6.5)
        self.camera.lookAt(0, 6.0, 1.2)

    # ---------------------------------------------------------------- input

    def _bind_keys(self) -> None:
        # Lane / posture — WASD + arrows
        for key in ("a", "arrow_left"):
            self.accept(key, self._queue_human, [Action.LEFT])
        for key in ("d", "arrow_right"):
            self.accept(key, self._queue_human, [Action.RIGHT])
        for key in ("w", "arrow_up"):
            self.accept(key, self._queue_human, [Action.JUMP])
        for key in ("s", "arrow_down"):
            self.accept(key, self._queue_human, [Action.ROLL])
        self.accept("p", self._toggle_pause)
        self.accept("r", self._apply_config_and_restart)
        self.accept("space", self._toggle_pause)

    def _queue_human(self, action: Action) -> None:
        if normalize_agent_name(self.agent_name) != "human":
            return
        if self.paused or self.core.is_terminal:
            return
        # Prefer the latest directional/posture press within the step window.
        self._pending_action = action

    def _toggle_pause(self) -> None:
        # After a crash, Space / Pause acts as Restart for a smooth demo loop.
        if self.core.is_terminal:
            self._apply_config_and_restart()
            return
        self.paused = not self.paused

    # ---------------------------------------------------------------- UI

    def _build_control_panel(self) -> None:
        self.panel = DirectFrame(
            frameColor=(0.04, 0.07, 0.11, 0.78),
            frameSize=(-0.42, 0.42, -0.78, 0.78),
            pos=(1.05, 0, 0.0),
        )
        y = 0.70
        DirectLabel(
            parent=self.panel,
            text="Demo Controls",
            scale=0.052,
            pos=(0, 0, y),
            text_fg=(1, 0.9, 0.3, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.09

        y = _section_label(self.panel, "1. Agent", y)
        refresh_registry()
        slots = list_all_agent_slots()
        available = list_available_agents()
        menu_items = [display_name(name) for name in available]
        self._menu_to_key = {display_name(name): name for name in available}
        initial_label = display_name(self.agent_name)
        initial_idx = (
            menu_items.index(initial_label) if initial_label in menu_items else 0
        )
        self._agent_menu = DirectOptionMenu(
            parent=self.panel,
            text="Agent",
            scale=0.042,
            items=menu_items,
            initialitem=initial_idx,
            highlightColor=(0.2, 0.45, 0.7, 1),
            command=self._on_agent_selected,
            pos=(-0.02, 0, y),
        )
        y -= 0.09
        DirectLabel(
            parent=self.panel,
            text="Changing agent restarts the run",
            scale=0.026,
            pos=(0, 0, y),
            text_fg=(0.7, 0.78, 0.88, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.08

        y = _section_label(self.panel, "2. Observation / track", y)
        DirectLabel(
            parent=self.panel,
            text="K (look-ahead rows)",
            scale=0.032,
            pos=(-0.02, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.055
        self._k_slider = DirectSlider(
            parent=self.panel,
            range=(1, 20),
            value=self.ui_k,
            pageSize=1,
            scale=0.28,
            pos=(0, 0, y),
            command=self._on_k_slider,
        )
        self._k_label = DirectLabel(
            parent=self.panel,
            text=str(self.ui_k),
            scale=0.038,
            pos=(0.32, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.085

        DirectLabel(
            parent=self.panel,
            text="Seed",
            scale=0.032,
            pos=(-0.28, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        self._seed_label = DirectLabel(
            parent=self.panel,
            text=str(self.ui_seed),
            scale=0.038,
            pos=(-0.05, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        DirectButton(
            parent=self.panel,
            text="-10",
            scale=0.032,
            pos=(0.14, 0, y),
            command=self._nudge_seed,
            extraArgs=[-10],
        )
        DirectButton(
            parent=self.panel,
            text="+10",
            scale=0.032,
            pos=(0.30, 0, y),
            command=self._nudge_seed,
            extraArgs=[10],
        )
        y -= 0.09

        y = _section_label(self.panel, "3. Feel (visual only)", y)
        DirectLabel(
            parent=self.panel,
            text="Playback rate",
            scale=0.032,
            pos=(-0.02, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.055
        self._rate_slider = DirectSlider(
            parent=self.panel,
            range=(0.35, 2.5),
            value=self.playback_rate,
            scale=0.28,
            pos=(0, 0, y),
            command=self._on_rate_slider,
        )
        self._rate_label = DirectLabel(
            parent=self.panel,
            text=f"{self.playback_rate:.2f}x",
            scale=0.034,
            pos=(0.32, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.085

        DirectLabel(
            parent=self.panel,
            text="Start speed",
            scale=0.032,
            pos=(-0.02, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.055
        self._spd_slider = DirectSlider(
            parent=self.panel,
            range=(0.5, 2.5),
            value=self.ui_initial_speed,
            scale=0.28,
            pos=(0, 0, y),
            command=self._on_spd_slider,
        )
        self._spd_label = DirectLabel(
            parent=self.panel,
            text=f"{self.ui_initial_speed:.2f}",
            scale=0.034,
            pos=(0.32, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.08

        self._climb_box = DirectCheckButton(
            parent=self.panel,
            text="Train climbing",
            scale=0.036,
            pos=(-0.02, 0, y),
            indicatorValue=1 if self.ui_climb else 0,
            command=self._on_climb_toggle,
            boxPlacement="left",
        )
        y -= 0.09

        y = _section_label(self.panel, "4. Run", y)
        DirectButton(
            parent=self.panel,
            text="Apply settings & Restart",
            scale=0.038,
            pos=(0, 0, y),
            command=self._apply_config_and_restart,
            frameColor=(0.12, 0.48, 0.78, 1),
            text_fg=(1, 1, 1, 1),
        )
        y -= 0.085
        DirectButton(
            parent=self.panel,
            text="Pause / Resume (P)",
            scale=0.034,
            pos=(0, 0, y),
            command=self._toggle_pause,
            frameColor=(0.22, 0.28, 0.36, 1),
        )
        y -= 0.07
        DirectButton(
            parent=self.panel,
            text="Restart (R)",
            scale=0.034,
            pos=(0, 0, y),
            command=self._apply_config_and_restart,
            frameColor=(0.55, 0.28, 0.18, 1),
            text_fg=(1, 0.95, 0.9, 1),
        )

        missing = [display_name(n) for n, ok in slots if not ok]
        note = "Agents ready: " + ", ".join(display_name(n) for n in available)
        if missing:
            note += "  |  Later: " + ", ".join(missing)
        DirectLabel(
            parent=self.panel,
            text=note,
            scale=0.026,
            pos=(0, 0, -0.72),
            text_fg=(0.72, 0.78, 0.88, 1),
            text_wordwrap=18,
            frameColor=(0, 0, 0, 0),
        )

    def _on_agent_selected(self, label: str) -> None:
        refresh_registry()
        name = self._menu_to_key.get(label, label)
        try:
            name = normalize_agent_name(name)
        except KeyError:
            return
        if name not in list_available_agents():
            return
        if name == self.agent_name:
            return
        self.agent_name = name
        # Fresh episode so the viva can compare agents cleanly.
        self._apply_config_and_restart()

    def _on_k_slider(self) -> None:
        self.ui_k = int(round(self._k_slider["value"]))
        self._k_label.setText(str(self.ui_k))

    def _on_rate_slider(self) -> None:
        self.playback_rate = float(self._rate_slider["value"])
        self._rate_label.setText(f"{self.playback_rate:.2f}x")

    def _on_spd_slider(self) -> None:
        self.ui_initial_speed = float(self._spd_slider["value"])
        self._spd_label.setText(f"{self.ui_initial_speed:.2f}")

    def _on_climb_toggle(self, checked: bool) -> None:
        self.ui_climb = bool(checked)

    def _nudge_seed(self, delta: int) -> None:
        self.ui_seed = max(0, int(self.ui_seed) + delta)
        self._seed_label.setText(str(self.ui_seed))

    # ---------------------------------------------------------------- loop

    def _step_interval(self) -> float:
        # Faster game speed → shorter interval; playback_rate scales demo feel.
        speed = max(0.25, float(self.core.state.speed))
        return 0.42 / (speed * max(0.25, self.playback_rate))

    def _choose_action(self) -> Action:
        if normalize_agent_name(self.agent_name) == "human":
            action = self._pending_action
            self._pending_action = Action.STAY
            return action
        obs = self.core.observe(k=int(self.ui_k))
        try:
            action = self._agent.act(obs)
        except Exception:
            action = Action.STAY
        if not isinstance(action, Action):
            try:
                action = Action(action)
            except Exception:
                action = Action.STAY
        return action

    def _update(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        self._elapsed += dt
        if self._auto_quit_after is not None and self._elapsed >= self._auto_quit_after:
            # Prefer a soft stop so smoke tests can drive taskMgr.step()
            # without ShowBase.finalizeExit() calling sys.exit().
            self._smoke_done = True
            return task.done

        if not self.paused and not self.core.is_terminal:
            self._step_timer += dt
            interval = self._step_interval()
            self._step_alpha = min(1.0, self._step_timer / max(1e-6, interval))
            if self._step_timer >= interval:
                self._step_timer -= interval
                action = self._choose_action()
                self.core.step(action)
                self._step_alpha = 0.0
        else:
            self._step_alpha = 1.0

        self.scene.sync_from_core(self.core, dt, self._step_alpha)

        # Subtle camera sway with lane
        target_x = self.scene.runner_np.getX() * 0.35
        cam = self.camera
        cam.setX(cam.getX() + (target_x - cam.getX()) * min(1.0, dt * 4.0))
        cam.lookAt(self.scene.runner_np.getX() * 0.2, 6.0, 1.3 + self.scene._runner_z * 0.15)

        st = self.core.state
        self.hud.update(
            coins=st.coins,
            distance=st.distance,
            speed=st.speed,
            score=st.score,
            agent_name=display_name(self.agent_name),
            paused=self.paused,
            crashed=st.crashed,
            seed=self.ui_seed,
            k=int(self.ui_k),
        )
        return task.cont


def run_viewer(
    *,
    window_type: str = "onscreen",
    auto_quit_after: Optional[float] = None,
    config: Optional[GameConfig] = None,
    agent_name: str = "human",
    seed: Optional[int] = None,
) -> None:
    app = ViewerApp(
        config=config,
        window_type=window_type,
        auto_quit_after=auto_quit_after,
        agent_name=agent_name,
        seed=seed,
    )
    app.run()


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Subway Surfers Lite — Panda3D viewer (Layer 2)"
    )
    parser.add_argument(
        "--agent",
        default="human",
        help="Starting agent: human, random, baseline, lookahead, expectimax, mdp",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Track seed (default: GameConfig.default_seed)",
    )
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Open an offscreen window (smoke / CI)",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="Auto-quit after N seconds (smoke helper)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    run_viewer(
        window_type="offscreen" if args.offscreen else "onscreen",
        auto_quit_after=args.seconds,
        agent_name=args.agent,
        seed=args.seed,
    )
