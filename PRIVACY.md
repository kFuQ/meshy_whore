# Privacy & Data Handling

Meshy Studio is a desktop application that runs entirely on your machine. It has
no analytics, no telemetry, no accounts, and no backend of its own. See
[SECURITY.md](SECURITY.md) for the security controls behind the points below.

## What data the app handles

| Data | Where it lives | Encrypted at rest |
|------|----------------|-------------------|
| fal.ai API key | App data dir (`settings.enc`) | ✅ AES-256-GCM |
| Job history (params, request IDs, file paths) | App data dir (`history.enc`) | ✅ AES-256-GCM |
| Input images you select | Read from where you chose them; uploaded to fal.ai | n/a |
| Generated 3D models / textures | Your chosen output folder | n/a |

The app **never** transmits your data to anyone except **fal.ai**, and only to
perform the generation you requested.

## Third-party processing (fal.ai)

To generate a model, your **input images are uploaded to fal.ai** and processed
by the Meshy v7 model; results are downloaded back to your machine. That
processing is governed by fal.ai's own terms and privacy policy:

- fal.ai Terms of Service & Privacy Policy: <https://fal.ai/legal/terms-of-service>

Only upload images you have the rights to use.

## GDPR notes

Because Meshy Studio stores everything locally and adds no processing of its
own, you remain in control of your data:

- **Right to access / portability** — your data is plain files in the app data
  directory; history exports to JSON on decrypt. Set `MESHY_MASTER_KEY` to make
  the encrypted store portable.
- **Right to erasure** — use **Settings → Clear history**, delete the output
  folder, and delete the app data directory (which also removes the encrypted
  key). Removing `master.key` renders any remaining ciphertext unrecoverable.
- **Data minimisation** — the app stores only what it needs (a key and job
  metadata) and never records your images in its database.
- **International transfers** — uploading images to fal.ai may transfer data to
  fal.ai's infrastructure; consult their policy for details.

## Data locations

- Linux: `~/.local/share/meshy-studio/`
- macOS: `~/Library/Application Support/MeshyStudio/`
- Windows: `%APPDATA%\MeshyStudio\`
- Outputs: `~/MeshyStudioOutputs/` (configurable in Settings)

## Children's privacy

Meshy Studio is a developer tool and is not directed at children.
