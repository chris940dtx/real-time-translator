//hook to capture audio
import { useState, useRef, useEffect } from "react";

const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const BIT_DEPTH = 16;

export function useAudioRecorder(onAudioChunk: (pcmData: ArrayBuffer) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  //refs to store audio contxt and nodes
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  //func to convert Float32Array to PCM16

  const startRecording = async () => {
    try {
      setError(null);

      //step1 request mic access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: CHANNELS,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;

      //step2 create audioContext
      const audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)({
        sampleRate: SAMPLE_RATE,
      });
      audioContextRef.current = audioContext;

      //step3 load worklet module from our js file in public
      // we need it to be in public bc needs to be loaded by url, '/public' files are served
      //as-is at the site root
      await audioContext.audioWorklet.addModule("/pcm-processor.js");

      //step4 creating worklet node
      const processorNode = new AudioWorkletNode(audioContext, "pcm-processor");
      processorNodeRef.current = processorNode;

      //step5 create source node(connect mic to audio graph)
      const sourceNode = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = sourceNode;

      //step6 listen for processed PCM from worklet
      processorNode.port.onmessage = (event) => {
        const pcmBuffer: ArrayBuffer = event.data;
        //sendpcm data via callback
        onAudioChunk(pcmBuffer);
      };

      //step 6 connect nodes
      sourceNode.connect(processorNode); // conncecting mic to worklet

      setIsRecording(true);
    } catch (err) {
      setError(
        "Failed to access microphone: " +
          (err instanceof Error ? err.message : "Unknown error")
      );
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    //disconnect all nodes
    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    ///close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    //stop mic stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    setIsRecording(false);
  };

  //cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, []);

  return {
    isRecording,
    error,
    startRecording,
    stopRecording,
  };
}
