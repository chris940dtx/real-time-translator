//runs in audio thread
class PCMProcessor extends AudioWorkletProcessor {
    //helper:coverter Float32 samples to 16bit PCM
  convertFloat32ToPCM16(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);

    for (let i = 0; i < float32Array.length; i++) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      view.setInt16(i * 2, intSample, true);
    }

    return buffer;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0 ) {
        return true; // keep processor alive if even no input yet
    }

    const channelData = input[0];
    const pcmBuffer = this.convertFloat32ToPCM16(channelData);

    //send PCM bytes back to the main thread
    this.port.postMessage(pcmBuffer);

    return true; //returning true to keep processor running
  }
}

//'pcm-processor' will be referenced when creating AudioWorkletNode
registerProcessor('pcm-processor', PCMProcessor);
