#!/usr/bin/env python3
"""Create RTD and DPM/vector artifacts from a Fluent DPM summary.

The current Fluent 2023 R2 batch workflow advances transient DPM particles and
reports escaped-particle residence-time statistics, but its DPM sample file stays
header-only for this case. This postprocessor builds a fitted RTD from those
reported summary statistics and labels the output accordingly.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np


@dataclass(frozen=True)
class DpmSummary:
    count: int
    min_s: float
    max_s: float
    mean_s: float
    std_s: float
    injected_mass_kg: float
    escaped_mass_kg: float


DEFAULT_SUMMARY = DpmSummary(
    count=228,
    min_s=7.277e-01,
    max_s=1.353e00,
    mean_s=8.677e-01,
    std_s=1.813e-01,
    injected_mass_kg=2.000e-14,
    escaped_mass_kg=2.000e-14,
)


def beta_parameters(summary: DpmSummary) -> tuple[float, float]:
    span = summary.max_s - summary.min_s
    if span <= 0.0:
        raise ValueError("summary max_s must be greater than min_s")

    mu = (summary.mean_s - summary.min_s) / span
    var = summary.std_s**2 / span**2
    if not (0.0 < mu < 1.0 and 0.0 < var < mu * (1.0 - mu)):
        raise ValueError("summary moments cannot be represented by a bounded beta fit")

    common = mu * (1.0 - mu) / var - 1.0
    return mu * common, (1.0 - mu) * common


def beta_pdf(x: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    eps = np.finfo(float).eps
    x = np.clip(x, eps, 1.0 - eps)
    log_norm = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    log_pdf = (alpha - 1.0) * np.log(x) + (beta - 1.0) * np.log1p(-x) - log_norm
    return np.exp(log_pdf)


def fitted_distribution(summary: DpmSummary, points: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    alpha, beta = beta_parameters(summary)
    x = np.linspace(1.0e-5, 1.0 - 1.0e-5, points)
    t = summary.min_s + x * (summary.max_s - summary.min_s)
    pdf = beta_pdf(x, alpha, beta) / (summary.max_s - summary.min_s)
    return t, pdf


def fitted_quantiles(summary: DpmSummary, count: int) -> np.ndarray:
    t, pdf = fitted_distribution(summary, points=20000)
    cdf = np.cumsum((pdf[:-1] + pdf[1:]) * np.diff(t) * 0.5)
    cdf = np.concatenate(([0.0], cdf))
    cdf /= cdf[-1]
    q = (np.arange(count) + 0.5) / count
    return np.interp(q, cdf, t)


def write_summary(path: Path, summary: DpmSummary, alpha: float, beta: float) -> None:
    path.write_text(
        "\n".join(
            [
                "Fluent 2023 R2 transient DPM summary",
                f"escaped_parcels: {summary.count}",
                f"residence_time_min_s: {summary.min_s:.8g}",
                f"residence_time_max_s: {summary.max_s:.8g}",
                f"residence_time_mean_s: {summary.mean_s:.8g}",
                f"residence_time_std_s: {summary.std_s:.8g}",
                f"injected_mass_kg: {summary.injected_mass_kg:.8g}",
                f"escaped_mass_kg: {summary.escaped_mass_kg:.8g}",
                "",
                "RTD artifact note:",
                "Fluent's transient DPM run reported all outlet escapes, but the batch",
                "DPM sample file remained header-only. The RTD CSV/PNG/GIF are fitted",
                "from the summary using a bounded beta distribution.",
                f"beta_alpha: {alpha:.8g}",
                f"beta_beta: {beta:.8g}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_rtd_csv(path: Path, summary: DpmSummary, bins: int) -> None:
    samples = fitted_quantiles(summary, summary.count)
    weights, edges = np.histogram(samples, bins=bins, range=(summary.min_s, summary.max_s))
    width = float(edges[1] - edges[0])
    total = float(weights.sum())

    cumulative = 0.0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_s", "E_1_per_s", "F", "bin_weight", "source"])
        for left, right, weight in zip(edges[:-1], edges[1:], weights):
            cumulative += float(weight)
            center = 0.5 * float(left + right)
            density = float(weight) / (total * width) if total else 0.0
            writer.writerow([center, density, cumulative / total, int(weight), "dpm_summary_beta_fit"])


def write_fitted_samples_csv(path: Path, summary: DpmSummary) -> None:
    samples = fitted_quantiles(summary, summary.count)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parcel_index", "residence_time_s", "source"])
        for index, time_s in enumerate(samples, start=1):
            writer.writerow([index, time_s, "dpm_summary_beta_fit"])


def write_rtd_plot(path: Path, summary: DpmSummary, bins: int) -> None:
    import matplotlib.pyplot as plt

    samples = fitted_quantiles(summary, summary.count)
    weights, edges = np.histogram(samples, bins=bins, range=(summary.min_s, summary.max_s), density=False)
    width = float(edges[1] - edges[0])
    density = weights / (weights.sum() * width)
    centers = 0.5 * (edges[:-1] + edges[1:])

    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.step(centers, density, where="mid", color="#1e6f8c", linewidth=2.2, label="Fitted parcel histogram")
    ax.bar(centers, density, width=width * 0.92, color="#d9eef5", edgecolor="none", align="center")
    ax.axvline(summary.mean_s, color="#2f2f2f", linewidth=1.1, linestyle="--", label="Mean")
    ax.set_xlabel("Residence time, t [s]")
    ax.set_ylabel("E(t) [1/s]")
    ax.set_title("RTD from Fluent DPM Summary Fit")
    ax.grid(True, color="#d7d7d7", linewidth=0.8)
    ax.legend(frameon=False)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def inlet_face_centers(case_path: Path) -> np.ndarray:
    with h5py.File(case_path, "r") as h5:
        zones = h5["meshes/1/faces/zoneTopology"]
        names = b";".join(zones["name"][()]).decode("utf-8").split(";")
        inlet_index = names.index("inlet")
        lo = int(zones["minId"][inlet_index])
        hi = int(zones["maxId"][inlet_index])
        coords = h5["meshes/1/nodes/coords/4"][()]
        nnodes = h5["meshes/1/faces/nodes/1/nnodes"][()]
        nodes = h5["meshes/1/faces/nodes/1/nodes"][()]
        starts = np.concatenate(([0], np.cumsum(nnodes)))

        centers = []
        for face_id in range(lo, hi + 1):
            face_index = face_id - 1
            node_ids = nodes[starts[face_index] : starts[face_index + 1]].astype(int) - 1
            centers.append(coords[node_ids].mean(axis=0))
        return np.asarray(centers)


def write_dpm_gif(path: Path, case_path: Path, summary: DpmSummary) -> None:
    import matplotlib.pyplot as plt
    from PIL import Image

    centers = inlet_face_centers(case_path)
    radius = 0.0127
    radial = np.sqrt(centers[:, 1] ** 2 + centers[:, 2] ** 2)
    order = np.argsort(radial)
    times = fitted_quantiles(summary, len(centers))
    residence = np.empty_like(times)
    residence[order] = np.sort(times)

    y = np.clip(centers[:, 1] / radius, -1.0, 1.0)
    release_duration = 0.02
    releases = np.linspace(0.0, release_duration, len(centers), endpoint=False)
    duration = summary.max_s + release_duration + 0.25

    vector_y = np.linspace(-0.9, 0.9, 9)
    vector_speed = np.maximum(0.0, 1.0 - vector_y**2)

    frames: list[Image.Image] = []
    for frame_index, current_time in enumerate(np.linspace(0.0, duration, 64)):
        fig, ax = plt.subplots(figsize=(7.2, 3.0), constrained_layout=True)
        ax.set_xlim(-0.04, 1.04)
        ax.set_ylim(-1.15, 1.15)
        ax.set_facecolor("#f7fbfc")

        ax.fill_between([0, 1], [-1, -1], [1, 1], color="#ecf2f4")
        ax.plot([0, 1], [1, 1], color="#59656b", linewidth=1.2)
        ax.plot([0, 1], [-1, -1], color="#59656b", linewidth=1.2)

        ax.quiver(
            np.full_like(vector_y, 0.18),
            vector_y,
            0.18 * vector_speed,
            np.zeros_like(vector_y),
            angles="xy",
            scale_units="xy",
            scale=1,
            color="#335c67",
            width=0.004,
        )

        age = current_time - releases
        active = (age >= 0.0) & (age <= residence)
        escaped = age > residence
        x_active = np.clip(age[active] / residence[active], 0.0, 1.0)

        ax.scatter(np.zeros(np.count_nonzero(~active & ~escaped)), y[~active & ~escaped], s=10, c="#9aa4a9", alpha=0.25)
        if np.any(active):
            ax.scatter(x_active, y[active], s=18, c=age[active], cmap="viridis", vmin=0.0, vmax=summary.max_s)
        if np.any(escaped):
            ax.scatter(np.ones(np.count_nonzero(escaped)), y[escaped], s=8, c="#d95f02", alpha=0.35)

        ax.text(0.02, 1.03, "inlet", fontsize=9, color="#28343a")
        ax.text(0.92, 1.03, "outlet", fontsize=9, color="#28343a")
        ax.text(0.40, -1.10, f"t = {current_time:.2f} s after DPM pulse", fontsize=9, color="#28343a")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        fig.canvas.draw()
        width, height = fig.canvas.get_width_height()
        image = np.asarray(fig.canvas.buffer_rgba()).reshape((height, width, 4))
        frames.append(Image.fromarray(image[:, :, :3].copy()))
        plt.close(fig)

    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
        optimize=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=Path("case/dpm.cas.h5"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--bins", type=int, default=48)
    parser.add_argument("--count", type=int, default=DEFAULT_SUMMARY.count)
    parser.add_argument("--min-s", type=float, default=DEFAULT_SUMMARY.min_s)
    parser.add_argument("--max-s", type=float, default=DEFAULT_SUMMARY.max_s)
    parser.add_argument("--mean-s", type=float, default=DEFAULT_SUMMARY.mean_s)
    parser.add_argument("--std-s", type=float, default=DEFAULT_SUMMARY.std_s)
    parser.add_argument("--injected-mass-kg", type=float, default=DEFAULT_SUMMARY.injected_mass_kg)
    parser.add_argument("--escaped-mass-kg", type=float, default=DEFAULT_SUMMARY.escaped_mass_kg)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary = DpmSummary(
        count=args.count,
        min_s=args.min_s,
        max_s=args.max_s,
        mean_s=args.mean_s,
        std_s=args.std_s,
        injected_mass_kg=args.injected_mass_kg,
        escaped_mass_kg=args.escaped_mass_kg,
    )
    alpha, beta = beta_parameters(summary)

    write_summary(args.output_dir / "dpm_summary.txt", summary, alpha, beta)
    write_rtd_csv(args.output_dir / "rtd_curve.csv", summary, args.bins)
    write_fitted_samples_csv(args.output_dir / "rtd_fitted_parcel_times.csv", summary)
    write_rtd_plot(args.output_dir / "rtd_curve.png", summary, args.bins)
    write_dpm_gif(args.output_dir / "dpm_vectors.gif", args.case, summary)

    print(f"beta_alpha={alpha:.8g}")
    print(f"beta_beta={beta:.8g}")
    print(f"wrote {args.output_dir / 'dpm_summary.txt'}")
    print(f"wrote {args.output_dir / 'rtd_curve.csv'}")
    print(f"wrote {args.output_dir / 'rtd_fitted_parcel_times.csv'}")
    print(f"wrote {args.output_dir / 'rtd_curve.png'}")
    print(f"wrote {args.output_dir / 'dpm_vectors.gif'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
