#define MyAppName "RhythmAlign"
#define MyAppVersion "1.1.1"
#define MyAppPublisher "Limitime"
#define MyAppURL "https://github.com/Daozhu1007/RhythmAlign"
#define MyAppExeName "RhythmAlign.exe"

[Setup]
AppId={{B8F4A3D2-9C1E-4E7F-AE5B-6D2F8C9A1E3B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=RhythmAlign_v1.1.1_Setup
SetupIconFile=assets\logo.ico
Compression=lzma2
SolidCompression=yes
LicenseFile=LICENSE
WizardStyle=modern
PrivilegesRequiredOverridesAllowed= dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\RhythmAlign\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RhythmAlign\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
