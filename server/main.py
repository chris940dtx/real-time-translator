from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from io import BytesIO
import base64

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

def process_pcm_audio(pcm_data: bytes) -> bytes:
    return pcm_data

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            #receive data and check if its text or binary 
            try: 
                #try to receive as text first 
                data = await websocket.receive_text()
                #if its text, echo it back
                await websocket.send_text(f"Echo: {data}")
            except:
                #if txt fails, its binary(audio)
                message = await websocket.receive_bytes()
                print(f"Received PCM16 audio chunk: {len(message)} bytes")
                
                #process PCM16 data
                try:
                    processed_audio = process_pcm_audio(message)
                    print(f"Processed PCM16: {len(processed_audio)} bytes")
                    await websocket.send_text("Audio received successfully")
                except Exception as e:
                    print(f"Converison error: {e}")
                    await websocket.send_text(f"conversion failed: {str(e)}")

    except WebSocketDisconnect:
        print("Client disconnected")