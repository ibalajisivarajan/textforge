# Building TextForge.exe

## Automatic Build (GitHub Actions)

Every push to the `main` branch triggers an automatic build.

**What happens:**

1. GitHub spins up a `windows-latest` runner
2. Python 3.11 is installed
3. Dependencies are installed from `requirements.txt`
4. `client_secrets.json` is written from the `CLIENT_SECRETS_JSON` secret
5. `scripts/generate_icon.py` creates `assets/icon.ico`
6. PyInstaller bundles everything into a single `TextForge.exe`
7. The `.exe` is uploaded as a build artifact
8. A GitHub Release is created with the `.exe` attached

**To trigger a new build:** push any commit to `main`.

**To download:** go to [Releases](https://github.com/ibalajisivarajan/textforge/releases/latest) and download `TextForge.exe`.

> **Prerequisite:** The `CLIENT_SECRETS_JSON` GitHub Secret must be set.
> See [docs/02-google-oauth-setup.md](02-google-oauth-setup.md).

## Local Build (Surface Pro)

Use this to build and test on your machine before pushing.

**Prerequisites:**

- Python 3.11+ installed
- `client_secrets.json` in the repo root
- PowerShell

**Steps:**

```powershell
# From repo root
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller

.\scripts\build.ps1
```

The output is at `dist\TextForge.exe`.

## PyInstaller Command (Reference)

```powershell
pyinstaller `
  --onefile `
  --noconsole `
  --icon=assets\icon.ico `
  --name TextForge `
  "--add-data=client_secrets.json;." `
  src\textforge\__main__.py
```

- `--onefile` — single `.exe`, no extracted folder
- `--noconsole` — no terminal window when running
- `--add-data "client_secrets.json;."` — bundles `client_secrets.json` inside the `.exe`
