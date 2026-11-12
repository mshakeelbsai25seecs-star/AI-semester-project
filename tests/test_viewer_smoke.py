"""Offscreen Panda3D smoke test (skips if display/GL unavailable)."""

from __future__ import annotations

import pytest


def test_viewer_offscreen_runs_briefly():
    # Allow CI / headless VMs without a usable GL context to skip cleanly.
    try:
        from viewer.app import ViewerApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"viewer import failed: {exc}")

    try:
        app = ViewerApp(window_type="offscreen")
    except Exception as exc:
        pytest.skip(f"offscreen window unavailable: {exc}")

    try:
        # Drive a handful of frames without entering the blocking run() loop.
        for _ in range(12):
            app.taskMgr.step()
        assert app.core.state.distance >= 0
        assert app.scene.runner_np is not None
        # Human + Random registry path used by the viewer panel.
        assert app.agent_name == "human"
    finally:
        try:
            app.taskMgr.remove("game_update")
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass
