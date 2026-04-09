@echo off
echo ========================================
echo  Voice to Text - Build Script
echo ========================================
echo.

cd /d "%~dp0"

echo Installing dependencies...
pip install -r requirements.txt
pip install httpx[http2] groq

echo.
echo Building exe...
pyinstaller --onefile --noconsole --name VoiceToText ^
  --icon=icon.ico ^
  --hidden-import=pynput.keyboard._win32 ^
  --hidden-import=pynput.mouse._win32 ^
  --hidden-import=groq ^
  --hidden-import=httpx ^
  --hidden-import=h2 ^
  --hidden-import=hpack ^
  --hidden-import=hyperframe ^
  --hidden-import=silero_vad ^
  --collect-data silero_vad ^
  --collect-data torch ^
  --add-data "icon.png;." ^
  --add-data "icon.ico;." ^
  main.py

echo.
echo ========================================
if exist "dist\VoiceToText.exe" (
    echo  Build SUCCESS!
    echo  Output: dist\VoiceToText.exe
    echo.
    echo  Next: Run install.bat to install
) else (
    echo  Build FAILED. Check errors above.
)
echo ========================================
pause
