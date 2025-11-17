# Secure Password Manager (PySide6)

A desktop password manager built with PySide6, SQLite, and modern UX touches:
status badges, multi-select actions, sortable columns, and automatic backups.

## Features

- **Clean UI**
  - Modern table with hover highlight and **sortable headers** (including proper ordering for the **Status** column).
  - **Status badges** (Active, Archived, Expired, Deleted) rendered as pills.
  - Top bar with **Add / Edit**, grouped **Copy Email/Username/Password** buttons (enabled only for a single selection), and **Archive / Expire / Delete** actions.

- **Context Menus**
  - Right-click preserves multi-selection.
  - **Multi-select menu**: Archive Selected, Expire Selected, Delete (to Trash), Restore/Purge when in special folders.
  - Single-item menu includes quick **Copy** actions, **Edit**, lifecycle ops, and TOTP code copy when available.

- **Folders**
  - Normal categories **do not show counts** in the tree.
  - **Special folders** appear at the bottom **with counts**:
    - Archived, Expired, Deleted.
  - Selecting these loads the corresponding status view.

- **Lifecycle**
  - Archive, Expire, Soft Delete (move to Deleted), and **Permanent Delete** inside Deleted.
  - **Automatic expiration checker** runs periodically; when entries expire, the UI (tree + table) refreshes.

- **Backups**
  - Manual: “Backup now”.
  - **Auto-backup on close** (configurable).
  - **Retention**: keep the newest *N* backups (uses `backup_retention`; falls back to `backup_number`).

- **Hotkey copy / actions**
  - Hotkeys can copy fields (site, email, username, password, app password, TOTP, security code) or trigger actions (add, edit, duplicate, archive, expire, delete, lock vault).
  - All shortcuts are configurable or can be left blank in Preferences > Hotkeys.
  - Auto-clears clipboard after a configurable timeout.

- **Tray & startup**
  - Optional **minimize to tray on exit**.
  - Optional **Start with Windows** toggle (uses a Startup-folder shortcut, no services/registry).

## Tech

- **PySide6** for the UI.
- **SQLite** for storage.
- **Cryptography** for encryption.
- **zxcvbn** for strength estimation.
- **EFF Short Wordlist** for passphrase generation.
- **pywin32** for Windows startup integration.

Third-party attributions are in **THIRD_PARTY_NOTICES.md** (MIT for zxcvbn; CC-BY-4.0 for the EFF list).  
Please read those notices for details.

### Cloud Backup (Future Work)

Local backups are performed using a dedicated `BackupMixin` and are designed to be fast and safe on the local filesystem.

If/when a cloud backup feature is added (e.g. uploading backup files to a remote server or cloud storage), **all network uploads MUST be done off the UI thread**. Uploading even a ~50 MB database can take several seconds on typical home upload speeds, and performing that work on the main thread would freeze the application.

Planned approach for cloud backup:

- Continue using `_export_backup_core()` to create a local backup file.
- Perform any cloud uploads in a background worker (`QThread`/async job).
- Only update the UI (status messages, errors) via signals back to the main thread.
