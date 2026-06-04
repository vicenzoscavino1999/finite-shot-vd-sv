"""Deterministic white-box instance ensemble for Fase-0 freeze artifacts."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from vd_sv.qaoa import QAOAInstance


def sector_weight_for_size(n: int, rule: str) -> int:
    if rule == "n_over_2_minus_1":
        return n // 2 - 1
    raise ValueError(f"unknown sector weight rule: {rule}")


def generate_candidate(
    n: int,
    sector_weight: int,
    candidate_index: int,
    master_seed: int,
    extra_edge_prob: float,
    weight_low: float,
    weight_high: float,
) -> QAOAInstance:
    """Generate one deterministic connected weighted graph candidate."""
    seed = [int(master_seed), int(n), int(candidate_index)]
    rng = np.random.Generator(np.random.PCG64(seed))
    edges = random_connected_graph(n, extra_edge_prob, rng)
    weights = tuple(float(x) for x in rng.uniform(weight_low, weight_high, size=len(edges)))
    return QAOAInstance(
        n=n,
        weight=sector_weight,
        edges=edges,
        weights=weights,
        mixer_edges=edges,
        name=f"g{n}_k{sector_weight}_c{candidate_index:03d}",
    )


def random_connected_graph(
    n: int,
    extra_edge_prob: float,
    rng: np.random.Generator,
) -> tuple[tuple[int, int], ...]:
    """Random spanning tree plus independent extra edges."""
    if n < 2:
        raise ValueError("n must be at least 2")
    if not 0.0 <= extra_edge_prob <= 1.0:
        raise ValueError("extra_edge_prob must be in [0,1]")

    edges = set(_random_spanning_tree_edges(n, rng))
    for i in range(n):
        for j in range(i + 1, n):
            edge = (i, j)
            if edge not in edges and rng.random() < extra_edge_prob:
                edges.add(edge)
    return tuple(sorted(edges))


def _random_spanning_tree_edges(
    n: int,
    rng: np.random.Generator,
) -> tuple[tuple[int, int], ...]:
    if n == 2:
        return ((0, 1),)

    prufer = rng.integers(0, n, size=n - 2)
    degree = np.ones(n, dtype=np.int64)
    for node in prufer:
        degree[int(node)] += 1

    edges = []
    for node in prufer:
        leaves = np.flatnonzero(degree == 1)
        leaf = int(leaves[0])
        other = int(node)
        edges.append(_ordered_edge(leaf, other))
        degree[leaf] -= 1
        degree[other] -= 1

    leaves = np.flatnonzero(degree == 1)
    edges.append(_ordered_edge(int(leaves[0]), int(leaves[1])))
    return tuple(edges)


def _ordered_edge(i: int, j: int) -> tuple[int, int]:
    return (i, j) if i < j else (j, i)


def edge_tuple(value: Sequence[Sequence[int]]) -> tuple[tuple[int, int], ...]:
    return tuple((int(i), int(j)) for i, j in value)
