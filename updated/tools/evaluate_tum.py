"""Evaluate saved SfM camera centers against withheld TUM motion capture.

This is evaluation only: it never supplies a reference pose to reconstruction.
Monocular scale, orientation and origin are fitted with one proper Sim(3).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def align_similarity(estimated, reference):
    """Fit reference ~= scale * estimated @ rotation.T + translation."""
    x, y = np.asarray(estimated, dtype=float), np.asarray(reference, dtype=float)
    if x.shape != y.shape or x.ndim != 2 or x.shape[1] != 3 or len(x) < 3:
        raise ValueError("At least three paired three-dimensional centers are required")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Camera centers must be finite")
    a, b = x - x.mean(axis=0), y - y.mean(axis=0)
    variance = np.sum(a * a) / len(x)
    if variance < 1e-12 or np.linalg.matrix_rank(a) < 2:
        raise ValueError("Camera path must have nonzero translation in at least two directions")
    u, singular, vt = np.linalg.svd(b.T @ a / len(x))
    signs = np.ones(3)
    signs[-1] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ np.diag(signs) @ vt
    scale = float(singular @ signs / variance)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Cannot fit a positive similarity scale")
    translation = y.mean(axis=0) - scale * rotation @ x.mean(axis=0)
    return scale, rotation, translation


def reference_centers(timestamps, ground_truth, max_gap=0.05):
    """Interpolate translation only inside a bounded motion-capture time gap."""
    gt = np.asarray(ground_truth, dtype=float)
    if (gt.ndim != 2 or gt.shape[1] < 4 or len(gt) < 2
            or not np.isfinite(gt[:, :4]).all() or np.any(np.diff(gt[:, 0]) <= 0)):
        raise ValueError("Reference timestamps must be finite and strictly increasing")
    if max_gap <= 0:
        raise ValueError("Maximum interpolation gap must be positive")
    keep, centers = [], []
    for index, stamp in enumerate(timestamps):
        right = int(np.searchsorted(gt[:, 0], stamp))
        if right < len(gt) and abs(gt[right, 0] - stamp) < 1e-9:
            keep.append(index)
            centers.append(gt[right, 1:4])
        elif 0 < right < len(gt) and gt[right, 0] - gt[right-1, 0] <= max_gap:
            left = right - 1
            alpha = (stamp - gt[left, 0]) / (gt[right, 0] - gt[left, 0])
            keep.append(index)
            centers.append((1-alpha)*gt[left, 1:4] + alpha*gt[right, 1:4])
    return keep, np.asarray(centers, dtype=float).reshape(-1, 3)


def evaluate(workspace, ground_truth_path, max_gap=0.05):
    workspace = Path(workspace)
    cloud = json.loads((workspace / "cloud.json").read_text())
    inputs = {row["name"]: row for row in json.loads((workspace / "inputs.json").read_text())}
    cameras = sorted(cloud["cameras"], key=lambda camera: camera["name"])
    stamps = [float(Path(inputs[camera["name"]]["original_name"]).stem) for camera in cameras]
    estimated = np.asarray([camera["center"] for camera in cameras], dtype=float)
    gt = np.loadtxt(ground_truth_path, comments="#", ndmin=2)
    keep, reference = reference_centers(stamps, gt, max_gap)
    estimated = estimated[keep]
    scale, rotation, translation = align_similarity(estimated, reference)
    aligned = scale * estimated @ rotation.T + translation
    errors = np.linalg.norm(aligned - reference, axis=1)
    return {
        "evaluation": "translation absolute trajectory error after one proper Sim(3) fit",
        "reference": "withheld TUM motion-capture translations; not used by reconstruction",
        "scope": "registered cameras with bracketed reference timestamps only; not surface accuracy",
        "input_images": len(inputs), "registered_cameras": len(cameras),
        "associated_cameras": len(keep), "excluded_cameras": len(cameras)-len(keep),
        "maximum_interpolation_gap_seconds": max_gap,
        "scale_metres_per_sfm_unit": scale,
        "rmse_metres": float(np.sqrt(np.mean(errors**2))),
        "median_metres": float(np.median(errors)), "maximum_metres": float(errors.max()),
        "rotation_reference_from_estimate": rotation.tolist(),
        "translation_metres": translation.tolist(),
        "samples": [
            {"image": cameras[index]["name"], "timestamp": stamps[index],
             "reference_metres": ref.tolist(), "aligned_estimate_metres": point.tolist(),
             "translation_error_metres": float(error)}
            for index, ref, point, error in zip(keep, reference, aligned, errors, strict=True)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("ground_truth", type=Path)
    parser.add_argument("--max-gap", type=float, default=0.05)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.workspace, args.ground_truth, args.max_gap)
    value = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(value)
    else:
        print(value, end="")


if __name__ == "__main__":
    main()
