from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
#from deepgram.extensions.types.sockets import ListenV1SocketClientResponse, ListenV1MediaMessage 
from typing import Any
from deepl.exceptions import DeepLException

from translation import translate_text_sync

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
#check if key is valid 
if not DEEPGRAM_API_KEY:
    raise ValueError("Deepgram api key not found in enviorment variables")

deepgram_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)

# Thread pool for running sync DeepL calls so we don't block the event loop
_translation_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="deepl")

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    #client connection
    await websocket.accept()
    #then with already being connected make
    #Deepgram connection session  
    loop = asyncio.get_running_loop()
    async with deepgram_client.listen.v1.connect(
        model="nova-3",
        encoding="linear16",  # PCM16 encoding
        sample_rate=16000,     # 16kHz sample rate
        channels=1             # Mono
    ) as connection:
        connection_open = True

        #callback to receive transcript, ITS SYNC function not async
        #:. create_task() is used to schedule onto our outter Websocket loop
        #if msg not = "Reseults", return
        #extract transcript into "text" from channel.alt[0].transc
        #if txt is emtpy , return
        async def translate_and_send(text: str) -> None:
            try:
                translated = await loop.run_in_executor(
                    _translation_executor, translate_text_sync, text
                )
                await websocket.send_text(translated)
            except DeepLException as e:
                print(f"[DeepL error] {e}")
                await websocket.send_text(text)  # fallback: send original transcript
            except Exception as e:
                print(f"[Translation error] {e}")
                await websocket.send_text(text)

        def on_transcript(message: Any) -> None:

            if getattr(message, "type", None) != "Results":
                return
            
            try:
                alts = getattr(getattr(message, "channel", None), "alternatives", None) or []
                if not alts:
                    return
                text = getattr(alts[0], "transcript", "") or ""
                if not text:
                    return
                print(f"[Transcript] {text!r}")
                # translate in thread, then send translated text to client
                loop.create_task(translate_and_send(text))
            except Exception:
                return

        def on_error(error: Any) -> None:
            nonlocal connection_open
            print(f"Deepgram error: {error}")
            connection_open = False

        def on_close(_: Any) -> None:
            nonlocal connection_open
            print("Deepgram connection closed")
            connection_open = False

        #registered callbacks with deepgram
        connection.on(EventType.MESSAGE, on_transcript)  #when transcrtipt arrives
        connection.on(EventType.OPEN, lambda _: print("Deepgram connected"))# when connected
        connection.on(EventType.ERROR, lambda e: print(f"Deepgram error: {e}"))# on error 
        connection.on(EventType.CLOSE, on_close)

        #start_listening() running on background 
        listening_task = asyncio.create_task(connection.start_listening())
        print("Started listening to Deepgram")

        #main loop; receive audio from client and forwarf to Deepgram
        try:

            while True: #keep going and ea inner try has a specific handle case if its hit and does not stop the while loop
                #while stops when and it hits the "WebSocketDisconnect" 
                    msg = await websocket.receive() 
                    if "bytes" in msg: 
                        audio_chunk = msg["bytes"]
                        print(f"Received PCM16 audio chunk: {len(audio_chunk)} bytes")

                        if connection_open:
                            try:
                                await connection.send_media(audio_chunk)
                            except Exception as e:
                                print(f"Error sending media: {e}")
                                if not connection_open:
                                    break
                        else: 
                            print("deepgram connection closed, cannot send audio")
                            break
                    elif "text" in msg:
                        #text logic
                        await websocket.send_text(f"Echo: {msg['text']}")
                        continue
 
                    else:
                        print("unexpected message type")
                        break
                    continue 
        #cleanup w/ disconnect
        except WebSocketDisconnect:
            print("Client disconnected")
        finally:
            listening_task.cancel() #exit "asyn with" and close DG connection
            try:
                await listening_task
            except asyncio.CancelledError:
                pass
