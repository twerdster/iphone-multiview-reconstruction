# iPhone multi-view reconstruction: current state

The historical repository contains a README, image and redacted 16-slide presentation. No historical client, server or viewer source has been recovered. A further 2014 report was recovered privately and confirms the same phone-photo → ZIP/HTTP → reconstruction server → PLY/viewer workflow; it is not republished because it contains private database/account material.

## Updated implementation

`updated/` contains a **new 2026 implementation**, not a recovered or repaired student application. A browser uploads/captures JPEG/PNG photographs or accepts an image ZIP. A local, token-protected Flask server runs one isolated CPU reconstruction worker. COLMAP 3.13 estimates cameras and sparse geometry using SIFT, geometric verification, incremental SfM and bundle adjustment. Optional OpenCV 4.12 rectified pairwise SGBM produces a separate partial stereo cloud. A dependency-free WebGL viewer switches between the sparse cloud and final result and exports their PLY files.

The sparse and stereo results are distinct: successful stereo becomes `result.ply`; otherwise the final result is sparse. There is no mesh, recovered metric scale, live tracking or restored native iOS application. Physical iPhone/Safari capture and pinch interaction are not yet validated; the recorded browser checks use desktop Chrome and a phone-sized Chrome viewport.

## Recorded verification

- Real TUM `freiburg1_xyz`: 24 RGB-only inputs, all 24 views registered on Mac and Linux. No supplied depth or poses are reconstruction inputs. Exact run JSON under `updated/validation/mac/` and `linux/` records approximately 4,000 sparse and 45,000–49,000 stereo points.
- Independent post-reconstruction camera evaluation: seven-degree-of-freedom similarity alignment and translation error on the same 24 fitted centers. RMSE 0.010672 m (Mac), 0.010431 m (Linux), reference position span 0.661 m. This is not surface accuracy or independent metric scale recovery.
- Real Avignon facade: 11/11 views registered, 11,307 sparse points, 34,173 partial stereo points. No ground-truth surface/camera reference was provided. Photos are Romuald Perrot's CC BY-NC 3.0 dataset, distinct from MIT new-code licensing.
- The focused test suite currently has 43 cases; a clean Python 3.12 environment is required. The final suite passed on both Mac and Linux. Two actual read-only Claude reviews informed the final prose and lifecycle qualifications. Exact per-platform test logs and integration scope are in `updated/validation/`.
- A native Mac NumPy/Accelerate batched matrix-multiplication crash was reproduced using a saved model and avoided with mathematically equivalent BLAS-free coordinate contractions; see `updated/validation/native-coordinate-fix.json`.
- Actual HTTP/subprocess integration, blank-photo rejection and server SIGTERM/SIGINT worker reaping are recorded under `updated/validation/`. The final repaired browser run registered all 11 Avignon views and verified both cloud selections and a real PLY download; its 31-second recording is linked near the top of the updated guide. Normal shutdown stops its worker; forced process kills/power loss cannot guarantee cleanup.
- The README's top Avignon GIF and additional TUM GIF render saved real geometry, not live capture. Actual browser workflow media is separately labeled.

## Working locations and preservation

Development-specific workspace and dataset paths are recorded in the private task handoff rather than public project documentation. Keep environments, SQLite databases and active runs on native filesystems.

Preserve `assets/project-preview.jpg` and `docs/slides.pdf` byte for byte. The historical root README receives only the top update navigation and a historical-reference qualifier. All new software, media, results and detailed documentation remain under `updated/`. Original authors remain credited; do not attribute the new implementation to them.
