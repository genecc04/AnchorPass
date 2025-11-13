; ============================
; SecurePasswordManager.iss
; ============================

; ---- Edit these if you change name/version/icon later
#define MyAppName        "Secure Password Manager"
#define MyAppVersion     "Alpha 1.0"
#define MyAppPublisher   "devShawrk"
#define MyAppExeName     "SecurePasswordManager.exe"

; ---- Where your PyInstaller exe currently lives (ABSOLUTE PATH)
#define MyBuiltExe       "C:\Users\genes\Documents\password manager vA.1\dist\SecurePasswordManager.exe"

[Setup]
; Generate a GUID once in Inno IDE: Tools -> Generate GUID
AppId={{8F7E5F2A-7E6A-4F3F-AE37-5B1B2C7F2E55}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; ---- Per-user install (no admin). Installs to:
; C:\Users\<user>\AppData\Local\Programs\SecurePasswordManager
DefaultDirName={localappdata}\Programs\SecurePasswordManager
DefaultGroupName={#MyAppName}

; Optional: show your app icon in Add/Remove Programs if your exe has one:
UninstallDisplayIcon={app}\{#MyAppExeName}

; ---- Where to drop the built installer (.exe)
OutputDir=installer\output
OutputBaseFilename=SecurePasswordManager-Setup

; ---- Compression & format
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; Unicode is default in modern Inno

; Optional: use your app/icon for the installer UI (if you have it)
; SetupIconFile=assets\app.ico

; If you want no admin *and* no elevation prompts at all:
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; ---- Onefile PyInstaller build: copy the single exe to the app directory
Source: "{#MyBuiltExe}"; DestDir: "{app}"; Flags: ignoreversion

; If you ever switch to ONEDIR build, comment the above line and use:
; Source: "C:\Users\genes\Documents\password manager vA.1\dist\SecurePasswordManager\*"; \
;   DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Optional Desktop shortcut (toggled by Tasks)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Optionally launch app right after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
