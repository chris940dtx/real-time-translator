# Real-Time English → Spanish Subtitle Generator

A web app that streams your microphone to the server, transcribes speech in real time with **Deepgram**, translates the transcript to Spanish with **DeepL**, and displays the translated text as live subtitles in the browser.

---

## What It Does

1. **Client**: You click “Start Recording.” The app captures your microphone, converts audio to 16-bit PCM at 16 kHz, and streams it over a WebSocket to the server.
2. **Server**: Receives the audio stream, forwards it to Deepgram’s real-time speech API, and gets back English transcripts.
3. **Translation**: Each transcript segment is sent to DeepL (English → Spanish) on a thread pool so the WebSocket loop stays responsive.
4. **Subtitles**: The server sends the translated text back over the same WebSocket; the client appends it to the “Subtitles” list so you see live Spanish subtitles as you speak.

---

## Architecture Overview

```
[Browser]  →  Mic  →  AudioWorklet (Float32 → PCM16)  →  WebSocket (binary)
                                                                  ↓
[Server]   ←  WebSocket  ←  Deepgram (transcript)  ←  Deepgram real-time API
     ↓
  DeepL (EN → ES)  →  WebSocket  →  [Browser]  →  Subtitles UI
```

- **Client**: React + TypeScript (Vite). Uses the Web Audio API and an **Audio Worklet** (`pcm-processor.js`) to turn mic input into PCM16 chunks without blocking the main thread.
- **Server**: FastAPI (Python). Holds one WebSocket per client; for each client it opens a Deepgram live connection, pipes received audio to Deepgram, and on each transcript runs DeepL in a thread pool and sends the result back over the WebSocket.

---

## Tech Stack

| Layer   | Technology |
|--------|------------|
| Client | React 19, TypeScript, Vite |
| Audio  | Web Audio API, AudioWorklet (PCM16 @ 16 kHz mono) |
| Transport | WebSocket (binary audio up, text down) |
| Server | FastAPI, Uvicorn |
| Speech | Deepgram (Nova 3, live streaming) |
| Translation | DeepL API (sync, via thread pool) |

---

## Project Structure

```
real-time-translator/
├── client/                    # React frontend
│   ├── public/
│   │   └── pcm-processor.js   # AudioWorklet: Float32 → PCM16
│   ├── src/
│   │   ├── App.tsx            # UI, wires recorder + WebSocket + subtitles
│   │   ├── main.tsx
│   │   └── hooks/
│   │       ├── useAudioRecorder.ts  # Mic capture, worklet, PCM callback
│   │       └── useWebSocket.ts      # WS connection, send audio/text, receive subtitles
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── server/
│   ├── main.py                # FastAPI app, /ws WebSocket, Deepgram live, DeepL bridge
│   ├── translation.py         # DeepL sync translation (used via run_in_executor)
│   ├── requirements.txt
│   └── .env                   # API keys (create from .env.example; do not commit)
└── README.md
```

---

## Prerequisites

