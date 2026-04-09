@echo off
echo.
echo  ========================================
echo   Voice to Text - Installer
echo  ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\VoiceToText"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SOURCE=%~dp0"

:: Check if exe exists
if not exist "%SOURCE%dist\VoiceToText.exe" (
    echo  ERROR: VoiceToText.exe not found.
    echo  Please run build.bat first.
    echo.
    pause
    exit /b 1
)

echo  Installing to: %INSTALL_DIR%
echo.

:: Create install directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy files
echo  [1/3] Copying files...
copy /Y "%SOURCE%dist\VoiceToText.exe" "%INSTALL_DIR%\" >nul
copy /Y "%SOURCE%icon.ico" "%INSTALL_DIR%\" >nul
copy /Y "%SOURCE%icon.png" "%INSTALL_DIR%\" >nul
if not exist "%INSTALL_DIR%\config.json" (
    copy /Y "%SOURCE%config.example.json" "%INSTALL_DIR%\config.json" >nul
)

:: Create desktop shortcut with icon
echo  [2/3] Creating desktop shortcut...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set shortcut = WshShell.CreateShortcut^("%DESKTOP%\Voice to Text.lnk"^)
echo shortcut.TargetPath = "%INSTALL_DIR%\VoiceToText.exe"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%"
echo shortcut.IconLocation = "%INSTALL_DIR%\icon.ico, 0"
echo shortcut.Description = "Voice to Text - Press F2 to speak"
echo shortcut.Save
) > "%TEMP%\vtt_shortcut.vbs"
cscript //nologo "%TEMP%\vtt_shortcut.vbs"
del "%TEMP%\vtt_shortcut.vbs"

:: Create Start Menu shortcut
echo  [3/3] Creating Start Menu entry...
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set shortcut = WshShell.CreateShortcut^("%STARTMENU%\Voice to Text.lnk"^)
echo shortcut.TargetPath = "%INSTALL_DIR%\VoiceToText.exe"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%"
echo shortcut.IconLocation = "%INSTALL_DIR%\icon.ico, 0"
echo shortcut.Description = "Voice to Text - Press F2 to speak"
echo shortcut.Save
) > "%TEMP%\vtt_startmenu.vbs"
cscript //nologo "%TEMP%\vtt_startmenu.vbs"
del "%TEMP%\vtt_startmenu.vbs"

echo.
echo  ========================================
echo   Installation Complete!
echo  ========================================
echo.
echo   Desktop:    "Voice to Text" icon created
echo   Start Menu: "Voice to Text" added
echo   Location:   %INSTALL_DIR%
echo.
echo   Double-click the desktop icon to start!
echo   First launch will ask for your API key.
echo.
echo   Get free API key: https://console.groq.com
echo  ========================================
echo.
pause
