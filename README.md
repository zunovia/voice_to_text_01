# Voice to Text

AQUA Voice inspired voice-to-text desktop application. Press a hotkey, speak, and your words are transcribed and inserted at the cursor position in any application.

## Features

- **System-wide voice input** - Works in any app (Chrome, Word, VS Code, Slack, etc.)
- **Fast transcription** - Groq Whisper API (~0.3s latency)
- **Japanese optimized** - Excellent Japanese recognition with punctuation
- **Voice commands** - Say "enter" for newline, "period" for punctuation
- **Toggle mode** - Press F2 to start recording, press again to stop
- **System tray** - Runs quietly in the background
- **Recording overlay** - Waveform visualization while recording
- **Cross-platform** - Windows and macOS

## Quick Start

### 1. Install Python 3.10+

### 2. Install dependencies
```bash
pip install -r requirements.txt
pip install httpx[http2] groq
```

### 3. Get a Groq API Key (Free)

1. Go to https://console.groq.com
2. Sign up with Google account
3. Click **API Keys** in the left menu
4. Click **Create API Key**
5. Copy the key (starts with `gsk_...`)

Groq free tier: **14,400 requests/day** (practically unlimited for personal use).

### 4. Run
```bash
python main.py
```

On first launch, enter your Groq API Key in the setup dialog.

**Windows:** Double-click `VoiceToText.vbs` to run without console window.

### 5. Use

- **F2** (or Fn+F2) - Toggle recording on/off
- Speak naturally
- Text is inserted at cursor position

## Voice Commands

| Say | Output |
|-----|--------|
| エンター / 改行 | Enter (newline) |
| まる / ピリオド | 。 |
| てん / カンマ | 、 |
| かっこ | （ |
| かっことじ | ） |
| かぎかっこ | 「 |
| かぎかっことじ | 」 |

## Configuration

Edit `config.json` (created on first run):

```json
{
  "api_key": "gsk_...",           // Groq API key
  "hotkey": "f2",                  // Hotkey to toggle recording
  "mode": "toggle",               // "toggle" or "push_to_talk"
  "language": "ja",                // Language code
  "use_gemini_cleanup": false,     // Enable Gemini post-processing for better punctuation
  "gemini_api_key": ""             // Gemini API key (optional, for cleanup)
}
```

## Alternative STT Providers

| Provider | Speed | Cost | Setup |
|----------|-------|------|-------|
| **Groq Whisper** (default) | ~0.3s | Free (14,400 req/day) | https://console.groq.com |
| Gemini 2.5 Flash | ~2.5s | ~$0.0015/min | https://aistudio.google.com/apikey |
| OpenAI Whisper | ~1-2s | $0.006/min | https://platform.openai.com |

To switch providers, change `api_key` in `config.json`.

## Build Executable (Windows)

```bash
build.bat
```

Output: `dist/VoiceToText.exe`

To distribute:
1. Copy `dist/VoiceToText.exe`
2. Copy `config.example.json` as `config.json` (edit API key)
3. Double-click `VoiceToText.exe`

## System Tray Menu

Right-click the tray icon for:
- Mode toggle (Push-to-Talk / Toggle)
- Settings
- Auto-start on Windows login (ON/OFF)
- Quit

## Tech Stack

- **STT**: Groq Whisper Large V3 Turbo (+ optional Gemini cleanup)
- **Audio**: sounddevice (16kHz mono)
- **VAD**: Silero VAD (silence removal)
- **Hotkey**: pynput (global hotkey)
- **Text Insert**: pyperclip + pyautogui (clipboard paste)
- **UI**: pystray (system tray) + tkinter (overlay/settings)

## License

MIT
