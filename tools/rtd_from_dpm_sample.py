#!/usr/bin/env python3
"""Convert Fluent DPM sample output into a normalized RTD curve."""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


NUMBER_RE = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)


@dataclass(frozen=True)
class Sample:
    arrival_time_s: float
    birth_time_s: float
    residence_time_s: float
    sample_weight: float
    parcel_mass_kg: float
    particle_mass_kg: float


def _numbers_from_line(line: str) -> list[float]:
    return [float(match.group(0)) for match in NUMBER_RE.finditer(line)]


def read_samples(path: Path) -> list[Sample]:
    samples: list[Sample] = []

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        values = _numbers_from_line(line)
        if len(values) < 14:
            continue

        # Fluent's par_fprintf sorting keys may be present in some outputs.
        # The UDF's payload is the last 14 numeric columns.
        payload = values[-14:]
        samples.append(
            Sample(
                arrival_time_s=payload[0],
                birth_time_s=payload[1],
                residence_time_s=payload[2],
                sample_weight=payload[3],
                parcel_mass_kg=payload[4],
                particle_mass_kg=payload[5],
            )
        )

    return samples


def sample_weight(sample: Sample, mode: str) -> float:
    if mode == "none":
        return 1.0

    if mode == "mass":
        if sample.parcel_mass_kg > 0.0:
            return sample.parcel_mass_kg
        if sample.sample_weight > 0.0:
            return sample.sample_weight
        return 1.0

    if sample.sample_weight > 0.0:
        return sample.sample_weight
    return 1.0


def build_histogram(
    samples: Iterable[Sample],
    bins: int,
    bin_width: float | None,
    weight_mode: str,
) -> tuple[list[float], list[float], float]:
    pairs = valid_weighted_times(samples, weight_mode)

    if not pairs:
        raise ValueError("No valid DPM residence-time samples were found.")

    times = [time for time, _ in pairs]
    t_min = min(times)
    t_max = max(times)

    if bin_width is not None:
        if bin_width <= 0.0:
            raise ValueError("--bin-width must be positive.")
        first_edge = math.floor(t_min / bin_width) * bin_width
        last_edge = math.ceil(t_max / bin_width) * bin_width
        if last_edge <= first_edge:
            last_edge = first_edge + bin_width
        bin_count = max(1, math.ceil((last_edge - first_edge) / bin_width))
    else:
        if bins <= 0:
            raise ValueError("--bins must be positive.")
        bin_count = bins
        span = t_max - t_min
        if span == 0.0:
            span = max(abs(t_max), 1.0) * 0.02
            t_min -= span / 2.0
        bin_width = span / bin_count
        first_edge = t_min

    weights = [0.0 for _ in range(bin_count)]
    for time, weight in pairs:
        index = int((time - first_edge) / bin_width)
        if index < 0:
            index = 0
        elif index >= bin_count:
            index = bin_count - 1
        weights[index] += weight

    centers = [first_edge + (index + 0.5) * bin_width for index in range(bin_count)]
    return centers, weights, bin_width


def write_rtd_csv(
    output_path: Path,
    centers: list[float],
    weights: list[float],
    bin_width: float,
) -> None:
    total_weight = sum(weights)
    if total_weight <= 0.0:
        raise ValueError("Total sample weight is zero.")

    cumulative = 0.0
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_s", "E_1_per_s", "F", "bin_weight"])

        for center, weight in zip(centers, weights):
            cumulative += weight
            density = weight / (total_weight * bin_width)
            writer.writerow([center, density, cumulative / total_weight, weight])


def write_plot(path: Path, centers: list[float], weights: list[float], bin_width: float) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for --plot") from exc

    total_weight = sum(weights)
    densities = [weight / (total_weight * bin_width) for weight in weights]

    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(centers, densities, color="#1f6f8b", linewidth=2.0)
    ax.fill_between(centers, densities, color="#d7eef5")
    ax.set_xlabel("Residence time, t [s]")
    ax.set_ylabel("E(t) [1/s]")
    ax.grid(True, color="#d9d9d9", linewidth=0.8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def valid_weighted_times(samples: Iterable[Sample], weight_mode: str) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for sample in samples:
        weight = sample_weight(sample, weight_mode)
        if (
            math.isfinite(sample.residence_time_s)
            and sample.residence_time_s >= 0.0
            and math.isfinite(weight)
            and weight > 0.0
        ):
            pairs.append((sample.residence_time_s, weight))
    return pairs


def summarize(samples: list[Sample], weight_mode: str) -> dict[str, float]:
    weighted = valid_weighted_times(samples, weight_mode)
    if not weighted:
        raise ValueError("No valid DPM residence-time samples were found.")

    total_weight = sum(weight for _, weight in weighted)
    mean = sum(time * weight for time, weight in weighted) / total_weight
    variance = sum(weight * (time - mean) ** 2 for time, weight in weighted) / total_weight
    return {
        "samples": float(len(weighted)),
        "total_weight": total_weight,
        "mean_s": mean,
        "std_s": math.sqrt(max(variance, 0.0)),
        "min_s": min(time for time, _ in weighted),
        "max_s": max(time for time, _ in weighted),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a normalized RTD curve from rtd_dpm_output.c sample data."
    )
    parser.add_argument("sample_file", type=Path, help="Fluent DPM sample output file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("rtd_curve.csv"),
        help="CSV file to write",
    )
    parser.add_argument("--bins", type=int, default=80, help="number of RTD bins")
    parser.add_argument(
        "--bin-width",
        type=float,
        default=None,
        help="fixed RTD bin width in seconds; overrides --bins",
    )
    parser.add_argument(
        "--weight",
        choices=("parcel", "mass", "none"),
        default="parcel",
        help="weighting for RTD normalization",
    )
    parser.add_argument(
        "--plot",
        type=Path,
        default=None,
        help="optional PNG path; requires matplotlib",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    samples = read_samples(args.sample_file)
    centers, weights, bin_width = build_histogram(
        samples=samples,
        bins=args.bins,
        bin_width=args.bin_width,
        weight_mode=args.weight,
    )
    write_rtd_csv(args.output, centers, weights, bin_width)

    if args.plot is not None:
        write_plot(args.plot, centers, weights, bin_width)

    stats = summarize(samples, args.weight)
    print(f"Read samples: {int(stats['samples'])}")
    print(f"Total weight: {stats['total_weight']:.8g}")
    print(f"Mean residence time [s]: {stats['mean_s']:.8g}")
    print(f"Std residence time [s]: {stats['std_s']:.8g}")
    print(f"Min/Max residence time [s]: {stats['min_s']:.8g} / {stats['max_s']:.8g}")
    print(f"Wrote RTD CSV: {args.output}")
    if args.plot is not None:
        print(f"Wrote RTD plot: {args.plot}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
