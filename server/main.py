from dotenv import load_dotenv
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
#from deepgram.extensions.types.sockets import ListenV1SocketClientResponse, ListenV1MediaMessage 
from typing import Any

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
#check if key is valid 
if not DEEPGRAM_API_KEY:
    raise ValueError("Deepgram api key not found in enviorment variables")

deepgram_client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)

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

        #callback to receive transcript
        #if msg not = "Reseults", return
        #extract transcript into "text" from channel.alt[0].transc
        #if txt is emtpy , return
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
                loop.create_task(websocket.send_text(text))
            except Exception:
                return
            #test to see deepgram response format
            #transcript_text = parse_transcript(message)
            #loop.create_task(websocket.send_text(transcript_text)) # need callback to be async

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
