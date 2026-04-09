@echo off
echo.
echo  ========================================
echo   Voice to Text - Uninstaller
echo  ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\VoiceToText"
set "DESKTOP=%USERPROFILE%\Desktop"
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo  Are you sure you want to uninstall Voice to Text?
echo.
set /p CONFIRM=  Type Y to confirm:
if /i not "%CONFIRM%"=="Y" (
    echo  Cancelled.
    pause
    exit /b 0
)

echo.

:: Kill running process
echo  [1/4] Stopping Voice to Text...
taskkill /F /IM VoiceToText.exe >nul 2>&1

:: Remove desktop shortcut
echo  [2/4] Removing desktop shortcut...
del "%DESKTOP%\Voice to Text.lnk" >nul 2>&1

:: Remove Start Menu + Startup entries
echo  [3/4] Removing Start Menu entries...
del "%STARTMENU%\Voice to Text.lnk" >nul 2>&1
del "%STARTUP%\VoiceToText.vbs" >nul 2>&1

:: Remove install directory
echo  [4/4] Removing application files...
rmdir /S /Q "%INSTALL_DIR%" >nul 2>&1

echo.
echo  ========================================
echo   Uninstall Complete!
echo  ========================================
echo.
echo   Voice to Text has been removed.
echo  ========================================
echo.
pause
