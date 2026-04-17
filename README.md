# Voice to Text

[English](#english) | [日本語](#日本語)

---

## 日本語

AQUA Voice にインスパイアされた音声入力デスクトップアプリです。ホットキーを押して話すだけで、文字起こしされたテキストがカーソル位置に挿入されます。

### 特徴

- **どのアプリでも使える** - Chrome、Word、VS Code、Slack など全てのアプリで動作
- **高速変換** - Groq Whisper API で約0.3秒のレイテンシー
- **日本語最適化** - 高精度な日本語認識と句読点
- **音声コマンド** - 「エンター」で改行、「まる」で句点など
- **トグル方式** - F2で録音開始、もう一度押して停止
- **フローティングボタン** - 画面右下に常時表示。マイク(録音ON/OFF) + Enterボタン付き。ドラッグで移動可能
- **システムトレイ常駐** - バックグラウンドで静かに動作
- **波形オーバーレイ** - 録音中にリアルタイム波形表示
- **クロスプラットフォーム** - Windows / macOS 対応

### クイックスタート

#### 1. Python 3.10+ をインストール

#### 2. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

#### 3. Groq API Key を取得（無料）

1. https://console.groq.com にアクセス
2. Googleアカウントでサインアップ
3. 左メニューの **API Keys** をクリック
4. **Create API Key** をクリック
5. キーをコピー（`gsk_...` で始まる）

Groq 無料枠: **14,400リクエスト/日**（個人利用なら実質無制限）

#### 4. 起動
```bash
python main.py
```

初回起動時にGroq API Keyの入力画面が表示されます。

**Windows:** `VoiceToText.vbs` をダブルクリックするとコンソール非表示で起動します。

#### 5. 使い方

- **F2**（またはFn+F2）を押す → 録音開始
- 話す
- **F2** をもう一度押す → 録音停止 → テキスト変換 → カーソル位置に挿入

#### フローティングボタン

画面右下にフローティングボタンが常時表示されます。どの画面でも見やすいグローリング付きデザインです。

- **マイクボタン** (上) → クリックで録音開始/停止（F2キーと同じ動作）
- **Enterボタン** (下) → クリックでEnterキーを送信（チャット送信などに便利）
- **ドラッグ** → 両ボタンまとめて好きな位置に移動
- 録音中はボタンとリングが **赤色** に変化
- ホットキーを設定画面で変更するとボタンのラベルも自動更新
- ボタンクリック時にフォーカスは奪われないため、テキスト入力中でも安心して使えます

### 音声コマンド

| 発話 | 出力 |
|------|------|
| エンター / 改行 | 改行（Enter） |
| まる / ピリオド | 。 |
| てん / カンマ | 、 |
| かっこ | （ |
| かっことじ | ） |
| かぎかっこ | 「 |
| かぎかっことじ | 」 |

### 設定

`config.json`（初回起動時に自動作成）を編集:

```json
{
  "api_key": "gsk_...",           // Groq API キー
  "hotkey": "f2",                  // 録音トグルのホットキー
  "mode": "toggle",               // "toggle"（トグル）または "push_to_talk"（押しっぱなし）
  "language": "ja",                // 言語コード
  "use_gemini_cleanup": false,     // Geminiによる句読点後処理（ONにすると精度UP、速度DOWN）
  "gemini_api_key": ""             // Gemini APIキー（オプション）
}
```

### 音声認識プロバイダーの選択

| プロバイダー | 速度 | 料金 | 取得先 |
|-------------|------|------|--------|
| **Groq Whisper**（デフォルト） | 約0.3秒 | 無料（14,400回/日） | https://console.groq.com |
| Gemini 2.5 Flash | 約2.5秒 | 約$0.0015/分 | https://aistudio.google.com/apikey |
| OpenAI Whisper | 約1-2秒 | $0.006/分 | https://platform.openai.com |

プロバイダーを変更するには `config.json` の `api_key` を変更してください。

### exe化（Windows）

```bash
build.bat
```

出力: `dist\VoiceToText.exe`

### インストール（他のPCへ配布）

1. `build.bat` を実行してexeを生成
2. `install.bat` を実行 → デスクトップに「Voice to Text」ショートカットが作成
3. `config.json` にAPIキーを入力
4. デスクトップの「Voice to Text」をダブルクリック

### Windows SmartScreen の警告について

初回起動時に「WindowsによってPCが保護されました」という青い画面が表示されることがあります。これはコード署名されていないアプリに対するWindowsの標準的な警告で、アプリ自体に問題があるわけではありません。

**回避手順:**

1. 青い画面で **「詳細情報」** をクリック
2. **「実行」** ボタンが表示されるのでクリック
3. 次回以降は表示されません

> このアプリはオープンソースです。ソースコードはすべて公開されており、安全性を確認できます。

### システムトレイメニュー

トレイアイコンを右クリック:
- モード切替（Push-to-Talk / Toggle）
- 設定を開く
- 自動起動 ON/OFF（Windowsログイン時）
- 終了

---

## English

AQUA Voice inspired voice-to-text desktop application. Press a hotkey, speak, and your words are transcribed and inserted at the cursor position in any application.

### Features

- **System-wide voice input** - Works in any app (Chrome, Word, VS Code, Slack, etc.)
- **Fast transcription** - Groq Whisper API (~0.3s latency)
- **Japanese optimized** - Excellent Japanese recognition with punctuation
- **Voice commands** - Say "enter" for newline, "period" for punctuation
- **Toggle mode** - Press F2 to start recording, press again to stop
- **Floating button** - Always-on-screen mic + Enter buttons with glow ring. Drag to reposition
- **System tray** - Runs quietly in the background
- **Recording overlay** - Waveform visualization while recording
- **Cross-platform** - Windows and macOS

### Quick Start

#### 1. Install Python 3.10+

#### 2. Install dependencies
```bash
pip install -r requirements.txt
```

#### 3. Get a Groq API Key (Free)

1. Go to https://console.groq.com
2. Sign up with Google account
3. Click **API Keys** in the left menu
4. Click **Create API Key**
5. Copy the key (starts with `gsk_...`)

Groq free tier: **14,400 requests/day** (practically unlimited for personal use).

#### 4. Run
```bash
python main.py
```

On first launch, enter your Groq API Key in the setup dialog.

**Windows:** Double-click `VoiceToText.vbs` to run without console window.

#### 5. Use

- **F2** (or Fn+F2) - Toggle recording on/off
- Speak naturally
- Text is inserted at cursor position

#### Floating Button

A floating button panel appears at the bottom-right of your screen, visible on any background thanks to a glow ring design.

- **Mic button** (top) - Click to start/stop recording (same as F2)
- **Enter button** (bottom) - Click to send Enter key (useful for sending chat messages)
- **Drag** - Move both buttons together anywhere on screen
- Button and ring turn **red** while recording
- Hotkey label updates automatically when changed in settings
- Clicking the buttons does **not** steal focus from your active app

### Voice Commands

| Say | Output |
|-----|--------|
| エンター / 改行 | Enter (newline) |
| まる / ピリオド | 。 |
| てん / カンマ | 、 |
| かっこ | （ |
| かっことじ | ） |
| かぎかっこ | 「 |
| かぎかっことじ | 」 |

### Configuration

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

### Alternative STT Providers

| Provider | Speed | Cost | Setup |
|----------|-------|------|-------|
| **Groq Whisper** (default) | ~0.3s | Free (14,400 req/day) | https://console.groq.com |
| Gemini 2.5 Flash | ~2.5s | ~$0.0015/min | https://aistudio.google.com/apikey |
| OpenAI Whisper | ~1-2s | $0.006/min | https://platform.openai.com |

To switch providers, change `api_key` in `config.json`.

### Build Executable (Windows)

```bash
build.bat
```

Output: `dist/VoiceToText.exe`

### Install (distribute to other PCs)

1. Run `build.bat` to generate exe
2. Run `install.bat` to create desktop shortcut "Voice to Text"
3. Edit `config.json` with your API key
4. Double-click "Voice to Text" on desktop

### Windows SmartScreen Warning

On first launch you may see a blue "Windows protected your PC" screen. This is a standard Windows warning for unsigned apps and does not mean there is anything wrong with the application.

**How to proceed:**

1. Click **"More info"** on the blue screen
2. Click the **"Run anyway"** button
3. The warning will not appear again after this

> This app is open source. All source code is publicly available for review.

### System Tray Menu

Right-click the tray icon for:
- Mode toggle (Push-to-Talk / Toggle)
- Settings
- Auto-start on Windows login (ON/OFF)
- Quit

---

## Tech Stack

- **STT**: Groq Whisper Large V3 Turbo (+ optional Gemini cleanup)
- **Audio**: sounddevice (16kHz mono)
- **VAD**: Silero VAD (silence removal)
- **Hotkey**: pynput (global hotkey)
- **Text Insert**: pyperclip + pyautogui (clipboard paste)
- **UI**: pystray (system tray) + tkinter (overlay/settings)

## License

MIT
