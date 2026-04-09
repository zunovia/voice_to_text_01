@echo off
echo ========================================
echo  Voice to Text - Installer
echo ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\VoiceToText"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SOURCE=%~dp0"

echo Installing to: %INSTALL_DIR%
echo.

:: Create install directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy files
echo Copying files...
copy /Y "%SOURCE%dist\VoiceToText.exe" "%INSTALL_DIR%\" >nul 2>&1
if not exist "%INSTALL_DIR%\VoiceToText.exe" (
    echo ERROR: VoiceToText.exe not found in dist folder.
    echo Please run build.bat first.
    pause
    exit /b 1
)
copy /Y "%SOURCE%icon.ico" "%INSTALL_DIR%\" >nul 2>&1
if not exist "%INSTALL_DIR%\config.json" (
    copy /Y "%SOURCE%config.example.json" "%INSTALL_DIR%\config.json" >nul 2>&1
)

:: Create desktop shortcut
echo Creating desktop shortcut...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set shortcut = WshShell.CreateShortcut^("%DESKTOP%\Voice to Text.lnk"^)
echo shortcut.TargetPath = "%INSTALL_DIR%\VoiceToText.exe"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%"
echo shortcut.IconLocation = "%INSTALL_DIR%\icon.ico"
echo shortcut.Description = "Voice to Text - Speech Input Tool"
echo shortcut.Save
) > "%TEMP%\create_shortcut.vbs"
cscript //nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"

echo.
echo ========================================
echo  Installation Complete!
echo ========================================
echo.
echo  Location: %INSTALL_DIR%
echo  Desktop shortcut: "Voice to Text"
echo.
echo  IMPORTANT: Edit config.json to add your API key:
echo  %INSTALL_DIR%\config.json
echo.
echo  Get free API key at: https://console.groq.com
echo ========================================
pause
