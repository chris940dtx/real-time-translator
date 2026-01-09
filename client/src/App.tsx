import { useState } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useAudioRecorder } from "./hooks/useAudioRecorder";

function App() {
  const { isConnected, messages, sendMessage, sendAudioChunk } = useWebSocket(
    "ws://localhost:8000/ws"
  );
  //handles audio chunks, runs every time we get audio data
  const handleAudioChunk = (blob: Blob) => {
    console.log("handleAudioChunk called, blob size:", blob.size, "bytes");
    //send audio chunk to server via websocket
    sendAudioChunk(blob);
  };
  //audio recorder hook, passing handler func
  const { isRecording, error, startRecording, stopRecording } =
    useAudioRecorder(handleAudioChunk);

  return (
    <div style={{ padding: "20px" }}>
      <h1>Real Time Translator</h1>

      <p>Status: {isConnected ? "Connected" : "Disconnected"}</p>
      <p>Recording: {isRecording ? "Recording" : "Not recording"}</p>

      {/*Error display */}
      {error && <p style={{ color: "red" }}>Error: {error} </p>}

      {/*Start and stop recoding button*/}
      <div style={{ marginTop: "20px" }}>
        <button onClick={startRecording} disabled={!isConnected || isRecording}>
          {" "}
          Start Recording{" "}
        </button>

        <button onClick={stopRecording} disabled={!isRecording}>
          Stop Recording
        </button>
      </div>

      {/*Messages dislpayed(subtitles) */}
      <div style={{ marginTop: "30px" }}>
        <h2>Subtitles:</h2>
        {messages.length === 0 ? (
          <p style={{ color: "grey" }}>No subtitles yet</p>
        ) : (
          <div>
            {messages.map((msg, index) => (
              <div key={index}>{msg.text}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
