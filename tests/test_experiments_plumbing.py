"""Tests for experiments runner plumbing (not long evals)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from experiments.aggregate import aggregate_results
from experiments.defaults import agent_kwargs_for, presets_for_mode, smoke_presets
from experiments.episode import EpisodeResult, run_episode
from experiments.io_util import read_csv, run_metadata, write_csv
from experiments.suite import EXPERIMENT_IDS, main, run_experiments
from game import GameConfig


def test_smoke_presets_are_tiny():
    presets = smoke_presets()
    assert presets.mode == "smoke"
    assert len(presets.seeds) <= 3
    assert presets.max_steps <= 40
    assert set(presets.experiments) == set(EXPERIMENT_IDS)


def test_run_episode_is_seeded_and_metric_complete():
    cfg = GameConfig(observation_k=3)
    a = run_episode(
        "baseline",
        seed=42,
        config=cfg,
        max_steps=20,
        experiment="unit",
        mode="smoke",
        agent_kwargs={},
    )
    b = run_episode(
        "baseline",
        seed=42,
        config=cfg,
        max_steps=20,
        experiment="unit",
        mode="smoke",
        agent_kwargs={},
    )
    assert a.survival_steps == b.survival_steps
    assert a.coins == b.coins
    assert a.seed == 42
    assert a.decisions >= 1
    assert a.decision_time_total_s >= 0.0
    row = a.to_row()
    assert "survival_steps" in row
    assert "nodes_expanded_mean" in row


def test_run_episode_records_search_nodes():
    cfg = GameConfig(observation_k=3)
    result = run_episode(
        "lookahead",
        seed=7,
        config=cfg,
        max_steps=12,
        experiment="unit",
        mode="smoke",
    )
    assert result.nodes_expanded_total >= 0
    assert result.nodes_expanded_max >= 0


def test_run_episode_records_mdp_policy_size():
    cfg = GameConfig(observation_k=3)
    kwargs = agent_kwargs_for(smoke_presets(), "mdp")
    result = run_episode(
        "mdp",
        seed=3,
        config=cfg,
        max_steps=8,
        experiment="unit",
        mode="smoke",
        agent_kwargs=kwargs,
    )
    assert result.memory_or_policy_size > 0


def test_aggregate_mean_and_variance():
    samples = [
        EpisodeResult(
            experiment="e1",
            agent="random",
            seed=1,
            survival_steps=10,
            coins=1,
            score=1.0,
            crashed=True,
            decisions=10,
            nodes_expanded_total=0,
            nodes_expanded_mean=0.0,
            nodes_expanded_max=0,
            decision_time_total_s=0.1,
            decision_time_mean_s=0.01,
            memory_or_policy_size=0.0,
            observation_k=4,
            initial_speed=1.0,
            speed_increment=0.05,
            speed_interval_rows=50,
            train_climbing_enabled=True,
            max_steps=20,
            label="default",
        ),
        EpisodeResult(
            experiment="e1",
            agent="random",
            seed=2,
            survival_steps=20,
            coins=3,
            score=2.0,
            crashed=True,
            decisions=20,
            nodes_expanded_total=0,
            nodes_expanded_mean=0.0,
            nodes_expanded_max=0,
            decision_time_total_s=0.2,
            decision_time_mean_s=0.01,
            memory_or_policy_size=0.0,
            observation_k=4,
            initial_speed=1.0,
            speed_increment=0.05,
            speed_interval_rows=50,
            train_climbing_enabled=True,
            max_steps=20,
            label="default",
        ),
    ]
    rows = aggregate_results(samples, group_by=("experiment", "agent"))
    assert len(rows) == 1
    assert rows[0].n == 2
    assert rows[0].means["survival_steps"] == pytest.approx(15.0)
    assert rows[0].variances["survival_steps"] == pytest.approx(50.0)
    assert rows[0].stdevs["survival_steps"] == pytest.approx(50.0**0.5)


def test_run_e1_smoke_writes_outputs(tmp_path: Path):
    presets = replace(
        presets_for_mode("smoke"),
        agents=("baseline", "random"),
        seeds=(42,),
        max_steps=10,
        write_plots=True,
        results_dir=str(tmp_path),
        experiments=("e1",),
    )
    summary = run_experiments(presets=presets, progress=False)
    assert summary["episode_count"] == 2
    assert (tmp_path / "e1_episodes.csv").exists()
    assert (tmp_path / "e1_summary.csv").exists()
    assert (tmp_path / "e1_meta.json").exists()
    assert (tmp_path / "run_meta.json").exists()
    assert (tmp_path / "e1_survival_steps.png").exists()
    rows = read_csv(tmp_path / "e1_episodes.csv")
    assert {r["agent"] for r in rows} == {"baseline", "random"}
    assert all(r["seed"] == "42" for r in rows)


def test_run_experiments_all_ids_smoke(tmp_path: Path):
    presets = replace(
        smoke_presets(),
        agents=("baseline",),
        seeds=(42,),
        max_steps=8,
        k_values=(2, 3),
        speed_schedules=(("default", 1.0, 0.05, 50), ("fast", 1.5, 0.1, 30)),
        results_dir=str(tmp_path),
        write_plots=False,
    )
    summary = run_experiments(presets=presets, progress=False)
    assert set(summary["experiments"]) == {"e1", "e2", "e3", "e4"}
    assert summary["episode_count"] == 1 + 2 + 2 + 2
    for exp_id in EXPERIMENT_IDS:
        assert (tmp_path / f"{exp_id}_episodes.csv").exists()
        assert (tmp_path / f"{exp_id}_summary.csv").exists()


def test_cli_smoke_e1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    code = main(
        [
            "--smoke",
            "--experiment",
            "e1",
            "--results-dir",
            str(tmp_path / "out"),
            "--no-plots",
            "--quiet",
        ]
    )
    # Override default smoke agents via env is not available; CLI uses full
    # smoke agent list. Cap is still tiny (15 steps, cheap kwargs).
    assert code == 0
    assert (tmp_path / "out" / "e1_episodes.csv").exists()
    meta = (tmp_path / "out" / "e1_meta.json").read_text(encoding="utf-8")
    assert "smoke" in meta
    assert "seeds" in meta


def test_metadata_includes_repro_fields():
    meta = run_metadata(smoke_presets(), argv=["python", "-m", "experiments", "--smoke"])
    assert meta["mode"] == "smoke"
    assert meta["seeds"]
    assert "python" in meta
    assert "platform" in meta


def test_write_csv_roundtrip(tmp_path: Path):
    path = tmp_path / "rows.csv"
    write_csv(path, [{"a": 1, "b": "x"}, {"a": 2, "b": "y", "c": 3}])
    rows = read_csv(path)
    assert rows[0]["a"] == "1"
    assert rows[1]["c"] == "3"
