# Interactive saved-reconstruction viewer

[Open the hosted demonstration](https://twerdster.github.io/iphone-multiview-reconstruction/).

## Local use

From the repository root, use Python 3 and a browser:

```sh
python3 -m http.server --bind 127.0.0.1 --directory updated/demo
```

Open <http://127.0.0.1:8000/>. No dependency installation or build is required.

## Controls

Select Avignon sparse SfM or TUM fr1/xyz pairwise stereo. Drag or use left/right arrows to rotate, scroll or use Zoom, change point size, and pause/resume automatic rotation. Full PLY links lead to the complete saved outputs of the 2026 pipeline.

## Verification and limitations

Canvas rendering of actual saved geometry, not in-browser reconstruction or live capture. Avignon displays all 11,307 saved points; TUM deterministically subsamples the 45,424-point stereo cloud. JSON files record source PLY hashes, full counts and displayed counts. Coordinates have arbitrary SfM scale. Avignon-derived geometry is CC BY-NC 3.0 (noncommercial); TUM-derived data is CC BY 4.0. These rights are separate from the new viewer source license.

Actual Chrome checks on 2026-11-17 exercised the controls and 390-pixel/desktop layouts without JavaScript page errors or horizontal overflow. A narrow viewport is not a physical-device test; Safari/Firefox and physical phone input were not checked. Detailed current checks are in [VALIDATION.json](VALIDATION.json).

New demo source: Aaron Wetzler with agent assistance, 2026, under the scoped [MIT license](LICENSE). Original materials and supplied data retain their separate terms.
