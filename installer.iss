; installer.iss - Inno Setup script for AnchorPass

; -----------------------
; Preprocessor definitions
; -----------------------

; AppVersion is passed from CI via:
; ISCC.exe /DAppVersion=v1.2.3 installer.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppName "AnchorPass"
#define MyAppExeName "AnchorPass.exe"

; -----------------------
; Setup section
; -----------------------
[Setup]
; IMPORTANT: replace the GUID below with one generated from
; Inno Setup IDE: Tools -> Generate GUID
AppId={{A5EFA4F4-1C0F-4F7A-9A9D-EXAMPLE-GUID}
AppName={#MyAppName}
AppVersion={#AppVersion}

; You can tweak these strings however you like
AppPublisher=genecc04
AppPublisherURL=https://github.com/genecc04/AnchorPass
AppSupportURL=https://github.com/genecc04/AnchorPass/issues
AppUpdatesURL=https://github.com/genecc04/AnchorPass/releases

DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Where to put the generated installer
OutputDir=dist
OutputBaseFilename={#MyAppName}-Setup-{#AppVersion}

Compression=lzma
SolidCompression=yes

; Install to Program Files (64-bit) on 64-bit systems
ArchitecturesInstallIn64BitMode=x64

DisableDirPage=no
DisableProgramGroupPage=yes

; -----------------------
; Language(s)
; -----------------------
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; -----------------------
; Files
; -----------------------
[Files]
; Copy everything from the PyInstaller onedir output into {app}
; Matches your CI: dist\AnchorPass
Source: "dist\AnchorPass\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; -----------------------
; Icons (shortcuts)
; -----------------------
[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Optional: Desktop shortcut
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; -----------------------
; Tasks
; -----------------------
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

; -----------------------
; Run after install
; -----------------------
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
