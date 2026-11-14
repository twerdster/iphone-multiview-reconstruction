# Downloadable reconstructed geometry

These are actual saved output files, not supplied ground truth or display meshes:

- [Avignon sparse PLY](avignon-sparse.ply): 11,307 COLMAP sparse SfM points from 11 real photographs; arbitrary scale. Source photographs by Romuald Perrot, [pinned source](https://github.com/rperrot/ReconstructionDataSet/tree/4264089c791f7174e7f3657b22b80aac3668924e/AvignonHotelDesMonnaies), [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/). Derivative result/data terms are separate from the MIT code license.
- [TUM stereo PLY](tum-stereo.ply): 45,424 filtered pairwise stereo points from 24 RGB images, with estimated cameras and no depth/poses supplied to reconstruction; arbitrary scale. Source: TUM RGB-D benchmark, `freiburg1_xyz`, Jürgen Sturm, Nikolas Engelhard, Felix Endres, Wolfram Burgard and Daniel Cremers, IROS 2012, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Both clouds are incomplete and can contain noise. Neither is a watertight mesh or a metric surface accuracy result. Exact summaries, hashes and reconstruction scope are in [validation](../validation/README.md).
