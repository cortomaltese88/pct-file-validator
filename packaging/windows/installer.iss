#define MyAppName "GD LEX - PCT Validator"
#ifndef MyAppVersion
  #error MyAppVersion must be defined from git tag
#endif
#ifndef MyAppIcon
  #error MyAppIcon must be defined (generated in CI)
#endif
#define MyAppPublisher "Studio GD LEX"
#define MyAppExeName "pct-file-validator.exe"

[Setup]
AppId={{B4EAF5A4-7B4F-4A6C-8D11-5F07F7D34986}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\GDLEX-PCT-Validator
DefaultGroupName=GD LEX - PCT Validator
DisableProgramGroupPage=yes
OutputDir={#SourcePath}\..\..\dist-installer
OutputBaseFilename=pct-file-validator-{#MyAppVersion}-windows
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourcePath}\..\..\dist\pct-file-validator\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\GD LEX - PCT Validator"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\GD LEX - PCT Validator"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
