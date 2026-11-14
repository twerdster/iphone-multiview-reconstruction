"""CPU structure from motion and optional pairwise rectified stereo.

COLMAP estimates poses from image correspondences. Stereo is an additional,
limited OpenCV SGBM stage, not COLMAP PatchMatch or a surface mesher.
"""
from __future__ import annotations

import json
import platform
import time
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pycolmap


def write_json(path, value):
    path = Path(path)
    # Parent lifecycle/status reporting may race a worker's final progress update.
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".status-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        except Exception:
            temporary.unlink()
            raise
    temporary.replace(path)


def write_ply(path, xyz, rgb):
    xyz, rgb = np.asarray(xyz), np.asarray(rgb)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.shape != rgb.shape:
        raise ValueError("PLY requires equal N by 3 position and color arrays")
    if not np.isfinite(xyz).all():
        raise ValueError("Non-finite PLY coordinates")
    with Path(path).open("w") as stream:
        stream.write("ply\nformat ascii 1.0\ncomment New implementation; arbitrary SfM scale\n")
        stream.write(f"element vertex {len(xyz)}\nproperty float x\nproperty float y\nproperty float z\n")
        stream.write("property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        for point, color in zip(xyz, rgb, strict=True):
            stream.write("%.7g %.7g %.7g %d %d %d\n" % (*point, *color))


def camera_cv(camera, scale):
    k = camera.calibration_matrix() * scale
    k[2, 2] = 1.0
    if camera.model.name == "SIMPLE_RADIAL":
        distortion = np.array([camera.params[3], 0., 0., 0., 0.])
    elif camera.model.name in {"PINHOLE", "SIMPLE_PINHOLE"}:
        distortion = np.zeros(5)
    else:
        raise ValueError(f"Unsupported stereo camera model: {camera.model.name}")
    return k, distortion


def transform_rows(points, matrix):
    """Transform 3-vectors without batched BLAS (avoids an Accelerate matmul crash)."""
    return np.einsum("...j,jk->...k", points, matrix, optimize=False)


def rectified_to_world(rectified, rectification_rotation, world_to_camera_rotation, world_to_camera_translation):
    """Undo stereo rectification and the COLMAP world-to-camera pose."""
    in_camera = transform_rows(rectified, rectification_rotation)
    return transform_rows(in_camera - world_to_camera_translation, world_to_camera_rotation)


def horizontal_positive_disparity(projection):
    """SGBM configuration expects horizontal epipolar lines and positive disparity."""
    return abs(float(projection[1, 3])) < 1e-8 and float(projection[0, 3]) < -1e-8


def dense_stereo(model, image_dir, max_size=960, max_pairs=20, progress=None):
    """Fuse independently filtered stereo pairs; no multi-view surface guarantee."""
    images = sorted(model.images.values(), key=lambda im: im.name)
    candidates = []
    for ai, a in enumerate(images):
        ids_a = {p.point3D_id for p in a.points2D if p.has_point3D()}
        center_a = a.projection_center()
        for b in images[ai + 1:]:
            shared = ids_a.intersection(p.point3D_id for p in b.points2D if p.has_point3D())
            if len(shared) < 50:
                continue
            points = np.array([model.points3D[p].xyz for p in shared])
            midpoint = np.median(points, axis=0)
            va, vb = center_a - midpoint, b.projection_center() - midpoint
            angle = np.degrees(np.arccos(np.clip(va @ vb / (np.linalg.norm(va)*np.linalg.norm(vb)), -1, 1)))
            relative_r = b.cam_from_world().rotation.matrix() @ a.cam_from_world().rotation.matrix().T
            relative_t = b.cam_from_world().translation - relative_r @ a.cam_from_world().translation
            # Reject vertical baselines before spending the per-image pairing quota.
            if 2.0 <= angle <= 30.0 and abs(relative_t[0]) >= abs(relative_t[1]):
                candidates.append((len(shared), a, b))
    candidates.sort(key=lambda item: item[0], reverse=True)
    chosen, uses = [], {}
    for overlap, a, b in candidates:
        if uses.get(a.image_id, 0) >= 3 or uses.get(b.image_id, 0) >= 3:
            continue
        chosen.append((a, b))
        uses[a.image_id] = uses.get(a.image_id, 0) + 1
        uses[b.image_id] = uses.get(b.image_id, 0) + 1
        if len(chosen) >= max_pairs:
            break
    output_xyz, output_rgb, records = [], [], []
    for index, (a, b) in enumerate(chosen):
        if progress:
            progress("stereo", f"Rectified stereo pair {index + 1}/{len(chosen)}")
        record = {"left": a.name, "right": b.name, "accepted_points": 0}
        records.append(record)
        ca, cb = model.cameras[a.camera_id], model.cameras[b.camera_id]
        if (ca.width, ca.height) != (cb.width, cb.height):
            record["skipped_reason"] = "different_image_dimensions"
            continue
        ra, ta = a.cam_from_world().rotation.matrix(), a.cam_from_world().translation
        rb, tb = b.cam_from_world().rotation.matrix(), b.cam_from_world().translation
        relative_r, relative_t = rb @ ra.T, tb - rb @ ra.T @ ta
        if abs(relative_t[0]) < abs(relative_t[1]):
            # SGBM follows horizontal epipolar lines, not vertical stereo.
            record["skipped_reason"] = "vertical_baseline"
            continue
        if relative_t[0] > 0:
            a, b, ca, cb, ra, rb, ta, tb = b, a, cb, ca, rb, ra, tb, ta
            relative_r, relative_t = rb @ ra.T, tb - rb @ ra.T @ ta
        record.update(left=a.name, right=b.name)
        scale = min(1., max_size / max(ca.width, ca.height))
        size = (round(ca.width * scale), round(ca.height * scale))
        ka, da = camera_cv(ca, scale)
        kb, db = camera_cv(cb, scale)
        rect_a, rect_b, pa, pb, q, _, _ = cv2.stereoRectify(
            ka, da, kb, db, size, relative_r, relative_t, flags=cv2.CALIB_ZERO_DISPARITY, alpha=0)
        if not horizontal_positive_disparity(pb):
            # stereoRectify chooses its final axis after accounting for relative rotation.
            # Raw translation alone cannot establish the epipolar direction/sign.
            record["skipped_reason"] = "rectified_axis_or_disparity_sign_not_supported"
            continue
        maps_a = cv2.initUndistortRectifyMap(ka, da, rect_a, pa, size, cv2.CV_32FC1)
        maps_b = cv2.initUndistortRectifyMap(kb, db, rect_b, pb, size, cv2.CV_32FC1)
        source_a, source_b = cv2.imread(str(image_dir / a.name)), cv2.imread(str(image_dir / b.name))
        if source_a is None or source_b is None:
            raise ValueError("A registered source image is missing")
        source_a = cv2.resize(source_a, size)
        source_b = cv2.resize(source_b, size)
        left = cv2.remap(source_a, *maps_a, cv2.INTER_LINEAR)
        right = cv2.remap(source_b, *maps_b, cv2.INTER_LINEAR)
        gray_l, gray_r = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY), cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
        disparities = min(160, ((size[0] // 4) // 16) * 16)
        config = dict(numDisparities=disparities, blockSize=5, P1=8*25, P2=32*25,
                      uniquenessRatio=10, speckleWindowSize=80, speckleRange=2,
                      disp12MaxDiff=1, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
        dl = cv2.StereoSGBM_create(minDisparity=0, **config).compute(gray_l, gray_r).astype(np.float32) / 16.
        dr = cv2.StereoSGBM_create(minDisparity=-disparities, **config).compute(gray_r, gray_l).astype(np.float32) / 16.
        yy, xx = np.indices(dl.shape)
        xr = np.rint(xx - dl).astype(int)
        inside = (xr >= 0) & (xr < size[0])
        sampled = dr[yy, np.clip(xr, 0, size[0]-1)]
        valid = (dl > 1) & inside & (np.abs(dl + sampled) <= 1.)
        # Reject rectification padding and locally flat patches.
        valid &= (left.max(axis=2) > 0) & (right[yy, np.clip(xr, 0, size[0]-1)].max(axis=2) > 0)
        fgray = gray_l.astype(np.float32)
        variance = cv2.blur(fgray*fgray, (5, 5)) - cv2.blur(fgray, (5, 5))**2
        valid &= variance > 16
        rectified = cv2.reprojectImageTo3D(dl, q)
        in_a = transform_rows(rectified, rect_a)
        world = rectified_to_world(rectified, rect_a, ra, ta)
        sparse_in_a = transform_rows(np.array([model.points3D[p.point3D_id].xyz for p in a.points2D if p.has_point3D()]), ra.T) + ta
        zlo, zhi = np.percentile(sparse_in_a[:, 2], [2, 98])
        valid &= np.isfinite(world).all(axis=2) & (in_a[:, :, 2] > max(0., zlo*.4)) & (in_a[:, :, 2] < zhi*1.5)
        # Two-pixel sampling bounds output and avoids claiming dense per-pixel coverage.
        valid &= (xx % 2 == 0) & (yy % 2 == 0)
        output_xyz.append(world[valid])
        output_rgb.append(left[valid][:, ::-1])
        record.update(accepted_points=int(valid.sum()), resolution=list(size),
                      left_right_tolerance_pixels=1.0)
    if not output_xyz or sum(len(p) for p in output_xyz) == 0:
        return np.empty((0, 3)), np.empty((0, 3), dtype=np.uint8), records
    xyz, rgb = np.concatenate(output_xyz), np.concatenate(output_rgb)
    extent = np.linalg.norm(np.percentile(xyz, 99, axis=0) - np.percentile(xyz, 1, axis=0))
    voxel = max(extent / 700, 1e-9)
    _, indices = np.unique(np.floor(xyz / voxel).astype(np.int64), axis=0, return_index=True)
    return xyz[indices], rgb[indices], records


def reconstruct(workspace: Path, dense=True, threads=4, max_features=8192):
    started = time.perf_counter()
    cv2.setNumThreads(threads)
    images = workspace / "images"
    inputs = json.loads((workspace / "inputs.json").read_text())
    def progress(stage, message):
        write_json(workspace / "status.json", {"state": "running", "stage": stage,
                   "message": message, "elapsed_seconds": round(time.perf_counter()-started, 2)})
    progress("features", "Extracting CPU SIFT features")
    database = workspace / "database.db"
    options = pycolmap.FeatureExtractionOptions()
    options.max_image_size, options.num_threads = 1600, threads
    options.use_gpu = False
    options.sift.max_num_features = max_features
    dimensions = {(im["width"], im["height"]) for im in inputs}
    mode = pycolmap.CameraMode.SINGLE if len(dimensions) == 1 else pycolmap.CameraMode.AUTO
    pycolmap.extract_features(str(database), str(images), camera_mode=mode,
                             camera_model="SIMPLE_RADIAL", extraction_options=options, device=pycolmap.Device.cpu)
    progress("matching", "Matching image pairs and verifying epipolar geometry")
    match_options = pycolmap.FeatureMatchingOptions()
    match_options.num_threads, match_options.use_gpu = threads, False
    pycolmap.match_exhaustive(str(database), matching_options=match_options, device=pycolmap.Device.cpu)
    progress("mapping", "Estimating camera poses, triangulating and bundle adjusting")
    mapper = pycolmap.IncrementalPipelineOptions()
    mapper.num_threads, mapper.random_seed = threads, 0
    mapper.min_model_size = 3
    mapper.ba_use_gpu = False
    maps = pycolmap.incremental_mapping(str(database), str(images), str(workspace / "sparse"), options=mapper)
    if not maps:
        raise ValueError("No reconstruction: use sharp, textured photographs with overlap and camera translation")
    model = max(maps.values(), key=lambda m: (m.num_reg_images(), m.num_points3D()))
    if model.num_reg_images() < 3 or model.num_points3D() < 30:
        raise ValueError("Insufficient consistent 3D structure; at least three registered views and 30 points are required")
    final = workspace / "model"
    final.mkdir()
    model.write(str(final))
    sparse_xyz = np.array([p.xyz for p in model.points3D.values()])
    sparse_rgb = np.array([p.color for p in model.points3D.values()])
    write_ply(workspace / "sparse.ply", sparse_xyz, sparse_rgb)
    xyz, rgb, pairs = sparse_xyz, sparse_rgb, []
    output_kind = "sparse_sfm"
    if dense:
        stereo_xyz, stereo_rgb, pairs = dense_stereo(model, images, progress=progress)
        if len(stereo_xyz):
            write_ply(workspace / "stereo.ply", stereo_xyz, stereo_rgb)
            xyz, rgb = stereo_xyz, stereo_rgb
            output_kind = "pairwise_stereo"
    write_ply(workspace / "result.ply", xyz, rgb)
    cameras = []
    for image in sorted(model.images.values(), key=lambda im: im.name):
        pose = image.cam_from_world()
        original_name = next(item["original_name"] for item in inputs if item["name"] == image.name)
        cameras.append({"name": image.name, "original_name": original_name, "center": image.projection_center().tolist(),
                        "rotation_world_from_camera": pose.rotation.matrix().T.tolist(),
                        "camera_id": image.camera_id})
    write_json(workspace / "cameras.json", cameras)
    summary = {"implementation": "new implementation, not recovered student source",
               "pycolmap": pycolmap.__version__, "opencv": cv2.__version__,
               "python": platform.python_version(), "system": platform.platform(),
               "input_images": len(inputs), "registered_images": model.num_reg_images(),
               "returned_models": len(maps), "sparse_points": model.num_points3D(),
               "mean_reprojection_error_pixels": float(model.compute_mean_reprojection_error()),
               "mean_track_length_images": float(model.compute_mean_track_length()),
               "output_kind": output_kind, "output_points": len(xyz), "stereo_pairs": pairs,
               "elapsed_seconds": round(time.perf_counter()-started, 3), "scale": "arbitrary; no metric reference supplied",
               "camera_poses": "estimated from images using CPU SIFT, geometric verification, incremental SfM and bundle adjustment",
               "threads": threads, "max_features": max_features}
    write_json(workspace / "summary.json", summary)
    sparse_summary = {**summary, "output_kind": "sparse_sfm", "output_points": len(sparse_xyz)}
    sparse_step = max(1, int(np.ceil(len(sparse_xyz) / 120000)))
    write_json(workspace / "sparse-cloud.json", {"points": np.round(sparse_xyz[::sparse_step], 6).tolist(),
               "colors": sparse_rgb[::sparse_step].tolist(), "cameras": cameras, "summary": sparse_summary})
    # Bounded, dependency-free browser format; PLY retains every point.
    step = max(1, int(np.ceil(len(xyz) / 120000)))
    write_json(workspace / "cloud.json", {"points": np.round(xyz[::step], 6).tolist(),
               "colors": rgb[::step].tolist(), "cameras": cameras, "summary": summary})
    write_json(workspace / "status.json", {"state": "complete", "stage": "complete", "summary": summary})
    return summary
