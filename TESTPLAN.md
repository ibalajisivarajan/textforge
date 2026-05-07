# TextForge — Manual Test Plan

Version tested: ___________  
Date: ___________  
Tester: ___________  
Machine: ___________

Mark each case **PASS**, **FAIL**, or **SKIP** (with notes).

---

## TRAY MENU

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| T1 | Launch app for the first time (no token.json) | Tray icon appears. Menu shows "● Not signed in" and "Sign In" option. No "Sign Out" or "Sync Now" visible. | | |
| T2 | Sign in successfully, then open tray menu | Menu shows "● email@gmail.com", "Sign Out" and "Sync Now" visible. "Sign In" gone. | | |
| T3 | Sign out, then open tray menu | Menu reverts to "● Not signed in" and "Sign In". "Sign Out" and "Sync Now" gone. | | |
| T4 | Click "Manage Snippets" | Snippet manager window opens. | | |
| T5 | Click "Pause Expansion" | Menu label changes to "Resume Expansion". Type a known shortcut — it does NOT expand. | | |
| T6 | Click "Resume Expansion" | Menu label changes back to "Pause Expansion". Type the same shortcut — it expands correctly. | | |
| T7 | Click "Sync Now" (while signed in) | Tray notification appears: "Snippets synced successfully." or an error message if offline. | | |
| T8 | Click "Quit" | App exits. No `TextForge` process remains in Task Manager → Details tab. | | |

---

## SIGN IN / AUTH

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| A1 | Click "Sign In" in tray menu | Default browser opens to Google OAuth consent screen. | | |
| A2 | Complete OAuth flow in browser | Browser shows "The authentication flow has completed. You may close this window." Tray notification: "Signed in as email@gmail.com". | | |
| A3 | Quit app and relaunch | App starts signed in — no browser prompt. Tray menu shows email. | | |
| A4 | Sign out, then quit and relaunch | App starts signed out. Tray shows "● Not signed in". | | |

---

## SNIPPET MANAGEMENT UI

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| U1 | Open Manage Snippets | Window opens (600×450). Existing snippets shown in two columns: SHORTCUT / EXPANSION. | | |
| U2 | Add a new snippet (e.g. `bs` → `Balaji Sivarajan`) | Click "+ Add", fill shortcut and expansion, click Save. New row appears in list immediately. | | |
| U3 | Edit an existing snippet | Select row, click "✏ Edit" (or double-click). Change expansion, Save. List row updates immediately. | | |
| U4 | Delete a snippet | Select row, click "🗑 Delete", confirm. Row removed from list immediately. | | |
| U5 | Duplicate shortcut | Try to add a shortcut that already exists. Error message shown: "Shortcut already used. Choose another." Save does not proceed. | | |
| U6 | Empty shortcut field | Leave shortcut blank, click Save. Error shown: "Shortcut is required." Row not added. | | |
| U7 | Empty expansion field | Leave expansion blank, click Save. Error shown: "Expansion is required." Row not added. | | |
| U8 | Search bar — matching query | Type part of a shortcut or expansion. List filters to matching rows in real time. | | |
| U9 | Search bar — no match | Type a string that matches nothing. List shows empty (no rows). | | |
| U10 | Clear search bar | All snippets reappear. | | |
| U11 | Close window via X | Window disappears. App stays running in tray (icon still present). | | |
| U12 | Reopen Manage Snippets after closing | Window reopens with current snippet list. | | |

---

## TEXT EXPANSION

Test in at least: **Notepad**, **Chrome address bar**, **VS Code**.

Setup: add snippet `bs` → `Balaji Sivarajan` before running these tests.

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| E1 | Type `bs` + Space | Expands to `Balaji Sivarajan ` | | |
| E2 | Type `bs` + Period (`.`) | Expands to `Balaji Sivarajan.` | | |
| E3 | Type `bs` + Enter | Expands to `Balaji Sivarajan` then new line | | |
| E4 | Type `bs` + Comma (`,`) | Expands to `Balaji Sivarajan,` | | |
| E5 | Type `bs` + Tab | Expands to `Balaji Sivarajan` then tab | | |
| E6 | Type `BS` (uppercase) + Space | Expands — case-insensitive match | | |
| E7 | Type `Bs` (mixed) + Space | Expands — case-insensitive match | | |
| E8 | Type `bS` (mixed) + Space | Expands — case-insensitive match | | |
| E9 | Type `sb` + Space | Does NOT expand — wrong character order | | |
| E10 | Type `xbs` + Space | Does NOT expand — not at a word boundary | | |
| E11 | Type `bs` with no word-ending character (just stop typing) | Does NOT expand — no trigger fired | | |
| E12 | Expansion in Notepad | Correct expansion text inserted | | |
| E13 | Expansion in Chrome address bar | Correct expansion text inserted | | |
| E14 | Expansion in VS Code | Correct expansion text inserted | | |

---

## SYNC

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| S1 | Add a snippet via UI | Open `%APPDATA%\TextForge\snippets.json` in Notepad — new snippet is present with correct shortcut, expansion, id, and timestamps. | | |
| S2 | Delete a snippet via UI | `snippets.json` no longer contains that snippet's id. | | |
| S3 | Wait up to 5 minutes after adding a snippet (auto-sync) | `snippets.json` "updated_at" timestamp changes. Sync status label in Manage Snippets window updates to "Synced ✓ HH:MM". | | |
| S4 | Click "Sync Now" from tray | Tray notification confirms sync. `snippets.json` "updated_at" updates. | | |
| S5 | Second machine sign-in (cross-device sync) | Sign in with the same Google account on another Windows machine. Open Manage Snippets — all snippets from first machine appear. | | |
| S6 | Offline behaviour | Disconnect network. Add a snippet. Expansion still works locally. Sync shows "Offline" or error notification — app does not crash. | | |

---

## AUTO-START

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| AS1 | Copy `TextForge.exe` to `shell:startup` folder | — | | |
| AS2 | Restart Windows | After login, TextForge icon appears in system tray without manually launching the exe. | | |
| AS3 | Confirm no duplicate instances | Only one TextForge process in Task Manager. Launching the exe a second time shows "already running" dialog and exits. | | |

---

## STABILITY

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| ST1 | Run app for 30 minutes with normal use | No crash, no freeze, tray icon remains responsive. | | |
| ST2 | No memory leak after 30 minutes | Task Manager → Details → `TextForge.exe` runs as a single process. Memory usage should not be continuously growing over the session — a stable or slowly fluctuating value is acceptable. | | |
| ST3 | Add 20+ snippets | All snippets saved and listed correctly. No UI slowdown. | | |
| ST4 | Rapid expansion (type 10 shortcuts quickly) | All expansions fire correctly and in order. No dropped or doubled characters. | | |

---

## HOW TO FILE A BUG

When a test fails, capture:
1. Which test case (e.g. "E10")
2. What you saw vs. what was expected
3. Contents of `%APPDATA%\TextForge\textforge.log`
4. Windows version and TextForge version (shown in tray menu title)
