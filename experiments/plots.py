"""Matplotlib plots for E1–E4 summaries."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from experiments.aggregate import AggregateRow
from experiments.io_util import ensure_dir


def _maybe_pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _bar_with_err(
    path: Path,
    labels: Sequence[str],
    means: Sequence[float],
    stds: Sequence[float],
    *,
    title: str,
    ylabel: str,
    xlabel: str = "",
) -> Path:
    plt = _maybe_pyplot()
    ensure_dir(path.parent)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = list(range(len(labels)))
    ax.bar(xs, means, yerr=stds, capsize=4, color="#2f6fed", ecolor="#1a1a1a", alpha=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(list(labels), rotation=20, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def _line_with_err(
    path: Path,
    xs: Sequence[float],
    series: Sequence[tuple[str, Sequence[float], Sequence[float]]],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
) -> Path:
    plt = _maybe_pyplot()
    ensure_dir(path.parent)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, means, stds in series:
        ax.errorbar(xs, means, yerr=stds, marker="o", capsize=3, label=name)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_e1_agent_comparison(rows: Sequence[AggregateRow], out_dir: Path) -> List[Path]:
    ordered = sorted(rows, key=lambda r: str(r.group.get("agent", "")))
    labels = [str(r.group.get("agent", "?")) for r in ordered]
    paths = [
        _bar_with_err(
            out_dir / "e1_survival_steps.png",
            labels,
            [r.means["survival_steps"] for r in ordered],
            [r.stdevs["survival_steps"] for r in ordered],
            title="E1 agent comparison — survival steps",
            ylabel="Steps (mean ± std)",
            xlabel="Agent",
        ),
        _bar_with_err(
            out_dir / "e1_coins.png",
            labels,
            [r.means["coins"] for r in ordered],
            [r.stdevs["coins"] for r in ordered],
            title="E1 agent comparison — coins",
            ylabel="Coins (mean ± std)",
            xlabel="Agent",
        ),
        _bar_with_err(
            out_dir / "e1_decision_time.png",
            labels,
            [r.means["decision_time_mean_s"] for r in ordered],
            [r.stdevs["decision_time_mean_s"] for r in ordered],
            title="E1 agent comparison — mean decision time",
            ylabel="Seconds / decision (mean ± std)",
            xlabel="Agent",
        ),
        _bar_with_err(
            out_dir / "e1_nodes_expanded.png",
            labels,
            [r.means["nodes_expanded_mean"] for r in ordered],
            [r.stdevs["nodes_expanded_mean"] for r in ordered],
            title="E1 agent comparison — nodes expanded / decision",
            ylabel="Nodes (mean ± std)",
            xlabel="Agent",
        ),
    ]
    return paths


def plot_e2_effect_of_k(rows: Sequence[AggregateRow], out_dir: Path) -> List[Path]:
    agents = sorted({str(r.group.get("agent", "")) for r in rows})
    ks = sorted(
        {int(r.group.get("observation_k", r.group.get("label", 0))) for r in rows}
    )
    index = {
        (
            str(r.group.get("agent")),
            int(r.group.get("observation_k", r.group.get("label", 0))),
        ): r
        for r in rows
    }

    def series_for(metric: str):
        out = []
        for agent in agents:
            means, stds = [], []
            for k in ks:
                row = index.get((agent, k))
                means.append(row.means[metric] if row else 0.0)
                stds.append(row.stdevs[metric] if row else 0.0)
            out.append((agent, means, stds))
        return out

    return [
        _line_with_err(
            out_dir / "e2_survival_vs_k.png",
            ks,
            series_for("survival_steps"),
            title="E2 effect of K — survival steps",
            xlabel="Observation K",
            ylabel="Steps (mean ± std)",
        ),
        _line_with_err(
            out_dir / "e2_coins_vs_k.png",
            ks,
            series_for("coins"),
            title="E2 effect of K — coins",
            xlabel="Observation K",
            ylabel="Coins (mean ± std)",
        ),
        _line_with_err(
            out_dir / "e2_nodes_vs_k.png",
            ks,
            series_for("nodes_expanded_mean"),
            title="E2 effect of K — nodes / decision",
            xlabel="Observation K",
            ylabel="Nodes (mean ± std)",
        ),
        _line_with_err(
            out_dir / "e2_time_vs_k.png",
            ks,
            series_for("decision_time_mean_s"),
            title="E2 effect of K — decision time",
            xlabel="Observation K",
            ylabel="Seconds / decision (mean ± std)",
        ),
    ]


def plot_e3_speed_schedule(rows: Sequence[AggregateRow], out_dir: Path) -> List[Path]:
    schedules: List[str] = []
    seen = set()
    for r in rows:
        label = str(r.group.get("label") or r.group.get("speed_schedule") or "")
        if label not in seen:
            seen.add(label)
            schedules.append(label)
    agents = sorted({str(r.group.get("agent", "")) for r in rows})
    index = {
        (
            str(r.group.get("agent")),
            str(r.group.get("label") or r.group.get("speed_schedule") or ""),
        ): r
        for r in rows
    }
    plt = _maybe_pyplot()
    ensure_dir(out_dir)
    paths: List[Path] = []
    width = 0.8 / max(1, len(agents))
    xs = list(range(len(schedules)))
    for metric, title, fname in (
        ("survival_steps", "E3 speed schedule — survival steps", "e3_survival_by_speed.png"),
        ("coins", "E3 speed schedule — coins", "e3_coins_by_speed.png"),
    ):
        fig, ax = plt.subplots(figsize=(9, 4.8))
        for i, agent in enumerate(agents):
            means, stds = [], []
            for sched in schedules:
                row = index.get((agent, sched))
                means.append(row.means[metric] if row else 0.0)
                stds.append(row.stdevs[metric] if row else 0.0)
            offset = (i - (len(agents) - 1) / 2) * width
            ax.bar(
                [x + offset for x in xs],
                means,
                width=width,
                yerr=stds,
                capsize=3,
                label=agent,
            )
        ax.set_xticks(xs)
        ax.set_xticklabels(schedules)
        ax.set_title(title)
        ax.set_ylabel(f"{metric} (mean ± std)")
        ax.set_xlabel("Speed schedule")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        fig.tight_layout()
        path = out_dir / fname
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    return paths


def plot_e4_climbing(rows: Sequence[AggregateRow], out_dir: Path) -> List[Path]:
    agents = sorted({str(r.group.get("agent", "")) for r in rows})
    climb_labels: List[str] = []
    for r in rows:
        raw = r.group.get("label")
        if raw is None:
            raw = r.group.get("train_climbing_enabled")
        text = str(raw)
        if text not in climb_labels:
            climb_labels.append(text)
    index = {}
    for r in rows:
        raw = r.group.get("label")
        if raw is None:
            raw = r.group.get("train_climbing_enabled")
        index[(str(r.group.get("agent")), str(raw))] = r

    plt = _maybe_pyplot()
    ensure_dir(out_dir)
    paths: List[Path] = []
    for metric, title, fname in (
        ("survival_steps", "E4 train climbing — survival steps", "e4_survival_climbing.png"),
        ("coins", "E4 train climbing — coins", "e4_coins_climbing.png"),
    ):
        fig, ax = plt.subplots(figsize=(9, 4.8))
        width = 0.8 / max(1, len(climb_labels))
        xs = list(range(len(agents)))
        for i, climb in enumerate(climb_labels):
            means, stds = [], []
            for agent in agents:
                row = index.get((agent, climb))
                means.append(row.means[metric] if row else 0.0)
                stds.append(row.stdevs[metric] if row else 0.0)
            offset = (i - (len(climb_labels) - 1) / 2) * width
            ax.bar(
                [x + offset for x in xs],
                means,
                width=width,
                yerr=stds,
                capsize=3,
                label=f"climb={climb}",
            )
        ax.set_xticks(xs)
        ax.set_xticklabels(agents, rotation=15, ha="right")
        ax.set_title(title)
        ax.set_ylabel(f"{metric} (mean ± std)")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        fig.tight_layout()
        path = out_dir / fname
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    return paths


def write_plots_for_experiment(
    experiment_id: str,
    aggregates: Sequence[AggregateRow],
    out_dir: Path,
) -> List[Path]:
    exp = experiment_id.lower()
    if not aggregates:
        return []
    if exp == "e1":
        return plot_e1_agent_comparison(aggregates, out_dir)
    if exp == "e2":
        return plot_e2_effect_of_k(aggregates, out_dir)
    if exp == "e3":
        return plot_e3_speed_schedule(aggregates, out_dir)
    if exp == "e4":
        return plot_e4_climbing(aggregates, out_dir)
    return []
