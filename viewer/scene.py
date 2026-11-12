"""Procedural track / city / runner visuals driven only by GameCore state."""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from panda3d.core import AmbientLight, DirectionalLight, NodePath, Vec4

from game.actions import BodyStatus
from game.cells import Cell, CellType
from game.core import GameCore
from viewer import constants as C
from viewer.geometry import make_box, make_wedge, smoothstep


def lane_x(lane: int, num_lanes: int = 3) -> float:
    mid = (num_lanes - 1) * 0.5
    return (lane - mid) * C.LANE_WIDTH


class GameScene:
    """Owns visual nodes. Reads core state; never applies game rules."""

    def __init__(self, root: NodePath, render: NodePath, loader) -> None:
        self.root = root
        self.render = render
        self.loader = loader
        self.world = root.attachNewNode("world")
        self.track_root = self.world.attachNewNode("track")
        self.city_root = self.world.attachNewNode("city")
        self.runner_np = self.world.attachNewNode("runner")
        self._cell_nodes: Dict[Tuple[int, int], NodePath] = {}
        self._coin_spin: List[NodePath] = []
        self._scroll_y = 0.0
        self._target_lane_x = 0.0
        self._runner_z = 0.0
        self._runner_roll = 0.0
        self._built_static = False
        self._last_distance = -1
        self._bob_t = 0.0

        self._setup_lights()
        self._build_runner()
        self._build_static_city()

    def _setup_lights(self) -> None:
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.45, 0.48, 0.55, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor(Vec4(1.05, 0.98, 0.88, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(35, -50, 0)
        self.render.setLight(sun_np)

        fill = DirectionalLight("fill")
        fill.setColor(Vec4(0.25, 0.35, 0.55, 1))
        fill_np = self.render.attachNewNode(fill)
        fill_np.setHpr(-120, -20, 0)
        self.render.setLight(fill_np)

    def _build_runner(self) -> None:
        # Simple stylized surfer: torso + head + legs (primitives).
        body = make_box(
            self.runner_np,
            (0.55, 0.35, 0.85),
            C.RUNNER,
            pos=(0, 0, 0.95),
            name="torso",
        )
        make_box(
            self.runner_np,
            (0.42, 0.38, 0.42),
            (1.0, 0.82, 0.7, 1.0),
            pos=(0, 0.02, 1.55),
            name="head",
        )
        make_box(
            self.runner_np,
            (0.7, 0.25, 0.18),
            (0.15, 0.55, 0.95, 1.0),
            pos=(0, 0, 1.25),
            name="pack",
        )
        make_box(
            self.runner_np,
            (0.22, 0.28, 0.55),
            (0.2, 0.25, 0.45, 1.0),
            pos=(-0.16, 0, 0.35),
            name="leg_l",
        )
        make_box(
            self.runner_np,
            (0.22, 0.28, 0.55),
            (0.2, 0.25, 0.45, 1.0),
            pos=(0.16, 0, 0.35),
            name="leg_r",
        )
        self._runner_body = body

    def _build_static_city(self) -> None:
        if self._built_static:
            return
        self._built_static = True
        rng = random.Random(17)
        # Ground strip under rails
        make_box(
            self.city_root,
            (C.TRACK_HALF_WIDTH * 2.2, (C.VISIBLE_AHEAD + C.VISIBLE_BEHIND) * C.ROW_LENGTH * 2, 0.15),
            C.GROUND,
            pos=(0, C.VISIBLE_AHEAD * C.ROW_LENGTH * 0.4, -0.08),
            name="ground",
        )
        # Sidewalks
        for side in (-1, 1):
            make_box(
                self.city_root,
                (1.4, (C.VISIBLE_AHEAD + 8) * C.ROW_LENGTH, 0.2),
                (0.35, 0.36, 0.38, 1.0),
                pos=(side * (C.TRACK_HALF_WIDTH + 0.9), 20, 0.05),
                name=f"walk_{side}",
            )
        # Procedural building blocks flanking the track
        for side in (-1, 1):
            y = -8.0
            while y < C.VISIBLE_AHEAD * C.ROW_LENGTH + 40:
                w = rng.uniform(2.5, 5.5)
                d = rng.uniform(3.0, 7.0)
                h = rng.uniform(6.0, 22.0)
                color = C.BUILDING_COLORS[rng.randrange(len(C.BUILDING_COLORS))]
                x = side * (C.TRACK_HALF_WIDTH + 3.5 + w * 0.5 + rng.uniform(0, 2))
                make_box(
                    self.city_root,
                    (w, d, h),
                    color,
                    pos=(x, y + d * 0.5, h * 0.5),
                    name="bldg",
                )
                # Window strip accent
                make_box(
                    self.city_root,
                    (w * 0.85, 0.08, h * 0.7),
                    (0.75, 0.85, 1.0, 0.35),
                    pos=(x - side * 0.05, y + d * 0.5 + side * 0.0, h * 0.45),
                    name="win",
                    transparent=True,
                )
                y += d + rng.uniform(0.4, 2.2)

        # Far sky billboards (simple colored planes)
        make_box(
            self.city_root,
            (80, 1, 40),
            C.SKY_HORIZON,
            pos=(0, C.VISIBLE_AHEAD * C.ROW_LENGTH + 55, 12),
            name="sky_far",
        )

    def reset_visuals(self) -> None:
        for np in list(self._cell_nodes.values()):
            np.removeNode()
        self._cell_nodes.clear()
        self._coin_spin.clear()
        self._scroll_y = 0.0
        self._last_distance = -1
        self.track_root.setPos(0, 0, 0)

    def sync_from_core(self, core: GameCore, dt: float, step_alpha: float) -> None:
        """Update visuals from authoritative core state."""
        st = core.state
        cfg = core.config
        # Smooth world scroll so the runner stays near the camera focus.
        target_scroll = st.distance * C.ROW_LENGTH
        self._scroll_y = target_scroll - (1.0 - smoothstep(step_alpha)) * C.ROW_LENGTH * min(
            1.0, st.distance
        )
        self.track_root.setY(-self._scroll_y)
        self.city_root.setY((-self._scroll_y * 0.15) % 40.0)  # slight parallax loop feel

        self._rebuild_cells_if_needed(core)

        # Runner pose
        self._target_lane_x = lane_x(st.lane, cfg.num_lanes)
        cur_x = self.runner_np.getX()
        self.runner_np.setX(cur_x + (self._target_lane_x - cur_x) * min(1.0, dt * 14.0))

        base_z = 0.0
        scale_z = 1.0
        pitch = 0.0
        if st.body_status is BodyStatus.ON_TRAIN:
            base_z = C.TRAIN_TOP_Z
        elif st.body_status is BodyStatus.JUMPING:
            # Arc while jump_timer counts down
            total = max(1, cfg.jump_duration)
            t = 1.0 - (st.jump_timer / total)
            base_z = 1.35 * math.sin(math.pi * min(1.0, t + (1.0 - step_alpha) / total))
        elif st.body_status is BodyStatus.ROLLING:
            scale_z = 0.45
            pitch = 70.0
            base_z = -0.15

        self._runner_z += (base_z - self._runner_z) * min(1.0, dt * 12.0)
        self.runner_np.setZ(self._runner_z)
        self.runner_np.setScale(1.0, 1.0, scale_z)
        self.runner_np.setP(pitch)

        self._bob_t += dt * (6.0 + st.speed * 2.0)
        if st.body_status is BodyStatus.GROUND:
            self.runner_np.setY(math.sin(self._bob_t) * 0.04)

        # Spin coins
        for coin in self._coin_spin:
            if not coin.isEmpty():
                coin.setH(coin.getH() + dt * 220.0)

    def _rebuild_cells_if_needed(self, core: GameCore) -> None:
        st = core.state
        if st.distance == self._last_distance and self._cell_nodes:
            return
        self._last_distance = st.distance

        for np in list(self._cell_nodes.values()):
            np.removeNode()
        self._cell_nodes.clear()
        self._coin_spin.clear()

        start = max(0, st.distance - C.VISIBLE_BEHIND)
        end = st.distance + C.VISIBLE_AHEAD
        for row_i in range(start, end):
            row = core.generator.get_row(row_i)
            y = row_i * C.ROW_LENGTH + C.ROW_LENGTH * 0.5
            self._draw_lane_segment(row_i, y, core.config.num_lanes)
            for lane, cell in enumerate(row):
                self._spawn_cell(row_i, lane, cell, y)

    def _draw_lane_segment(self, row_i: int, y: float, num_lanes: int) -> None:
        # Rails + sleeper for this row
        key = (row_i, -1)
        seg = self.track_root.attachNewNode(f"seg_{row_i}")
        make_box(
            seg,
            (C.TRACK_HALF_WIDTH * 2, C.ROW_LENGTH * 0.98, 0.12),
            (0.18, 0.19, 0.22, 1.0),
            pos=(0, y, 0),
            name="bed",
        )
        for lane in range(num_lanes):
            x = lane_x(lane, num_lanes)
            make_box(
                seg,
                (0.12, C.ROW_LENGTH * 0.95, 0.08),
                C.RAIL,
                pos=(x - 0.55, y, 0.08),
                name="rail_l",
            )
            make_box(
                seg,
                (0.12, C.ROW_LENGTH * 0.95, 0.08),
                C.RAIL,
                pos=(x + 0.55, y, 0.08),
                name="rail_r",
            )
            make_box(
                seg,
                (1.5, 0.35, 0.06),
                C.LANE_PAINT,
                pos=(x, y, 0.1),
                name="tie",
            )
        self._cell_nodes[key] = seg

    def _spawn_cell(self, row_i: int, lane: int, cell: Cell, y: float) -> None:
        x = lane_x(lane)
        key = (row_i, lane)
        holder = self.track_root.attachNewNode(f"cell_{row_i}_{lane}")
        self._cell_nodes[key] = holder

        if cell.type is CellType.EMPTY:
            return

        if cell.type is CellType.COIN or (cell.has_coin and not cell.is_train):
            self._add_coin(holder, x, y, 0.7)
            if cell.type is CellType.COIN:
                return

        if cell.type is CellType.LOW_BARRIER:
            make_box(
                holder,
                (1.7, 0.45, C.LOW_BARRIER_H),
                C.LOW_BARRIER,
                pos=(x, y, C.LOW_BARRIER_H * 0.5),
                name="low",
            )
            # hazard stripes
            make_box(
                holder,
                (1.75, 0.5, 0.12),
                (0.05, 0.05, 0.05, 1.0),
                pos=(x, y, C.LOW_BARRIER_H * 0.55),
                name="stripe",
            )
            return

        if cell.type is CellType.HIGH_BARRIER:
            make_box(
                holder,
                (1.8, 0.4, C.HIGH_BARRIER_H),
                C.HIGH_BARRIER,
                pos=(x, y, C.HIGH_BARRIER_H * 0.5),
                name="high",
            )
            make_box(
                holder,
                (1.9, 0.15, 0.25),
                (0.9, 0.9, 0.95, 1.0),
                pos=(x, y, C.HIGH_BARRIER_H - 0.2),
                name="beam",
            )
            return

        if cell.type is CellType.TRAIN_RAMP:
            make_wedge(
                holder,
                length=C.ROW_LENGTH * 0.9,
                width=1.9,
                height=C.TRAIN_HEIGHT,
                color=C.RAMP,
                pos=(x, y, 0.02),
                name="ramp",
            )
            make_box(
                holder,
                (1.85, C.ROW_LENGTH * 0.35, C.TRAIN_HEIGHT),
                C.TRAIN_BODY,
                pos=(x, y + C.ROW_LENGTH * 0.25, C.TRAIN_HEIGHT * 0.5),
                name="ramp_car",
            )
            if cell.has_coin:
                self._add_coin(holder, x, y, C.TRAIN_TOP_Z + 0.55)
            return

        if cell.type is CellType.TRAIN:
            make_box(
                holder,
                (1.9, C.ROW_LENGTH * 0.92, C.TRAIN_HEIGHT),
                C.TRAIN_BODY,
                pos=(x, y, C.TRAIN_HEIGHT * 0.5),
                name="train",
            )
            make_box(
                holder,
                (1.95, 0.2, 0.35),
                C.TRAIN_ACCENT,
                pos=(x, y + C.ROW_LENGTH * 0.35, C.TRAIN_HEIGHT * 0.75),
                name="accent",
            )
            # windows
            make_box(
                holder,
                (1.6, 0.08, 0.55),
                (0.7, 0.9, 1.0, 0.55),
                pos=(x, y, C.TRAIN_HEIGHT * 0.65),
                name="windows",
                transparent=True,
            )
            if cell.has_coin:
                self._add_coin(holder, x, y, C.TRAIN_TOP_Z + 0.55)

    def _add_coin(self, parent: NodePath, x: float, y: float, z: float) -> None:
        coin = make_box(
            parent,
            (0.55, 0.12, 0.55),
            C.COIN,
            pos=(x, y, z),
            name="coin",
        )
        self._coin_spin.append(coin)
