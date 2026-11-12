"""CSV / JSON helpers for experiment outputs."""

from __future__ import annotations

import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_metadata(presets: Any, argv: Sequence[str] | None = None) -> Dict[str, Any]:
    """Reproducibility blob: seeds, config, versions, machine."""
    try:
        import matplotlib

        mpl_version = matplotlib.__version__
    except Exception:  # pragma: no cover
        mpl_version = None
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "argv": list(argv or sys.argv),
        "mode": getattr(presets, "mode", None),
        "experiments": list(getattr(presets, "experiments", ())),
        "agents": list(getattr(presets, "agents", ())),
        "seeds": list(getattr(presets, "seeds", ())),
        "max_steps": getattr(presets, "max_steps", None),
        "observation_k": getattr(presets, "observation_k", None),
        "k_values": list(getattr(presets, "k_values", ())),
        "speed_schedules": [
            {
                "label": label,
                "initial_speed": init,
                "speed_increment": inc,
                "speed_interval_rows": interval,
            }
            for label, init, inc, interval in getattr(presets, "speed_schedules", ())
        ],
        "climb_values": list(getattr(presets, "climb_values", ())),
        "agent_kwargs": getattr(presets, "agent_kwargs", {}),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.node(),
        "matplotlib": mpl_version,
    }
