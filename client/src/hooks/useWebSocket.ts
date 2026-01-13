import { useState, useEffect, useRef } from "react";

interface Message {
  text: string;
  timestamp: Date;
}

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log("WebSocket connected!");
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      const receivedText = event.data;

      setMessages((prev) => [
        ...prev,
        {
          text: receivedText,
          timestamp: new Date(),
        },
      ]);
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
    };

    ws.current.onerror = (error) => {
      console.log("WebSocket error:", error);
      setIsConnected(false);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendMessage = (message: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message);
    } else {
      console.warn("WebSocket is not connected");
    }
  };

  const sendAudioChunk = (audioBlob: Blob) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(audioBlob);
    }
  };

  return {
    isConnected,
    messages,
    sendMessage,
    sendAudioChunk,
  };
}
