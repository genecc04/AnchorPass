# Secure Password Manager (PySide6)

A desktop password manager built with PySide6, SQLite, and modern UX touches:
status badges, multi-select actions, sortable columns, and automatic backups.

## ✨ Features

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

- **Clipboard workflow**
  - Keyboard shortcuts:
    - `Alt+Z` Copy Email
    - `Alt+X` Copy Username
    - `Alt+C` Copy Password
    - `Alt+A` Copy App Password
  - Auto-clears clipboard after a configurable timeout.

## 🧰 Tech

- **PySide6** for the UI.
- **SQLite** for storage.
- **Cryptography** for encryption (via your `cipher` pipeline).
- **zxcvbn** (or `_zxcvbn` port) for strength estimation.
- **EFF Short Wordlist #1** for passphrase generation.

Third-party attributions are in **THIRD_PARTY_NOTICES.md** (MIT for zxcvbn; CC-BY-4.0 for the EFF list).  
Please read those notices for details.