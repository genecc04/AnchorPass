# AnchorPass (PySide6)

AnchorPass is a desktop password manager built with PySide6 and SQLite, featuring a clean, keyboard-friendly UI, built-in password generator, TOTP authenticator, and automatic backups. It uses strong, modern cryptography to protect your vault while giving you practical tools like status-based lifecycle management, folder-like categories, and flexible column and view customization for your entries.

## Features

- **Clean UI**
  - Feature-rich table with **sortable** and **movable headers**, plus a **customizable column layout**.
  - Table rows support **drag & drop** into the category tree for quick re-organization.
  - Category tree uses a familiar **folder-like structure**.
  - **Status badges** (Active, Archived, Expired, Deleted) are rendered as pill-style labels for quick scanning.
  - Compact top bar with:
    - **Add / Duplicate / Edit** entry actions  
    - Grouped **Copy Email / Username / Password** buttons (enabled only when a single row is selected)  
    - **Archive / Expire / Delete** actions  
    - Table **Settings** for view and column customization

- **Folders**
  - Normal categories **do not show counts** in the tree.
  - **Special folders** appear at the bottom **with counts**:
    - Archived, Expired, Deleted.
  - Selecting these loads the corresponding status view.

- **Password Generator**
  - **Built-in password generator** for creating strong, unique passwords.
  - Can generate **random character-based passwords** based on your length and character set preferences.
  - Can generate **random word-based passphrases** with customizable separators for easier-to-memorize passwords.

- **Authenticator**
  - **Built-in authenticator** with TOTP (Time-based One-Time Password) support.
  - Works with TOTP secrets provided manually or extracted from QR codes (where available).

- **Lifecycle**
  - Archive, Expire, Soft Delete (move to Deleted), and **Permanent Delete** inside Deleted.
  - **Automatic expiration checker** runs periodically; when entries expire, the UI (tree + table) refreshes.
  - **Expiry warnings** for entries that are about to expire (highlighted as Expiring with a tooltip showing days remaining).

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
- **cryptography** for encryption.
- **bcrypt** for master password hashing.
- **zxcvbn** for strength estimation.
- **EFF Short Wordlist** for passphrase generation.
- **pywin32** for Windows startup integration.
- **pytz** for timezone handling.

Third-party attributions are in **THIRD_PARTY_NOTICES.md** (MIT for zxcvbn; CC-BY-4.0 for the EFF list).  
Please read those notices for details.

## Security / Encryption

- All sensitive vault data is encrypted using AES (via the Fernet standard). Encryption keys are derived from your master password using PBKDF2 (SHA-256) with a per-vault random salt.
- **Clipboard auto-clear**: copied secrets are automatically cleared from the clipboard after a configurable timeout.
- **Auto-lock on idle**: the vault locks itself after a period of inactivity.
- **Lock on minimize**: optionally lock the vault whenever the window is minimized.
- **Lock on sleep**: automatically lock the vault when the system goes to sleep or is locked.

**Important limitations:**

- Like other password managers, AnchorPass cannot protect you if your computer is compromised by malware, keyloggers, or screen capture tools. Use it only on devices you trust.
- If you lose or forget your master password, you will lose access to your vault contents. There is no backdoor or recovery key by design.
- AnchorPass uses modern, well-known cryptographic primitives (AES via Fernet, PBKDF2-HMAC-SHA256 with a per-vault salt, and bcrypt for the master password). Security is an ongoing effort, and feedback or review from the community is welcome.