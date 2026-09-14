# TODO / Roadmap

See [README.md](README.md) for an overview and [CHANGELOG.md](CHANGELOG.md) for
shipped work.

## Known limitations

- **No in-app 3D viewer.** Tkinter can't render GLB. The app shows the returned
  PNG thumbnail and opens output files with your OS's default handler. A future
  version could embed a viewer (e.g. via an OpenGL widget or a bundled
  `<model-viewer>` in a webview).
- **Polling, not webhooks.** The desktop app polls fal.ai for status. Webhooks
  aren't applicable to a local GUI without a public endpoint.

## Planned

- [ ] Optional embedded 3D preview for GLB output.
- [ ] Batch mode: queue multiple image sets.
- [ ] Re-run a past job from the History tab (reuse its parameters).
- [ ] Per-job output subfolders named by request ID.
- [ ] Drag-and-drop image adding (needs `tkinterdnd2`, kept optional).
- [ ] Cost estimate preview based on selected options (texture/PBR/rigging).
- [ ] Localisation of UI strings.
- [ ] Packaged binaries (PyInstaller) for macOS / Windows / Linux.

## Testing

- [x] Unit tests for crypto, schema, and encrypted store.
- [x] Headless GUI construction + theme-switch smoke test.
- [ ] Mocked end-to-end worker test (fake fal client).
