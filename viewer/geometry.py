"""Procedural colored primitives for a Subway Surfers-like look."""

from __future__ import annotations

from typing import Sequence, Tuple

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    TransparencyAttrib,
)

Color = Tuple[float, float, float, float]


def _box_mesh(
    sx: float,
    sy: float,
    sz: float,
    color: Color,
    name: str = "box",
) -> GeomNode:
    """Axis-aligned box centered at origin, size (sx, sy, sz)."""
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    # 8 corners
    corners = [
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    ]
    faces = [
        (0, 1, 2, 3),  # bottom
        (4, 7, 6, 5),  # top
        (0, 4, 5, 1),  # -Y
        (2, 6, 7, 3),  # +Y
        (0, 3, 7, 4),  # -X
        (1, 5, 6, 2),  # +X
    ]
    normals = [
        (0, 0, -1),
        (0, 0, 1),
        (0, -1, 0),
        (0, 1, 0),
        (-1, 0, 0),
        (1, 0, 0),
    ]

    fmt = GeomVertexFormat.getV3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color_w = GeomVertexWriter(vdata, "color")
    tris = GeomTriangles(Geom.UHStatic)

    idx = 0
    for face, nrm in zip(faces, normals):
        base = idx
        for ci in face:
            vertex.addData3(*corners[ci])
            normal.addData3(*nrm)
            color_w.addData4(*color)
            idx += 1
        tris.addVertices(base, base + 1, base + 2)
        tris.addVertices(base, base + 2, base + 3)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    return node


def make_box(
    parent: NodePath,
    size: Sequence[float],
    color: Color,
    pos: Sequence[float] = (0, 0, 0),
    name: str = "box",
    transparent: bool = False,
) -> NodePath:
    node = _box_mesh(float(size[0]), float(size[1]), float(size[2]), color, name=name)
    np = parent.attachNewNode(node)
    np.setPos(*pos)
    if transparent or color[3] < 0.999:
        np.setTransparency(TransparencyAttrib.MAlpha)
    np.setTwoSided(True)
    return np


def make_wedge(
    parent: NodePath,
    length: float,
    width: float,
    height: float,
    color: Color,
    pos: Sequence[float] = (0, 0, 0),
    name: str = "wedge",
) -> NodePath:
    """Ramp rising along +Y (low at -Y, high at +Y)."""
    hw = width * 0.5
    hl = length * 0.5
    # Triangle prism: ground quad + slope + sides
    fmt = GeomVertexFormat.getV3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color_w = GeomVertexWriter(vdata, "color")

    # Points: back-left/right ground, front-left/right ground, front-left/right top
    pts = [
        (-hw, -hl, 0.0),  # 0 back L
        (hw, -hl, 0.0),  # 1 back R
        (hw, hl, 0.0),  # 2 front R ground
        (-hw, hl, 0.0),  # 3 front L ground
        (hw, hl, height),  # 4 front R top
        (-hw, hl, height),  # 5 front L top
    ]

    def add_tri(i0, i1, i2, nrm):
        for i in (i0, i1, i2):
            vertex.addData3(*pts[i])
            normal.addData3(*nrm)
            color_w.addData4(*color)

    # slope (facing up-ish)
    add_tri(0, 1, 4, (0, -0.4, 0.9))
    add_tri(0, 4, 5, (0, -0.4, 0.9))
    # front face
    add_tri(3, 2, 4, (0, 1, 0))
    add_tri(3, 4, 5, (0, 1, 0))
    # left / right
    add_tri(0, 5, 3, (-1, 0, 0))
    add_tri(1, 2, 4, (1, 0, 0))

    geom = Geom(vdata)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(0, 18, 3):
        tris.addVertices(i, i + 1, i + 2)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    np = parent.attachNewNode(node)
    np.setPos(*pos)
    np.setTwoSided(True)
    return np


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
