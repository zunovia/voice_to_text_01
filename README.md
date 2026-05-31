# Voice to Text

[English](#english) | [日本語](#日本語)

> **v3.0.1** — Groq 一本化・起動高速化（339MB→89MB）・AI校正モード・モダンUIに刷新

---

## 日本語

SuperWhisper / Aqua Voice にインスパイアされた音声入力デスクトップアプリです。ホットキーを押して話すだけで、文字起こし＋AI校正されたテキストがカーソル位置に挿入されます。**API は Groq 一本**（APIキー1つで完結）。

### 特徴

- **どのアプリでも使える** — Chrome、Word、VS Code、Slack など全てのアプリで動作
- **高速** — Groq Whisper で約0.3〜0.5秒。マイクは常時ウォーム状態なので**押した瞬間に録音開始**（オープン待ちゼロ）
- **軽量・速い起動** — torch を撤廃し exe は **約89MB**（旧339MB）。起動の待ち時間を大幅短縮
- **AI校正モード** — 句読点付与・フィラー除去に加え、**文脈から誤変換の漢字を自動修正**（例: 成形→整形、機械→機会）。整形 LLM は Groq `gpt-oss-20b`（プロンプトキャッシュ対応）
- **ユーザー辞書** — よく使う固有名詞・専門用語を登録すると Whisper の認識精度が向上
- **音声コマンド** — 「エンター」で改行、「まる」で句点など（最長一致で正確に変換）
- **モダンなフローティングボタン** — 画面右下に常時表示のティール／シアンの縦長カプセル。上＝マイク（録音ON/OFF）、下＝Enter。ドラッグで移動可能・常に最前面に自動固定
- **状態が一目でわかる** — 状態ドット（待機/録音/処理中/完了）。効果音（録音開始・停止・完了）は**既定OFF**・設定でON可能（音量は控えめ）
- **システムトレイ常駐** — バックグラウンドで静かに動作
- **波形オーバーレイ** — 録音中にリアルタイム波形表示

### インストール（exe版・推奨）

1. [最新リリース](https://github.com/zunovia/voice_to_text_01/releases/latest) から `VoiceToText-*.zip`（最新版）をダウンロード
2. ZIPを任意のフォルダに展開
3. `install.bat` をダブルクリックで実行
4. デスクトップに「Voice to Text」ショートカットが作成されます（OneDrive のデスクトップにも正しく対応）
5. ショートカットをダブルクリックで起動
6. 初回起動時に Groq API Key の入力画面が表示されます（取得方法は下記参照）

> **SmartScreenの警告が出た場合:** 「詳細情報」→「実行」をクリックしてください（初回のみ）

### Groq API キーの取得（無料・約3分）

このアプリを使うには **無料の Groq API キー** が必要です（利用者ごとに各自で取得）。初回起動時に入力を求められます。

1. https://console.groq.com にアクセス
2. Google アカウント等でサインアップ（無料・クレジットカード不要）
3. 左メニューの **API Keys** → **Create API Key**
4. 表示されたキー（`gsk_...` で始まる）をコピー
5. アプリ初回起動時の画面に貼り付けて「はじめる」をクリック

> 無料枠：音声認識 2,000回/日 ＋ 整形 14,400回/日。個人利用なら実質無料です。
> アプリの初回画面にも「取得する」リンクがあり、そこから取得ページを直接開けます。

### クイックスタート（ソースから実行）

#### 1. Python 3.10+ をインストール

#### 2. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```
> torch / silero-vad は不要になりました（無音判定は numpy の軽量 RMS ゲートに置換）。

#### 3. Groq API Key を取得（無料）

1. https://console.groq.com にアクセス
2. Googleアカウントでサインアップ
3. 左メニューの **API Keys** をクリック
4. **Create API Key** をクリック
5. キーをコピー（`gsk_...` で始まる）

Groq 無料枠: STT 2,000回/日 + LLM 14,400回/日（個人利用なら実質無料）

#### 4. 起動
```bash
python main.py
```

初回起動時に Groq API Key の入力画面が表示されます。

**Windows:** `VoiceToText.vbs` をダブルクリックするとコンソール非表示で起動します。

#### 5. 使い方

- **F2**（またはFn+F2）を押す → 録音開始（効果音＋ボタンがコーラルに点灯）
- 話す
- **F2** をもう一度押す → 録音停止 → 文字起こし＋校正 → カーソル位置に挿入

#### フローティングボタン

画面右下に、ティール／シアンの**縦長カプセル**が常時表示されます。

- **上＝マイク部**（ダーク＋ティールの円） → クリックで録音開始/停止（F2と同じ）。録音中は**コーラル（ピンク）**に点灯
- **下＝Enterバー**（明るいスレート色） → クリックで Enter キーを送信（チャット送信に便利）。色で上下を見分けやすく
- **ドラッグ** → カプセルごと好きな位置に移動
- 他アプリが全画面でも**自動で最前面に復帰**（1.5秒ごとに再固定）
- ボタンクリック時にフォーカスを奪わないため、テキスト入力中でも安心

### 音声コマンド

| 発話 | 出力 |
|------|------|
| エンター / 改行 | 改行（Enter） |
| まる / ピリオド | 。 |
| てん / カンマ | 、 |
| かっこ / かっことじ | （ / ） |
| かぎかっこ / かぎかっことじ | 「 / 」 |
| すみかっこ / すみかっことじ | 【 / 】 |

### 設定

トレイの「設定を開く」、または `config.json`（`%LOCALAPPDATA%\VoiceToText\config.json`）を編集:

```json
{
  "api_key": "gsk_...",                      // Groq API キー（STT + 校正LLM 共用）
  "hotkey": "f2",                             // 録音トグルのホットキー
  "mode": "toggle",                          // "toggle" または "push_to_talk"
  "language": "ja",                           // 言語コード
  "use_llm_cleanup": true,                   // AI校正（漢字修正・句読点・フィラー除去）
  "llm_provider": "groq",                    // Groq 固定
  "groq_llm_model": "openai/gpt-oss-20b",    // 校正LLM（キャッシュ対応・推奨）
  "stt_model": "whisper-large-v3-turbo",     // 認識モデル（turbo=高速 / whisper-large-v3=高精度）
  "vocabulary": "",                           // よく使う固有名詞・専門用語（スペース区切り・精度向上）
  "silence_threshold": 0.010,                // 無音判定のRMS閾値（小声を拾わない時は下げる）
  "sounds_enabled": false                    // 効果音（既定OFF・設定でON可・音量控えめ）
}
```

### 認識精度を上げるには

1. **ユーザー辞書**（設定の「認識精度」欄）— 固有名詞・専門用語を登録すると Whisper が正しい表記を選びやすくなる（最も安全で的確）
2. **AI校正モード**（既定ON）— 文脈から誤変換の漢字を自動修正
3. **認識モデルを `whisper-large-v3` に**（設定）— 基礎精度がわずかに向上

### exe化（Windows）

```bash
build.bat
```
出力: `dist\VoiceToText.exe`（約89MB）

> `pyinstaller` コマンドは PATH に無い場合があるため、`build.bat` は `python -m PyInstaller` を使用します。

### Windows の警告について

未署名アプリのため初回起動時に警告が出ることがあります（アプリに問題はありません）。

- **SmartScreen（青い画面）**: 「詳細情報」→「実行」
- **完全にブロックされる場合**: ファイルを右クリック → プロパティ → 「ブロックの解除」にチェック → OK（ZIPは解除後に再展開）
- それでも不可なら、ソースから `python main.py` で実行してください

> このアプリはオープンソースです。ソースコードはすべて公開されており、安全性を確認できます。

### システムトレイメニュー

トレイアイコンを右クリック:
- モード切替（Push-to-Talk / Toggle）
- 文章整形 ON/OFF
- 設定を開く
- 自動起動 ON/OFF（Windowsログイン時）
- 終了

---

## English

A SuperWhisper / Aqua Voice inspired voice-to-text desktop app. Press a hotkey, speak, and your words are transcribed, AI-corrected, and inserted at the cursor in any application. **Powered solely by Groq** (one API key).

### Features

- **System-wide voice input** — Works in any app (Chrome, Word, VS Code, Slack, etc.)
- **Fast** — ~0.3–0.5s via Groq Whisper. The mic is kept warm, so recording starts **the instant you press** (no open latency)
- **Lightweight, fast launch** — torch removed; the exe is **~89MB** (was 339MB)
- **AI correction mode** — Punctuation, filler removal, and **context-aware kanji homophone correction** (e.g. 成形→整形, 機械→機会). Cleanup runs on Groq `gpt-oss-20b` (prompt-cache eligible)
- **Custom dictionary** — Register frequent names/jargon to bias Whisper toward correct spellings
- **Voice commands** — Say "enter" for newline, "period" for punctuation (longest-match replacement)
- **Modern floating button** — A teal/cyan vertical capsule at the bottom-right: mic (top) + Enter (bottom). Draggable, auto-pinned to the top of the z-order
- **At-a-glance state** — Status dot (idle / listening / processing / done). Sound cues (start / stop / done) are **off by default** (enable in Settings; volume kept low)
- **System tray** — Runs quietly in the background
- **Recording overlay** — Live waveform while recording

### Install (exe — Recommended)

1. Download `VoiceToText-*.zip` (latest) from the [latest release](https://github.com/zunovia/voice_to_text_01/releases/latest)
2. Extract the ZIP to any folder
3. Double-click `install.bat`
4. A "Voice to Text" shortcut is created on your desktop (OneDrive desktops handled correctly)
5. Double-click the shortcut to launch
6. Enter your Groq API Key in the first-run dialog (see below)

> **If SmartScreen appears:** Click "More info" → "Run anyway" (first time only)

### Get a Groq API Key (free, ~3 min)

This app needs a **free Groq API key** (each user gets their own). You'll be prompted on first launch.

1. Go to https://console.groq.com
2. Sign up (free, no credit card)
3. **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)
5. Paste it into the first-run dialog and click Start

> Free tier: 2,000 STT + 14,400 LLM requests/day — effectively free for personal use. The first-run dialog also has a "Get key" link.

### Quick Start (from source)

```bash
pip install -r requirements.txt   # torch / silero-vad no longer required
python main.py
```

Get a free Groq API key at https://console.groq.com (API Keys → Create API Key). Free tier: 2,000 STT req/day + 14,400 LLM req/day.

**Windows:** double-click `VoiceToText.vbs` to run without a console window.

#### Use

- **F2** (or Fn+F2) — toggle recording (sound cue + button turns coral)
- Speak naturally
- Press **F2** again — transcribe + correct → inserted at the cursor

#### Floating Button

A teal/cyan **vertical capsule** at the bottom-right:

- **Mic (top)** — click to start/stop recording (same as F2); turns **coral** while recording
- **Enter bar (bottom, lighter slate)** — click to send the Enter key; the color difference makes the two halves easy to tell apart
- **Drag** to reposition; it auto-returns to the top even over fullscreen apps
- Clicking does **not** steal focus from your active app

### Configuration

Edit `config.json` (`%LOCALAPPDATA%\VoiceToText\config.json`) or use the Settings window:

```json
{
  "api_key": "gsk_...",                      // Groq API key (STT + cleanup LLM)
  "hotkey": "f2",
  "mode": "toggle",                          // "toggle" or "push_to_talk"
  "language": "ja",
  "use_llm_cleanup": true,                   // AI correction (kanji fix, punctuation, filler)
  "llm_provider": "groq",
  "groq_llm_model": "openai/gpt-oss-20b",    // cleanup model (cached, recommended)
  "stt_model": "whisper-large-v3-turbo",     // turbo (fast) or whisper-large-v3 (accurate)
  "vocabulary": "",                           // space-separated names/jargon to improve accuracy
  "silence_threshold": 0.010,                // RMS gate for empty-recording detection
  "sounds_enabled": false                    // sound cues: OFF by default, enable in Settings
}
```

### Improving accuracy

1. **Custom dictionary** (Settings → Accuracy) — safest, most targeted
2. **AI correction mode** (on by default) — fixes contextual kanji errors
3. **Switch STT model to `whisper-large-v3`** for slightly higher accuracy

### Build Executable (Windows)

```bash
build.bat   # uses "python -m PyInstaller"; output: dist/VoiceToText.exe (~89MB)
```

---

## Tech Stack

- **STT**: Groq Whisper Large V3 Turbo (`verbose_json` segment filtering to suppress hallucinations)
- **AI cleanup / correction**: Groq `gpt-oss-20b` (prompt caching, `reasoning_effort=low`)
- **Audio**: sounddevice (16kHz mono, warm/persistent stream for zero-latency start)
- **Empty-detection**: lightweight numpy RMS energy gate (no torch / Silero)
- **Hotkey**: pynput (global hotkey)
- **Text insert**: pyperclip + pyautogui (clipboard paste)
- **UI**: pystray (tray) + tkinter (overlay / capsule button / settings)
- **Sound cues**: winsound + numpy-synthesized WAVs (no extra dependency)
- **Packaging**: PyInstaller (onefile)

## License

MIT
