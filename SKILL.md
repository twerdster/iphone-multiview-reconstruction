# Working on this repository

Read `SUMMARY.md`, this file, the root README, then `updated/README.md` and its validation records. Original application source is absent. Do not claim that the historical iPhone app, VisualSFM server or KiwiViewer integration has been rebuilt. All new software, tests, guides, results and media belong under `updated/`.

## Setup and use

Use Python 3.12 and `updated/requirements.txt`. Keep environments, SQLite databases and active run workspaces on a native filesystem. From `updated/`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m multiview.server --work-dir /path/to/runs
python -m multiview /path/to/photos-or.zip /path/to/new-run --threads 4
python -m pytest -q
```

The browser requires the complete printed URL including its token fragment. For a phone on a trusted LAN, add `--host 0.0.0.0` and use the server computer's LAN address. This is an unencrypted local development server, not a hosted multi-user service. Normal Ctrl-C/SIGTERM shutdown terminates its active worker; forced kills do not guarantee cleanup. Check `status.json` and `worker.log` after failures.

Use `tools/download_demo.py /path/to/avignon-images` to obtain only the 11 pinned Avignon photographs, about 152 MiB. The helper verifies byte counts and SHA-256, preserves different existing files, and reports the separate CC BY-NC 3.0 noncommercial data license. Its manifest pins the source commit and attribution. The new code is MIT; recovered materials and third-party data retain their own terms.

## Engine and outputs

The tested chain is CPU COLMAP SIFT → exhaustive matching/verification → incremental mapping/triangulation/bundle adjustment, followed optionally by OpenCV rectified pairwise SGBM. Stereo uses estimated poses, checks the actual rectified projection axis/sign, records skipped candidate reasons, and filters left/right disparity, texture and depth. Large point-coordinate transforms deliberately use BLAS-free `np.einsum(..., optimize=False)` to avoid the recorded Mac NumPy/Accelerate batched-matmul native crash. Preserve that behavior and its large-array regression test. It is not COLMAP PatchMatch or a full multi-view consistency solver.

`result.ply` is the stereo cloud if it exists, otherwise the sparse cloud. Keep `sparse.ply` separate. `cloud.json` and `sparse-cloud.json` are bounded previews with estimated cameras and per-cloud labels/counts. `inputs.json` records original basenames plus input/normalized hashes. Source photographs are not assumed to have known intrinsics or poses.

## Verification and publishing

Use real overlapping photographs for reconstruction evidence. Supplied poses/depth may be used only after reconstruction as clearly labeled evaluation references. The TUM evaluator in `updated/tools/evaluate_tum.py` measures translation after a similarity fit on the same associated centers; it does not validate mesh accuracy, orientation or recovered metric scale.

Run the focused tests and actual CLI/HTTP reconstruction when changing relevant code. A phone-sized browser viewport is not a physical iPhone test. Preserve failure logs; distinguish blank-photo rejection, failed matching/mapping and server/worker failures.

Use `updated/validation/browser.json` for the exact final browser scope, per-cloud counts and recording provenance. Shutdown records distinguish SIGTERM to the server alone from SIGINT to its isolated process group. Keep individual reconstruction runs separate when reporting numerical variation or a later repair.

`tools/render_preview.py` renders a labeled display orbit of saved geometry. Set its cloud, dataset and credit arguments correctly. Preserve media/data attribution and license distinctions. Do not manufacture interfaces or imply the saved orbit is live capture.

Before a commit, review and synchronize SUMMARY.md and SKILL.md, verify the historical PDF/image bytes and original README body, check documentation links/media, and retain the original authors' attribution. No model training is part of this workflow.
