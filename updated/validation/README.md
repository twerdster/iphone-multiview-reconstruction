# Validation record

Validation checks the **new implementation**, not the unrecovered historical iPhone application. Runs used CPU computation; no model training or GPU reconstruction was performed.

## Real photographs

Input: 24 evenly selected 640×480 color frames spanning approximately 26.57 seconds of TUM `freiburg1_xyz`. No depth, camera poses, feature tracks or prebuilt model were given to reconstruction. Input timestamps and SHA-256 hashes are recorded with each run. JPEG normalization changes pixels slightly; normalized hashes identify the actual engine input.

Operator chain: Pillow orientation/resize/JPEG → pycolmap 3.13.0 CPU SIFT → exhaustive pair matching and two-view verification → incremental mapping, triangulation and bundle adjustment → OpenCV 4.12.0 horizontal rectification/StereoSGBM → one-pixel left/right, texture and depth checks → voxel deduplication → PLY.

Recorded Mac run on November 14, 2026: Python 3.12.11, macOS 15.1.1 arm64, four configured CPU threads; **24/24 registered views**, **4,053 sparse points**, **0.779905 pixels mean sparse reprojection error**, **45,424 output stereo points**, **8.644 seconds** from feature extraction through PLY/camera export. This excludes upload, image normalization and final JSON-preview serialization. Two candidate COLMAP models were returned; the largest 24-view model was selected. CPU numerical variation can change matches, candidate models and stereo counts between runs. Timing is one recorded run, not a benchmark or an expected phone processing time.

Linux (Ubuntu 22.04 x86_64, Python 3.12.12, CPU4) registered **24/24 views**, with **4,057 sparse points**, **0.785800 pixels mean sparse reprojection error**, **48,991 stereo points**, and **8.505 seconds** for its recorded run. Exact summaries and input hashes: [Mac](mac/summary.json), [Linux](linux/summary.json). The run-summary JSON files, rather than rounded README counts, are the authoritative per-run counts.

A second real scene, Avignon Hotel des Monnaies, registered **11/11 photographs**, with **11,307 sparse points**, **34,173 stereo points**, **1.008280 pixels mean sparse reprojection error** and **19.153 seconds** in one Mac CPU4 run. Its sparse facade is the top README visual; stereo remains partial, with most attempted pairs empty. See [Avignon summary](avignon/summary.json) and [pinned data manifest](../tools/demo_manifest.json).

Camera translation is evaluated **after** reconstruction against withheld TUM motion-capture positions, with timestamp interpolation and a fitted similarity transform (rotation, translation and scale). All **24 camera centers** were both fitted and evaluated using a seven-degree-of-freedom Sim(3) alignment. Translation RMSE was **0.010672 m (Mac)** and **0.010431 m (Linux)** over a reference position span of approximately **0.66 m**. See the [Mac](mac/trajectory-evaluation.json) and [Linux](linux/trajectory-evaluation.json) samples and fit. This evaluates translation on the same aligned camera centers used for fitting, not orientation, held-out generalization, independently recovered metric scale or 3D surface accuracy. The evaluator rejects degenerate/insufficient associations and includes a labeled synthetic alignment control. Do not interpret fitted-scale centimeter camera error as centimeter mesh accuracy.

## Tests and failure controls

Run `python -m pytest -q` from `updated/`. The current suite has 43 cases, including six evaluator cases; this count describes focused import/API/coordinate/evaluation checks, not 43 scenes or platform executions. Cases cover duplicate rejection, unsafe ZIP paths, invalid image content, metadata handling, token/origin checks, malformed multipart lock recovery, absolute worker paths, native-worker failure/timeout reporting, shutdown cleanup, pinned-demo hash verification, COLMAP/OpenCV radial projection equivalence, large strided-array coordinate transforms, rectification-axis checking and Q-to-world reprojection with rotated cameras.

A real native-engine **negative control** supplied three different uniform-color PNG images. The CLI returned a nonzero exit and wrote:

```
No reconstruction: use sharp, textured photographs with overlap and camera translation
```

It did not export a fabricated cloud. This control checks one failure mode; it does not enumerate every degeneracy.

The initial existing miniconda Python 3.12.7 interpreter crashed while pytest imported its readline extension, before collecting tests. A clean uv-managed Python 3.12.11 environment was installed outside the repository and the tests passed there. A source API mismatch (`Camera.model_name` versus `Camera.model.name`) and AppleDouble sidecar import error were reproduced, fixed, and followed by fresh successful real-image runs. These are implementation corrections, not repairs to student source.

A final real Avignon browser check exposed a native NumPy/Accelerate matrix-multiplication crash after successful SfM. Re-running **only stereo on the same saved model** reproduced the crash. Large coordinate-array transforms now use equivalent `np.einsum` contractions with `optimize=False`, avoiding the implicated batched BLAS path. The same model then completed all 15 candidate pairs and produced 34,154 stereo points. This is a coordinate-transform implementation change; COLMAP and OpenCV remain the numerical engines. See [failure and regression evidence](native-coordinate-fix.json).

## HTTP and browser integration

[Integration evidence](integration.json) records an actual multipart photo upload and worker subprocess using a relative workspace, followed by successful reconstruction and PLY/JSON exports. [Shutdown evidence](shutdown.json) records SIGTERM sent to the server process only: its real native worker was reaped and the unfinished job marked failed. [Browser evidence](browser.json) identifies desktop Chrome, phone-sized viewport, software WebGL, workflow media and layout/error checks. A physical iPhone/Safari capture session has not been recorded.

A separate [SIGINT process-group check](shutdown-sigint.json) exercised terminal Ctrl-C signal semantics and also reaped the worker. The final repaired browser flow registered all 11 Avignon views, switched between 11,305 sparse points and 34,262 stereo points, and downloaded a valid sparse PLY. The 19.892-second reconstruction timing excludes upload and input normalization. A fresh Linux run after the coordinate repair is retained separately in [its summary](linux-coordinate-fix/summary.json) and [trajectory evaluation](linux-coordinate-fix/trajectory-evaluation.json); the earlier quantitative records remain identified by their individual runs.

## Review

Two actual read-only Claude reviews examined the documentation and relevant code/project facts. Feedback improved source attribution, sparse/stereo output descriptions, physical-device scope, timing/evaluation qualifications and shutdown behavior. Suggestions were checked against the code and focused/runtime tests; the reviews are not independent reconstruction executions. See [review scope](review.json).

## Practical limits

- The result is a partially reconstructed point cloud. Black, reflective, textureless, occluded or motion-blurred regions can be missing or noisy. No ground-truth surface evaluation was performed.
- Pairwise stereo is not a full multi-view consistency solver. Empty stereo pairs are recorded; absence of usable stereo retains the sparse result.
- A browser at a phone-sized viewport is a layout/input test, not proof of physical iPhone camera capture. Physical device runs must be identified separately when recorded.
- Dependencies were installed from pinned wheels. No original Xcode project, VisualSFM server, KiwiViewer integration or Windows deployment was built.

Avignon photographs and facade derivatives: Romuald Perrot, [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/); see the pinned source/data manifest.

TUM data and derivative image attribution: Jürgen Sturm, Nikolas Engelhard, Felix Endres, Wolfram Burgard and Daniel Cremers, TUM RGB-D benchmark, IROS 2012, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [references](../REFERENCES.md).
