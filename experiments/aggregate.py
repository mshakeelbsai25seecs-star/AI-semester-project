"""Averages and variance over seeded episode results."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from experiments.episode import EpisodeResult

METRIC_FIELDS: Tuple[str, ...] = (
    "survival_steps",
    "coins",
    "score",
    "nodes_expanded_total",
    "nodes_expanded_mean",
    "nodes_expanded_max",
    "decision_time_total_s",
    "decision_time_mean_s",
    "memory_or_policy_size",
    "decisions",
)


@dataclass
class AggregateRow:
    """Mean ± variance (sample) for one group of episodes."""

    group: Dict[str, Any]
    n: int
    means: Dict[str, float]
    variances: Dict[str, float]
    stdevs: Dict[str, float]
    seeds: List[int]

    def to_row(self) -> Dict[str, Any]:
        row: Dict[str, Any] = dict(self.group)
        row["n"] = self.n
        row["seeds"] = ",".join(str(s) for s in self.seeds)
        for key in METRIC_FIELDS:
            row[f"{key}_mean"] = self.means.get(key, 0.0)
            row[f"{key}_var"] = self.variances.get(key, 0.0)
            row[f"{key}_std"] = self.stdevs.get(key, 0.0)
        return row


def _mean_var(values: Sequence[float]) -> Tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0, 0.0
    mean = statistics.fmean(values)
    var = statistics.variance(values)
    return mean, var, math.sqrt(var)


def group_key(result: EpisodeResult, fields: Sequence[str]) -> Tuple[Any, ...]:
    out: List[Any] = []
    for name in fields:
        if hasattr(result, name):
            out.append(getattr(result, name))
        else:
            out.append(result.extra.get(name))
    return tuple(out)


def aggregate_results(
    results: Iterable[EpisodeResult],
    group_by: Sequence[str] = ("experiment", "agent", "label"),
) -> List[AggregateRow]:
    buckets: Dict[Tuple[Any, ...], List[EpisodeResult]] = defaultdict(list)
    for result in results:
        buckets[group_key(result, group_by)].append(result)

    rows: List[AggregateRow] = []
    for key, items in sorted(buckets.items(), key=lambda kv: [str(x) for x in kv[0]]):
        group = {field: value for field, value in zip(group_by, key)}
        means: Dict[str, float] = {}
        variances: Dict[str, float] = {}
        stdevs: Dict[str, float] = {}
        for metric in METRIC_FIELDS:
            values = [float(getattr(item, metric)) for item in items]
            mean, var, std = _mean_var(values)
            means[metric] = mean
            variances[metric] = var
            stdevs[metric] = std
        rows.append(
            AggregateRow(
                group=group,
                n=len(items),
                means=means,
                variances=variances,
                stdevs=stdevs,
                seeds=sorted({item.seed for item in items}),
            )
        )
    return rows
