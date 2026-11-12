"""Panda3D Layer 2 viewer — reads GameCore state; never owns rules."""

__all__ = ["run_viewer"]


def run_viewer(**kwargs):
    from viewer.app import run_viewer as _run

    return _run(**kwargs)
