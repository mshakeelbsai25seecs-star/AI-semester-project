"""Panda3D application: human play + runtime controls over GameCore."""

from __future__ import annotations

import sys
from typing import List, Optional

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
    list_all_agent_slots,
    list_available_agents,
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


class ViewerApp(ShowBase):
    """Layer 2 viewer. All rules come from ``GameCore``."""

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        *,
        window_type: str = "onscreen",
        auto_quit_after: Optional[float] = None,
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

        self.ui_seed = (config or GameConfig()).default_seed
        self.ui_k = (config or GameConfig()).observation_k
        self.ui_climb = (config or GameConfig()).train_climbing_enabled
        self.ui_initial_speed = (config or GameConfig()).initial_speed
        self.ui_speed_increment = (config or GameConfig()).speed_increment
        self.playback_rate = 1.0
        self.agent_name = "Human"
        self.paused = False
        self._pending_action: Action = Action.STAY
        self._step_timer = 0.0
        self._step_alpha = 1.0
        self._agent = create_agent("Human")
        self._auto_quit_after = auto_quit_after
        self._elapsed = 0.0
        self._smoke_done = False

        self.core = GameCore(self._make_config())
        self.core.reset(seed=self.ui_seed)

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
        if hasattr(self._agent, "reset"):
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
        if self.agent_name != "Human":
            return
        if self.paused or self.core.is_terminal:
            return
        # Prefer the latest directional/posture press within the step window.
        self._pending_action = action

    def _toggle_pause(self) -> None:
        if self.core.is_terminal:
            return
        self.paused = not self.paused

    # ---------------------------------------------------------------- UI

    def _build_control_panel(self) -> None:
        self.panel = DirectFrame(
            frameColor=(0.05, 0.08, 0.12, 0.72),
            frameSize=(-0.42, 0.42, -0.72, 0.72),
            pos=(1.05, 0, 0.05),
        )
        y = 0.62
        DirectLabel(
            parent=self.panel,
            text="Controls",
            scale=0.055,
            pos=(0, 0, y),
            text_fg=(1, 0.9, 0.3, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.1

        refresh_registry()
        slots = list_all_agent_slots()
        labels: List[str] = []
        for name, ok in slots:
            labels.append(name if ok else f"{name} (soon)")
        # Only selectable items that are available
        available = list_available_agents()
        self._agent_menu = DirectOptionMenu(
            parent=self.panel,
            text="Agent",
            scale=0.045,
            items=available,
            initialitem=available.index("Human") if "Human" in available else 0,
            highlightColor=(0.2, 0.45, 0.7, 1),
            command=self._on_agent_selected,
            pos=(-0.05, 0, y),
        )
        y -= 0.12

        DirectLabel(
            parent=self.panel,
            text="K (look-ahead)",
            scale=0.035,
            pos=(0, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.06
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
            scale=0.04,
            pos=(0.32, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.1

        DirectLabel(
            parent=self.panel,
            text="Seed",
            scale=0.035,
            pos=(-0.22, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        self._seed_label = DirectLabel(
            parent=self.panel,
            text=str(self.ui_seed),
            scale=0.04,
            pos=(0.05, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        DirectButton(
            parent=self.panel,
            text="-10",
            scale=0.035,
            pos=(-0.05, 0, y - 0.07),
            command=self._nudge_seed,
            extraArgs=[-10],
        )
        DirectButton(
            parent=self.panel,
            text="+10",
            scale=0.035,
            pos=(0.15, 0, y - 0.07),
            command=self._nudge_seed,
            extraArgs=[10],
        )
        y -= 0.18

        DirectLabel(
            parent=self.panel,
            text="Playback rate",
            scale=0.035,
            pos=(0, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.06
        self._rate_slider = DirectSlider(
            parent=self.panel,
            range=(0.35, 2.5),
            value=self.playback_rate,
            scale=0.28,
            pos=(0, 0, y),
            command=self._on_rate_slider,
        )
        y -= 0.1

        DirectLabel(
            parent=self.panel,
            text="Start speed",
            scale=0.035,
            pos=(0, 0, y),
            text_fg=(0.9, 0.9, 0.95, 1),
            frameColor=(0, 0, 0, 0),
        )
        y -= 0.06
        self._spd_slider = DirectSlider(
            parent=self.panel,
            range=(0.5, 2.5),
            value=self.ui_initial_speed,
            scale=0.28,
            pos=(0, 0, y),
            command=self._on_spd_slider,
        )
        y -= 0.1

        self._climb_box = DirectCheckButton(
            parent=self.panel,
            text="Train climbing",
            scale=0.04,
            pos=(-0.05, 0, y),
            indicatorValue=1 if self.ui_climb else 0,
            command=self._on_climb_toggle,
            boxPlacement="left",
        )
        y -= 0.12

        DirectButton(
            parent=self.panel,
            text="Apply & Restart",
            scale=0.045,
            pos=(0, 0, y),
            command=self._apply_config_and_restart,
            frameColor=(0.15, 0.45, 0.75, 1),
        )
        y -= 0.1
        DirectButton(
            parent=self.panel,
            text="Pause / Resume",
            scale=0.04,
            pos=(0, 0, y),
            command=self._toggle_pause,
        )
        y -= 0.08
        DirectButton(
            parent=self.panel,
            text="Restart",
            scale=0.04,
            pos=(0, 0, y),
            command=self._apply_config_and_restart,
        )

        # Availability footnote
        missing = [n for n, ok in slots if not ok]
        note = "Ready: " + ", ".join(available)
        if missing:
            note += "  |  Later: " + ", ".join(missing)
        DirectLabel(
            parent=self.panel,
            text=note,
            scale=0.028,
            pos=(0, 0, -0.66),
            text_fg=(0.75, 0.8, 0.9, 1),
            text_wordwrap=18,
            frameColor=(0, 0, 0, 0),
        )

    def _on_agent_selected(self, name: str) -> None:
        refresh_registry()
        if name not in list_available_agents():
            return
        self.agent_name = name
        self._agent = create_agent(name)
        self._pending_action = Action.STAY

    def _on_k_slider(self) -> None:
        self.ui_k = int(round(self._k_slider["value"]))
        self._k_label.setText(str(self.ui_k))

    def _on_rate_slider(self) -> None:
        self.playback_rate = float(self._rate_slider["value"])

    def _on_spd_slider(self) -> None:
        self.ui_initial_speed = float(self._spd_slider["value"])

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
        if self.agent_name == "Human":
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
            agent_name=self.agent_name,
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
) -> None:
    app = ViewerApp(
        config=config,
        window_type=window_type,
        auto_quit_after=auto_quit_after,
    )
    app.run()


if __name__ == "__main__":
    run_viewer()
