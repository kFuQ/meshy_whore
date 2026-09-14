# Changelog

All notable changes to Meshy Studio are documented here. This project adheres
to [Semantic Versioning](https://semver.org/) and the
[Keep a Changelog](https://keepachangelog.com/) format.

## [1.0.0] — 2026-09-14

### Added
- Initial release: desktop client for the fal.ai **Meshy v7
  multi-image-to-3D** model.
- Multi-image input (1–4 images) with type + size validation and thumbnails.
- Full v7 parameter surface: topology, target polycount, symmetry mode,
  remesh, textures, PBR maps, pose mode, texture prompt / image URL,
  auto-rigging, rig height, animation preset + action ID, safety checker.
  Dependent options auto-enable/disable per the API's rules.
- Native menu bar: **File** (Set API Key…, Set Output Directory…, Open Output
  Folder, Exit), **View** (theme), and **Help** (Getting Started, Parameter
  Guide, How to Get an API Key, About) with themed in-app help windows.
- Background generation worker (upload → submit → poll → download) that keeps
  the UI responsive, with live status log and cancellation.
- Result panel with preview thumbnail, per-file outputs, and auto-download of
  GLB / FBX / OBJ / USDZ / textures / animations.
- History tab (encrypted) and Settings tab.
- Global theming: light / dark / high-contrast + system auto-detect, driven by
  a single colour-token set (no hard-coded colours). ARIA-equivalent tooltips
  on every parameter.
- All timestamps displayed in the user's local time zone.

### Security
- API key and job history **encrypted at rest with AES-256-GCM**; master key
  file stored `0600`, data directory `0700`, atomic `0600` writes.
- Downloads restricted to `http(s)`, filenames sanitised against path
  traversal, and a 1 GiB per-file download cap.
- API key is never logged and never written to history.
- Dependency floors set past known CVEs (`cryptography>=42.0.4`,
  `Pillow>=10.3.0`).

[1.0.0]: #
