"""E1–E4 experiment orchestration."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from game.config import GameConfig

from experiments.aggregate import AggregateRow, aggregate_results
from experiments.defaults import (
    ExperimentPresets,
    agent_kwargs_for,
    presets_for_mode,
    with_experiments,
)
from experiments.episode import EpisodeResult, run_episode
from experiments.io_util import ensure_dir, run_metadata, write_csv, write_json
from experiments.plots import write_plots_for_experiment

EXPERIMENT_IDS = ("e1", "e2", "e3", "e4")


def _base_config(presets: ExperimentPresets, **overrides) -> GameConfig:
    payload = {
        "observation_k": presets.observation_k,
        "train_climbing_enabled": True,
    }
    payload.update(overrides)
    return GameConfig(**payload)


def run_e1(presets: ExperimentPresets) -> List[EpisodeResult]:
    """E1 — Which agent survives longer and collects more coins?"""
    results: List[EpisodeResult] = []
    cfg = _base_config(presets)
    for agent_name in presets.agents:
        for seed in presets.seeds:
            results.append(
                run_episode(
                    agent_name,
                    seed=seed,
                    config=cfg,
                    max_steps=presets.max_steps,
                    experiment="e1",
                    mode=presets.mode,
                    label="default",
                    agent_kwargs=agent_kwargs_for(presets, agent_name),
                    extra={"variant": "agent_comparison"},
                )
            )
    return results


def run_e2(presets: ExperimentPresets) -> List[EpisodeResult]:
    """E2 — How does K change quality and cost?"""
    results: List[EpisodeResult] = []
    for k in presets.k_values:
        cfg = _base_config(presets, observation_k=int(k))
        for agent_name in presets.agents:
            for seed in presets.seeds:
                results.append(
                    run_episode(
                        agent_name,
                        seed=seed,
                        config=cfg,
                        max_steps=presets.max_steps,
                        experiment="e2",
                        mode=presets.mode,
                        label=str(k),
                        agent_kwargs=agent_kwargs_for(presets, agent_name),
                        extra={"variant": "effect_of_k", "observation_k": int(k)},
                    )
                )
    return results


def run_e3(presets: ExperimentPresets) -> List[EpisodeResult]:
    """E3 — Which agents fail first as the game speeds up?"""
    results: List[EpisodeResult] = []
    for label, init, inc, interval in presets.speed_schedules:
        cfg = _base_config(
            presets,
            initial_speed=float(init),
            speed_increment=float(inc),
            speed_interval_rows=int(interval),
        )
        for agent_name in presets.agents:
            for seed in presets.seeds:
                results.append(
                    run_episode(
                        agent_name,
                        seed=seed,
                        config=cfg,
                        max_steps=presets.max_steps,
                        experiment="e3",
                        mode=presets.mode,
                        label=str(label),
                        agent_kwargs=agent_kwargs_for(presets, agent_name),
                        extra={"variant": "speed_schedule", "speed_schedule": label},
                    )
                )
    return results


def run_e4(presets: ExperimentPresets) -> List[EpisodeResult]:
    """E4 — Does climbing trains help or hurt?"""
    results: List[EpisodeResult] = []
    for climb in presets.climb_values:
        cfg = _base_config(presets, train_climbing_enabled=bool(climb))
        climb_label = "on" if climb else "off"
        for agent_name in presets.agents:
            for seed in presets.seeds:
                results.append(
                    run_episode(
                        agent_name,
                        seed=seed,
                        config=cfg,
                        max_steps=presets.max_steps,
                        experiment="e4",
                        mode=presets.mode,
                        label=climb_label,
                        agent_kwargs=agent_kwargs_for(presets, agent_name),
                        extra={
                            "variant": "train_climbing",
                            "climb": climb_label,
                            "train_climbing_enabled": bool(climb),
                        },
                    )
                )
    return results


_RUNNERS: Dict[str, Callable[[ExperimentPresets], List[EpisodeResult]]] = {
    "e1": run_e1,
    "e2": run_e2,
    "e3": run_e3,
    "e4": run_e4,
}


def _group_fields_for(experiment_id: str) -> Sequence[str]:
    if experiment_id == "e2":
        return ("experiment", "agent", "observation_k", "label")
    return ("experiment", "agent", "label")


def _write_outputs(
    experiment_id: str,
    results: Sequence[EpisodeResult],
    presets: ExperimentPresets,
    results_dir: Path,
) -> Dict[str, object]:
    ensure_dir(results_dir)
    raw_path = results_dir / f"{experiment_id}_episodes.csv"
    summary_path = results_dir / f"{experiment_id}_summary.csv"
    meta_path = results_dir / f"{experiment_id}_meta.json"

    write_csv(raw_path, [r.to_row() for r in results])
    aggregates = aggregate_results(results, group_by=_group_fields_for(experiment_id))
    write_csv(summary_path, [a.to_row() for a in aggregates])
    write_json(meta_path, run_metadata(presets))

    plot_paths: List[Path] = []
    if presets.write_plots:
        plot_paths = write_plots_for_experiment(experiment_id, aggregates, results_dir)

    return {
        "experiment": experiment_id,
        "episodes": len(results),
        "aggregates": len(aggregates),
        "raw_csv": str(raw_path),
        "summary_csv": str(summary_path),
        "meta_json": str(meta_path),
        "plots": [str(p) for p in plot_paths],
        "aggregate_rows": aggregates,
    }


def run_experiments(
    *,
    mode: str = "full",
    experiment_ids: Optional[Sequence[str]] = None,
    results_dir: Optional[str | Path] = None,
    presets: Optional[ExperimentPresets] = None,
    progress: bool = True,
) -> Dict[str, object]:
    """Run selected experiments and write CSV / plots under ``results/``."""
    base = presets or presets_for_mode(mode)
    ids = tuple(
        e.strip().lower()
        for e in (experiment_ids if experiment_ids is not None else base.experiments)
    )
    for exp_id in ids:
        if exp_id not in _RUNNERS:
            raise ValueError(
                f"Unknown experiment {exp_id!r}; choose from {list(EXPERIMENT_IDS)}"
            )
    cfg = with_experiments(base, ids)
    if results_dir is not None:
        cfg = replace(cfg, results_dir=str(results_dir))

    out_root = Path(cfg.results_dir)
    ensure_dir(out_root)
    (out_root / ".gitkeep").touch(exist_ok=True)
    write_json(out_root / "run_meta.json", run_metadata(cfg))

    all_results: List[EpisodeResult] = []
    per_experiment: Dict[str, object] = {}

    for exp_id in ids:
        if progress:
            print(f"[experiments] running {exp_id} ({cfg.mode}) ...", flush=True)
        results = _RUNNERS[exp_id](cfg)
        info = _write_outputs(exp_id, results, cfg, out_root)
        aggregates: List[AggregateRow] = info.pop("aggregate_rows")  # type: ignore[assignment]
        per_experiment[exp_id] = info
        all_results.extend(results)
        if progress:
            top = sorted(
                aggregates,
                key=lambda r: r.means.get("survival_steps", 0.0),
                reverse=True,
            )[:3]
            brief = ", ".join(
                f"{r.group.get('agent', '?')}/{r.group.get('label', '')}:"
                f"{r.means['survival_steps']:.1f}"
                for r in top
            )
            print(
                f"[experiments] {exp_id}: {len(results)} episodes → {info['summary_csv']}"
                + (f" | top survival {brief}" if brief else ""),
                flush=True,
            )

    combined_path = out_root / "all_episodes.csv"
    write_csv(combined_path, [r.to_row() for r in all_results])
    return {
        "mode": cfg.mode,
        "results_dir": str(out_root.resolve()),
        "experiments": per_experiment,
        "episode_count": len(all_results),
        "combined_csv": str(combined_path),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI used by ``python -m experiments``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m experiments",
        description="Run Subway Surfers Lite evaluation suite (proposal E1–E4).",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Short CI mode (few seeds, short episodes, light agent kwargs).",
    )
    parser.add_argument(
        "--mode",
        choices=("smoke", "full"),
        default=None,
        help="Preset pack (default: full; --smoke implies smoke).",
    )
    parser.add_argument(
        "--experiment",
        "-e",
        action="append",
        dest="experiments",
        choices=list(EXPERIMENT_IDS),
        help="Experiment id to run (repeatable). Default: all E1–E4.",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Output directory (default: experiments/results).",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip matplotlib plot generation.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress lines.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    mode = "smoke" if args.smoke else (args.mode or "full")
    presets = presets_for_mode(mode)
    if args.no_plots:
        presets = replace(presets, write_plots=False)
    if args.results_dir:
        presets = replace(presets, results_dir=args.results_dir)

    summary = run_experiments(
        presets=presets,
        experiment_ids=args.experiments,
        progress=not args.quiet,
    )
    print(
        f"[experiments] done mode={summary['mode']} "
        f"episodes={summary['episode_count']} "
        f"dir={summary['results_dir']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
