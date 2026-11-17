# Multi-view reconstruction: current maintenance context

Read this file, then SKILL.md, README.md and linked implementation/validation guides.

## Original project and preservation

Historical phone-to-server reconstruction by Mohamad Jabareen and Mostafa Agbariah, supervised by Aaron Wetzler. Preserve the historical image and redacted presentation. Original software is missing. A private recovered report contains account/database material and must not be published.

## Current work — 2026-11-17

The existing separate Python 3.12/pycolmap/OpenCV pipeline estimates cameras and sparse geometry and optionally produces pairwise stereo, with a token-protected local server and WebGL client. The new hosted Canvas viewer rotates saved actual Avignon sparse and TUM stereo geometry; it does not run reconstruction. JSON previews record PLY source hashes/full/display counts.

Aaron requested concise natural README prose and a runnable demo in each Updated section. A real tools-disabled Claude review and follow-up inform the wording; factual suggestions are checked against source and records. The previous full README is preserved as PROJECT_RECORD.md. Existing updated-guide anchors remain available; lengthy implementation/recovery records are linked rather than repeated in the main README.

## Checks and maintenance

Preserve image and presentation bytes. New code is MIT; Avignon geometry/photo terms are noncommercial CC BY-NC 3.0, TUM terms separate CC BY 4.0. Keep sparse/stereo outputs separate; result.ply selects stereo when present, otherwise sparse. Preserve BLAS-free coordinate contractions and related regression. Normal server shutdown reaps its worker; forced kills do not guarantee cleanup. Do not claim metric scale, mesh or surface accuracy from aligned camera errors. Use updated/DETAILS.md and validation records for exact pipeline/evaluation scope.

New static demonstration checks are in updated/demo/VALIDATION.json when present. Actual Chrome desktop/390-pixel interactions were checked; a narrow viewport is not a physical device. No hardware, live microphone/camera recognition or cross-browser coverage is added. Review and synchronize SUMMARY.md and SKILL.md before every commit. Keep private evidence, account details and machine paths outside the repository.
