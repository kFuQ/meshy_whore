# Security

Meshy Studio is a **local, single-user desktop application**. It has no server,
no listening ports, and no multi-user surface. This document describes its
threat model and the controls in place. See [PRIVACY.md](PRIVACY.md) for data
handling and [README.md](README.md) for an overview.

## Assets

1. **fal.ai API key** — grants billable access to your fal.ai account.
2. **Job history** — records of past generations (parameters, request IDs,
   local file paths). Never contains the API key.
3. **Your input images** and generated outputs on local disk.

## Trust boundaries

- **Local disk** — the only place the app persists data. Secrets are encrypted.
- **fal.ai API (network)** — the app uploads images and downloads results over
  HTTPS with default certificate verification.

## Controls

### Encryption at rest (AES-256-GCM)
- The API key and history are sealed with **AES-256-GCM** before being written
  (`meshy_studio/crypto.py`). Ciphertexts are authenticated — tampering is
  detected on decrypt — and bound to their purpose via associated data so a
  settings blob can't be swapped for a history blob.
- The 256-bit master key is either derived from a passphrase
  (`MESHY_MASTER_KEY`) via **scrypt**, or randomly generated once and stored in
  `master.key` with `0600` permissions. The data directory is `0700`.
- Writes are atomic (`tempfile` + `os.replace`) with `0600` on the temp file.
- **Verified by test:** `tests/test_core.py::TestStore::test_api_key_encrypted_on_disk`
  asserts the plaintext key is not present in the on-disk settings file.

### Secrets hygiene
- The API key is **never logged** and **never written to history**.
- In the UI it is masked (`•`) with an explicit "Show" toggle.
- An env-provided `FAL_KEY` is used for the session and takes precedence.

### File handling
- **Uploads:** input images are validated against an extension allowlist
  (`.jpg/.jpeg/.png/.avif/.heic/.heif`) and a 25 MB size cap before upload.
- **Downloads:** restricted to `http(s)` URLs; the destination filename is
  reduced to its basename and stripped of special characters to prevent path
  traversal; a 1 GiB per-file cap prevents a runaway write from filling the
  disk; partial files are removed on failure.

### Process & network
- OS "open file/folder" actions use `subprocess.run([...])` / `os.startfile`
  with **argument lists — never a shell string** — so filenames can't inject
  commands.
- System theme detection uses list-form subprocess calls with a timeout.
- HTTPS uses Python's default TLS context (**certificate verification on**).

### Dependencies
- Minimum versions are pinned past known CVEs: `cryptography>=42.0.4`,
  `Pillow>=10.3.0`. Run `pip-audit` / `pip install -U -r requirements.txt`
  periodically.

## Residual risks

- Anyone with **read access to your OS user account** can run the app, which can
  decrypt using the local `master.key`. Encryption at rest protects the data if
  the files are copied elsewhere (e.g. a stolen backup) without the key. For
  stronger separation, set `MESHY_MASTER_KEY` to a passphrase you type and do
  not store the key file alongside the data.
- The app trusts fal.ai's API responses (URLs, filenames). These are sanitised
  before use but are otherwise treated as functional data.

## Reporting a vulnerability

Please open a private report / security advisory on the repository, or contact
the maintainer directly. Do not file public issues for undisclosed
vulnerabilities.
