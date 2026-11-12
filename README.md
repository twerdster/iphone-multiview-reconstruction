# Multi-View 3D reconstruction application for iPhone

<p align="center">
  <img src="assets/project-preview.jpg" alt="Two iPod touch screenshots showing a coloured 3D point-cloud reconstruction of a statue of a seated figure on a bench, viewed from two angles" width="460">
</p>

![Platform: iOS + reconstruction server](https://img.shields.io/badge/platform-iOS%20%2B%20reconstruction%20server-lightgrey)
![Documents: 16-slide presentation (redacted)](https://img.shields.io/badge/documents-16--slide%20presentation%20%28redacted%29-informational)
![Source: not recovered](https://img.shields.io/badge/source-not%20recovered-lightgrey)

A documentation record of an iPhone image-capture client and server-side multi-view reconstruction project.

Students: Mohamad Jabareen, Mostafa Agbariah.

Supervision: Aaron Wetzler.

## Available materials

The [16-slide presentation](docs/slides.pdf), *3D Scanning framework for iPhone*, describes a client/server application for reconstructing a 3D model from photographs captured on a phone. The slides describe collecting images into a ZIP file, uploading them over HTTP, running VisualSFM on the server, and returning a PLY result for display through KiwiViewer.

The slides show feature detection and pairwise matching, sparse reconstruction and dense reconstruction as separate stages. The website description names PMVS2; the presentation names VisualSFM. The available materials do not establish the exact final versions or how these components were integrated.

This repository contains the presentation and a historical project image. No capture application, server implementation, viewer project, executable or deployable configuration has been recovered for publication.

## Historical credential exposure

The current public presentation removes one database screenshot from slide 7 to protect login details and personal data; the other slides are unchanged. The first PDF committed on November 12, 2026 included that screenshot. Replacing the current PDF did not remove historical Git copies. The authenticity and continued validity of the displayed application login records have not been established. Owners must change any real or reused credentials. Do not reuse historical accounts or signing/deployment settings if the implementation is later recovered.

## Use and validation

Read the presentation for the historical architecture and examples. There is no software to install or run here. The slides mention Objective-C, XAMPP, VisualSFM and KiwiViewer; they do not supply enough configuration to reproduce a client/server build. No Xcode build, server deployment, reconstruction run, timing benchmark or current dependency compatibility test was performed during recovery.

## Links

- [Project entry on Aaron Wetzler's website](https://twerdster.github.io/#multi-view-3d-reconstruction-application-for-iphone)

## Attribution and reuse

The credits above follow the archived project page. No license for unrecovered source code is implied by this README. Original authors can open an issue to contribute updates or request corrections or removal of their material.

Figure provenance: `assets/project-preview.jpg` is the original student-project figure from the archived project page on Aaron Wetzler's website, copied without modification. It is a historical figure, not a new reconstruction result.
