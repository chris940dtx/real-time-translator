//hook to capture audio
import {useState, useRef, useEffect } from 'react';

export function useAudioRecorder(onAudioChunk: (blob: Blob) => void) {
    const [isRecording, SetIsRecording] = useState(false); // check recording
    const [error, setError] = useState<string | null>(null); // error message(like permission denied)
    const mediaRecorderRef = useRef<MediaRecorder | null>(null); // store mediaRecord instance
    const streamRef = useRef<MediaStream | null>(null);// store audio stream

    // func to start recording
    const startRecording = async () => {
        try {
            setError(null);

            //requesting access to mic
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true // only audio, not video
            });

            streamRef.current = stream; 

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm'
            });

            //save recorder to control it
            mediaRecorderRef.current = mediaRecorder; 

            // event that mediaRecorder has audio data ready and sends it via webSocket
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0){
                    onAudioChunk(event.data);
                }
            }

            //start recording with 250 mls chunks
            mediaRecorder.start(250);

            SetIsRecording(true);

        } catch (err) {
            setError('failed to access microphone: ' + (err instanceof Error ? err.message : 'Unknown error'));
            SetIsRecording(false);
        }
    };

    //Func to stop recording
    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive'){
            mediaRecorderRef.current.stop();
        }

        //stop everything in the stream (release mic)
        if(streamRef.current){
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }

        SetIsRecording(false);
    };

    //cleanup for component unmount
    useEffect(() => {
        return () => {
            stopRecording();
        };
    }, []);

    return{
        isRecording,
        error,
        startRecording,
        stopRecording,
    };
}