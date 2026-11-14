# Updated media provenance

`avignon-sparse.gif` / `.png` and `reconstruction.gif` / `.png` are reproducible saved-result renderings from `tools/render_preview.py`. Both GIFs are 900×510 pixels, 28 frames at 90 ms each. The orbit changes only the display view; it adds no images, reconstructed points or estimated poses. Points are centered/scaled for display and initially oriented using one estimated camera. They are not recordings of live reconstruction, physical phone capture, a mesh or a fabricated interface.

- **Avignon:** `avignon-sparse.gif` is 1,187,260 bytes and displays 11,307 actual sparse COLMAP points plus three of the 11 input photographs. The source model and exact run counts are recorded in [Avignon validation](../validation/avignon/summary.json). Photographer: **Romuald Perrot**, Avignon Hotel des Monnaies, [pinned source](https://github.com/rperrot/ReconstructionDataSet/tree/4264089c791f7174e7f3657b22b80aac3668924e/AvignonHotelDesMonnaies), **[CC BY-NC 3.0 Unported](https://creativecommons.org/licenses/by-nc/3.0/)**. The preview and exported facade cloud are derivatives; their noncommercial data terms are distinct from the new code's MIT license.
- **TUM:** `reconstruction.gif` is 1,240,623 bytes and displays 45,424 actual filtered stereo points plus three of the 24 input color frames. Source: TUM `rgbd_dataset_freiburg1_xyz`, [TUM RGB-D benchmark](https://cvg.cit.tum.de/data/datasets/rgbd-dataset), **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. Credit Jürgen Sturm, Nikolas Engelhard, Felix Endres, Wolfram Burgard and Daniel Cremers, *A Benchmark for the Evaluation of RGB-D SLAM Systems*, IROS 2012. The output is from estimated cameras and OpenCV stereo, not Kinect depth or supplied poses.

Input photographs are resized/cropped for these previews. Reconstructed geometry is partial and retains the limitations in the [validation guide](../validation/README.md). Both captions include visible source/license credit.

The historical image at `../../assets/project-preview.jpg` is a separate, unchanged recovered figure. `new-badge.svg` is a locally stored navigation badge and conveys no reconstruction metric.

Actual browser workflow recordings/screenshots, when present in this directory, are separate from these saved-result orbit renders; their capture scope and recorded run counts are in [browser validation](../validation/browser.json).

## Recorded browser workflow

`browser-workflow.mp4` is a 31-second recording of the final working desktop Chrome application, sampled at two frames per second and encoded as H.264 at 24 fps (738,991 bytes). It records uploading all 11 original Avignon photographs, CPU reconstruction, switching between sparse SfM and filtered stereo, rotating the view, and downloading an actual sparse PLY. `browser-desktop.png` is a screenshot of that same run. This is a desktop browser recording with software WebGL, not a physical iPhone screen recording. A separate 393-pixel mobile layout check reused the result; camera capture and Safari were not tested. Exact scope and measured output counts are in [`../validation/browser.json`](../validation/browser.json).

Photographs and derived Avignon video/screenshot: Romuald Perrot, [ReconstructionDataSet](https://github.com/rperrot/ReconstructionDataSet), [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/). New application source has its separate code license. Earlier failed browser recordings and raw diagnostic reports remain private; the published video shows the successful repaired run.
