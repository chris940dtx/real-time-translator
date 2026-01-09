from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

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
                await websocket.send_text("Audio chunk received")

    except WebSocketDisconnect:
        print("Client disconnected")