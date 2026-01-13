from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from io import BytesIO
from pydub import AudioSegment
import base64

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

def convert_webm_to_pcm(webm_data: bytes) -> bytes:
    #create AudioSegment from WebM bytes
    audio = AudioSegment.from_file(BytesIO(webm_data), format="wbem")

    #convert to requried format AWS transcribe needs
    audio = audio.set_frame_rate(1600)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)  

    #export as raw PCM
    pcm_buffer = BytesIO()
    audio.export(pcm_buffer, format="raw")

    return pcm_buffer.getvalue()

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
                print(f"Received audio chunk: {len(message)} bytes")
                
                #convert WebM to PCM
                try:
                    pcm_audio = convert_webm_to_pcm(message)
                    print(f"converted to PCM: {len(pcm_audio)} bytes")
                    await websocket.send_text("Audio converted successfully")
                except Exception as e:
                    print(f"Converison error: {e}")
                    await websocket.send_text(f"conversion failed: {str(e)}")

    except WebSocketDisconnect:
        print("Client disconnected")