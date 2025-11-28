# AnchorPass (PySide6)

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
  - Manual: "Backup now".
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

## Security / Encryption

All sensitive vault data is encrypted using AES (via the Fernet standard), with keys derived from the master password using PBKDF2 with SHA-256 and a per-vault random salt.

**Important limitations:**

- Like other password managers, AnchorPass cannot protect you if your computer is compromised by malware, keyloggers, or screen capture tools. Use it only on devices you trust.
- If you lose or forget your master password, you will lose access to your vault contents. There is no backdoor or recovery key by design.
- AnchorPass uses modern, well-known cryptographic primitives (AES via Fernet, PBKDF2-HMAC-SHA256 with a per-vault salt, and bcrypt for the master password). Security is an ongoing effort, and feedback or review from the community is welcome.