- **Node.js** (for the client; LTS is fine)
- **Python 3.10+** (for the server)
- **Deepgram** API key ([sign up](https://deepgram.com/))
- **DeepL** API key ([sign up](https://www.deepl.com/pro-api); free tier available)

---

## Setup and Run

### 1. Server

```bash
cd server
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

Create `server/.env` (never commit real keys):

```env
# Deepgram (required)
DEEPGRAM_API_KEY=your_deepgram_api_key

# DeepL (required for translation)
DEEPL_AUTH_KEY=your_deepl_auth_key
DEEPL_SOURCE_LANG=EN
DEEPL_TARGET_LANG=ES
```

- `DEEPL_SOURCE_LANG`: source language (e.g. `EN`). Omit or leave empty for auto-detect.
- `DEEPL_TARGET_LANG`: target language (e.g. `ES`, `DE`).

Start the server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- WebSocket: `ws://localhost:8000/ws`

### 2. Client

```bash
cd client
npm install
npm run dev
```

Open the URL Vite prints (e.g. [http://localhost:5173](http://localhost:5173)).

### 3. Use the App

1. Make sure the client shows “Connected.”
2. Click **Start Recording** and allow microphone access.
3. Speak in English; Spanish subtitles appear below as Deepgram and DeepL process the stream.
4. Click **Stop Recording** when done.

---

## How It Works (In More Detail)

### Client

- **`useAudioRecorder`**: Requests the mic, creates an `AudioContext` at 16 kHz, loads the Audio Worklet from `/pcm-processor.js`, and connects: `MediaStreamSource → AudioWorkletNode`. The worklet converts Float32 samples to PCM16 and posts `ArrayBuffer`s to the main thread; the hook forwards each buffer to your callback (`handleAudioChunk`).
- **`useWebSocket`**: Connects to `ws://localhost:8000/ws`, exposes `sendAudioChunk(ArrayBuffer)` and `sendMessage(string)`, and pushes every incoming text message into `messages` (with a timestamp) for the UI.
- **`App`**: Uses `useWebSocket` and `useAudioRecorder(handleAudioChunk)`. On each PCM chunk it calls `sendAudioChunk(pcmData)`; each incoming WebSocket text is a translated subtitle line.

### Server

- **`main.py`**:  
  - On WebSocket connect, opens a Deepgram live connection (Nova 3, `linear16`, 16 kHz, mono).  
  - Registers a transcript callback: when Deepgram sends a “Results” message with a transcript, it runs `translate_text_sync(text)` in a thread pool (`run_in_executor`) and sends the result back over the WebSocket (or the original text on DeepL failure).  
  - Main loop: reads WebSocket messages; binary messages are forwarded to Deepgram with `send_media`; text messages are echoed for debugging.  
  - On disconnect, the Deepgram listening task is cancelled and the connection is closed.

- **`translation.py`**: Loads `DEEPL_AUTH_KEY`, `DEEPL_SOURCE_LANG`, `DEEPL_TARGET_LANG` from the environment, keeps a single DeepL `Translator` instance, and exposes `translate_text_sync(text)` for use from the thread pool.

### Audio Format

- The worklet and server expect **16 kHz, mono, 16-bit PCM**. The client configures the `AudioContext` and mic constraints for 16 kHz mono; the worklet converts Float32 to PCM16 so Deepgram’s `linear16` setting matches.

---

## Configuration

| Variable | Where | Description |
|----------|--------|-------------|
| `DEEPGRAM_API_KEY` | `server/.env` | Required. Deepgram API key. |
| `DEEPL_AUTH_KEY` | `server/.env` | Required for translation. DeepL auth key (e.g. `xxx:fx` for free). |
| `DEEPL_SOURCE_LANG` | `server/.env` | e.g. `EN`. Empty/omit for auto-detect. |
| `DEEPL_TARGET_LANG` | `server/.env` | e.g. `ES`, `DE`. Default `ES`. |
| WebSocket URL | `client/src/App.tsx` | Default `ws://localhost:8000/ws`. Change host/port if you run server elsewhere. |

---

## Security and Environment

- **Do not commit** `server/.env` or any file containing real API keys. The repo’s `.gitignore` already excludes `.env` and `server/.env`.
- For production, use env vars or a secrets manager; keep keys out of the client (the client never sees Deepgram or DeepL keys).

---

## Possible Next Steps

- Add CORS in FastAPI if the client is served from another origin.
- Support other languages by changing `DEEPL_SOURCE_LANG` / `DEEPL_TARGET_LANG` or adding a language picker that sends target lang to the server.
- Add a “Clear subtitles” button and optionally cap the number of lines shown.
- Harden error handling and reconnection logic on the client (e.g. reconnect WebSocket on disconnect).

---

## License

Use and modify as you like; ensure you comply with Deepgram’s and DeepL’s API terms.
