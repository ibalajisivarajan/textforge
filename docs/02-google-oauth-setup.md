# Google OAuth Setup

You need to do this once before your first build. Takes about 10 minutes.

## 1. Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top left) → **New Project**
3. Name: `TextForge` → **Create**
4. Make sure the new project is selected in the dropdown

## 2. Enable Google Drive API

1. **APIs & Services** → **Library**
2. Search for **Google Drive API** → click it → **Enable**

## 3. Configure OAuth Consent Screen

1. **APIs & Services** → **OAuth consent screen**
2. User Type: **External** → **Create**
3. Fill in:
   - App name: `TextForge`
   - User support email: your Gmail
   - Developer contact email: your Gmail
4. **Save and Continue**

## 4. Add Scopes

1. Click **Add or Remove Scopes**
2. Add these two scopes:
   - `https://www.googleapis.com/auth/drive.appdata`
   - `https://www.googleapis.com/auth/userinfo.email`
3. **Update** → **Save and Continue**

## 5. Add Test User

1. **Test users** → **Add Users**
2. Enter your Gmail address
3. **Save and Continue** → **Back to Dashboard**

## 6. Create OAuth Client ID

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `TextForge Desktop`
5. **Create**

## 7. Download client_secrets.json

1. Click the download button (↓) next to the new credential
2. Rename the downloaded file to `client_secrets.json`
3. Place it in the **repo root** (same folder as `requirements.txt`)

> `client_secrets.json` is in `.gitignore` and will never be committed.

## 8. Add GitHub Secret

So GitHub Actions can build the `.exe` with your credentials:

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. Name: `CLIENT_SECRETS_JSON`
4. Value: paste the **entire contents** of `client_secrets.json`
5. **Add secret**

That's it. Every push to `main` will now build `TextForge.exe` automatically.
