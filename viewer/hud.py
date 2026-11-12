"""On-screen HUD: coins, distance, speed, agent name."""

from __future__ import annotations

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode


class HUD:
    def __init__(self) -> None:
        self.title = OnscreenText(
            text="SUBWAY SURFERS LITE",
            pos=(-1.25, 0.92),
            scale=0.055,
            fg=(1, 0.92, 0.25, 1),
            align=TextNode.ALeft,
            mayChange=False,
            shadow=(0, 0, 0, 0.6),
        )
        self.stats = OnscreenText(
            text="",
            pos=(-1.25, 0.84),
            scale=0.045,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            mayChange=True,
            shadow=(0, 0, 0, 0.55),
        )
        self.agent = OnscreenText(
            text="",
            pos=(1.25, 0.92),
            scale=0.048,
            fg=(0.7, 0.95, 1.0, 1),
            align=TextNode.ARight,
            mayChange=True,
            shadow=(0, 0, 0, 0.55),
        )
        self.banner = OnscreenText(
            text="",
            pos=(0, 0.15),
            scale=0.08,
            fg=(1, 0.35, 0.3, 1),
            align=TextNode.ACenter,
            mayChange=True,
            shadow=(0, 0, 0, 0.7),
        )
        self.hint = OnscreenText(
            text="WASD / Arrows  |  P pause  |  R restart  |  Esc quit",
            pos=(0, -0.92),
            scale=0.035,
            fg=(0.9, 0.9, 0.95, 0.85),
            align=TextNode.ACenter,
            mayChange=False,
            shadow=(0, 0, 0, 0.5),
        )

    def update(
        self,
        *,
        coins: int,
        distance: int,
        speed: float,
        score: float,
        agent_name: str,
        paused: bool,
        crashed: bool,
        seed: int,
        k: int,
    ) -> None:
        self.stats.setText(
            f"Coins {coins}   Dist {distance}   Speed {speed:.2f}   Score {score:.1f}   "
            f"Seed {seed}   K {k}"
        )
        self.agent.setText(f"Agent: {agent_name}")
        if crashed:
            self.banner.setText("CRASH — press R to restart")
        elif paused:
            self.banner.setText("PAUSED")
        else:
            self.banner.setText("")

    def destroy(self) -> None:
        for node in (self.title, self.stats, self.agent, self.banner, self.hint):
            node.destroy()
