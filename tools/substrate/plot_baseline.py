"""Render verified baseline traces offline; matplotlib is an analysis dependency."""

import argparse
from pathlib import Path
import numpy as np

from .integrity import EvidenceRun, digest, strict_json, verify_bundle, verify_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--verification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    verify_manifest(args.capture)
    verified = verify_bundle(args.verification)
    if verified["capture_manifest_sha256"] != digest(args.capture / "manifest.json"):
        raise ValueError("verification belongs to another capture")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with EvidenceRun(args.output, {"operation": "verified_trace_plot"}) as run:
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
        colors = {
            "source_1": "#1b6ca8",
            "source_015": "#d47800",
            "source_03": "#10805b",
            "model_only": "#8760a8",
            "first_inference_only": "#cc4959",
            "source_variable": "#9a7413",
        }
        for name in colors:
            rows = [
                strict_json(line)
                for line in (args.capture / (name + ".jsonl")).read_text().splitlines()
            ]
            t = np.array([r["time"] for r in rows])
            q = np.array([r["qpos"] for r in rows])
            v = np.array([r["qvel"] for r in rows])
            vx = (
                (1 - 2 * (q[:, 5] ** 2 + q[:, 6] ** 2)) * v[:, 0]
                + 2 * (q[:, 4] * q[:, 5] + q[:, 3] * q[:, 6]) * v[:, 1]
                + 2 * (q[:, 4] * q[:, 6] - q[:, 3] * q[:, 5]) * v[:, 2]
            )
            if name in ("source_1", "source_015", "source_03", "model_only"):
                axes[0, 0].plot(
                    t[::5], vx[::5], color=colors[name], linewidth=0.9, label=name
                )
            if name == "source_variable":
                axes[0, 1].plot(t[::5], vx[::5], label="body vx", linewidth=0.9)
                axes[0, 1].step(
                    t,
                    [r["command"][0] for r in rows],
                    where="post",
                    color="black",
                    linestyle="--",
                    label="command",
                )
            if name in (
                "source_1",
                "first_inference_only",
                "source_variable",
                "model_only",
            ):
                axes[1, 0].plot(t[::5], q[::5, 1], color=colors[name], label=name)
        axes[0, 0].set(
            title="Source flat: speed is command-dependent",
            ylabel="Body forward velocity (m/s)",
        )
        axes[0, 1].set(
            title="Variable speed: longitudinal tracking",
            ylabel="Body forward velocity (m/s)",
        )
        axes[1, 0].axhline(0.3, color="black", linestyle="--", linewidth=1)
        axes[1, 0].axhline(-0.3, color="black", linestyle="--", linewidth=1)
        axes[1, 0].set(
            title="Lateral displacement: frozen limit +/-0.3 m",
            ylabel="World y displacement (m)",
        )
        rows = [
            strict_json(line)
            for line in (args.capture / "source_stairs.jsonl").read_text().splitlines()
        ]
        axes[1, 1].plot(
            [r["time"] for r in rows], [r["qpos"][0] for r in rows], label="base x"
        )
        axes[1, 1].plot(
            [r["time"] for r in rows], [r["qpos"][2] for r in rows], label="base z"
        )
        axes[1, 1].axvline(
            rows[-1]["time"],
            color="#cc4959",
            linestyle="--",
            label="base contact: safety stop",
        )
        axes[1, 1].set(
            title="23 cm stairs: base contact at 2.5 s",
            ylabel="Position (m)",
            xlim=(0, 3),
        )
        for ax in axes.flat:
            ax.set_xlabel("Simulated time (s)")
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8, loc="best")
        fig.suptitle(
            "Public CTS checkpoint: frozen source baseline, 2026-09-23", fontsize=15
        )
        fig.savefig(run.path / "tracking.png", dpi=160)
        plt.close(fig)
        run.result.update(
            status="ENGINEERING_ADMITTED",
            physics_steps=0,
            capture_manifest_sha256=digest(args.capture / "manifest.json"),
            plot_sampling="every fifth recorded state; no smoothing",
            matplotlib_version=matplotlib.__version__,
        )


if __name__ == "__main__":
    main()
