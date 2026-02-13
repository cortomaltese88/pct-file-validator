#define MyAppName "GD LEX - PCT Validator"
#ifndef MyAppVersion
#define MyAppVersion "1.1.7"
#endif
#define MyAppPublisher "Studio GD LEX"
#define MyAppExeName "GDLEX-PCT-Validator.exe"
#ifndef MyAppIcon
#define MyAppIcon "{#SourcePath}\..\..\dist-installer\assets\windows\app.ico"
#endif

[Setup]
AppId={{B4EAF5A4-7B4F-4A6C-8D11-5F07F7D34986}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\GDLEX-PCT-Validator
DefaultGroupName=GD LEX - PCT Validator
DisableProgramGroupPage=yes
OutputDir={#SourcePath}\..\..\dist-installer
OutputBaseFilename=GDLEX-PCT-Validator-Setup
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
Source: "{#SourcePath}\..\..\dist\GDLEX-PCT-Validator\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\GD LEX - PCT Validator"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\GD LEX - PCT Validator"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
