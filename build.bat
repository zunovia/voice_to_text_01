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
REM Delete any stale exe first, so a failed build can't masquerade as success.
if exist "dist\VoiceToText.exe" del /q "dist\VoiceToText.exe"

REM torch/silero-vad removed: VAD is now a pure-numpy RMS gate (recorder.py).
REM --noupx: UPX raises AV false-positive rate and offers no size win here.
REM Use "python -m PyInstaller": the bare "pyinstaller" command is NOT on PATH here.
python -m PyInstaller --onefile --noconsole --noupx --name VoiceToText ^
  --icon=icon.ico ^
  --hidden-import=pynput.keyboard._win32 ^
  --hidden-import=pynput.mouse._win32 ^
  --hidden-import=groq ^
  --hidden-import=httpx ^
  --hidden-import=h2 ^
  --hidden-import=hpack ^
  --hidden-import=hyperframe ^
  --exclude-module=torch ^
  --exclude-module=silero_vad ^
  --exclude-module=transformers ^
  --exclude-module=scipy ^
  --exclude-module=sklearn ^
  --exclude-module=matplotlib ^
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
