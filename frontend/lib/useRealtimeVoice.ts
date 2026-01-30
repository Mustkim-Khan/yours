'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface UIAction {
  action: string;
  data: Record<string, unknown>;
}

interface UseRealtimeVoiceReturn {
  isConnected: boolean;
  isConnecting: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  error: string | null;
  sessionId: string | null;
  connect: (conversationId?: string) => Promise<void>;
  disconnect: () => void;
  startListening: () => Promise<void>;
  stopListening: () => void;
  cancelResponse: () => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace('http://', 'ws://').replace('https://', 'wss://');

// PCM16 parameters expected by OpenAI Realtime API
const SAMPLE_RATE = 24000;

export function useRealtimeVoice(
  onUIAction?: (action: UIAction) => void
): UseRealtimeVoiceReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const captureContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const audioChunkCountRef = useRef(0);

  // Convert Float32 samples to Int16 (PCM16)
  const floatTo16BitPCM = useCallback((float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  }, []);

  // Resample audio to 24kHz using simple linear interpolation
  const resampleTo24kHz = useCallback((
    inputBuffer: Float32Array, 
    inputSampleRate: number
  ): Float32Array => {
    if (inputSampleRate === SAMPLE_RATE) {
      return inputBuffer;
    }
    
    const ratio = inputSampleRate / SAMPLE_RATE;
    const outputLength = Math.floor(inputBuffer.length / ratio);
    const output = new Float32Array(outputLength);
    
    for (let i = 0; i < outputLength; i++) {
      const sourceIndex = i * ratio;
      const index = Math.floor(sourceIndex);
      const fraction = sourceIndex - index;
      
      if (index + 1 < inputBuffer.length) {
        output[i] = inputBuffer[index] * (1 - fraction) + inputBuffer[index + 1] * fraction;
      } else {
        output[i] = inputBuffer[index] || 0;
      }
    }
    
    return output;
  }, []);

  // Play audio queue
  const playNextAudio = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    // Create playback context if needed
    if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
      playbackContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });
    }

    const audioContext = playbackContextRef.current;
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }

    isPlayingRef.current = true;
    setIsSpeaking(true);

    while (audioQueueRef.current.length > 0) {
      const samples = audioQueueRef.current.shift()!;
      
      // Create audio buffer
      const buffer = audioContext.createBuffer(1, samples.length, SAMPLE_RATE);
      buffer.copyToChannel(new Float32Array(samples), 0);

      // Play the buffer
      const source = audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(audioContext.destination);
      
      await new Promise<void>((resolve) => {
        source.onended = () => resolve();
        source.start();
      });
    }

    isPlayingRef.current = false;
    setIsSpeaking(false);
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback(async (event: MessageEvent) => {
    // Binary data = audio response
    if (event.data instanceof Blob) {
      const arrayBuffer = await event.data.arrayBuffer();
      const int16Array = new Int16Array(arrayBuffer);
      
      // Convert Int16 to Float32 for Web Audio API
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768;
      }
      
      audioQueueRef.current.push(float32Array);
      playNextAudio();
      return;
    }

    // Text data = JSON message
    try {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'ready':
          console.log('✅ Realtime voice session ready:', message.session_id);
          setSessionId(message.session_id);
          setIsConnected(true);
          setIsConnecting(false);
          setError(null);
          break;
          
        case 'ui_action':
          console.log('🎨 UI Action:', message.action);
          if (onUIAction) {
            onUIAction(message as UIAction);
          }
          break;
          
        case 'response_done':
          console.log('✅ Response complete');
          break;
          
        case 'error':
          console.error('❌ Realtime error:', message.message);
          setError(message.message);
          setIsConnecting(false);
          break;
          
        case 'disconnected':
          setIsConnected(false);
          setIsConnecting(false);
          break;
      }
    } catch (e) {
      console.error('Failed to parse message:', e);
    }
  }, [onUIAction, playNextAudio]);

  // Connect to backend WebSocket
  const connect = useCallback(async (conversationId?: string) => {
    try {
      setError(null);
      setIsConnecting(true);
      
      // Get user ID from localStorage or auth
      const userId = localStorage.getItem('firebase_user_id') || 'anonymous';
      
      // Create WebSocket connection
      const ws = new WebSocket(`${WS_URL}/ws/realtime-voice/${userId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('🔌 WebSocket connected');
        // Send start message
        ws.send(JSON.stringify({
          type: 'start',
          conversation_id: conversationId
        }));
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('❌ WebSocket error:', event);
        setError('Failed to connect to OpenAI');
        setIsConnected(false);
        setIsConnecting(false);
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        setIsConnected(false);
        setIsConnecting(false);
        setIsListening(false);
        setSessionId(null);
      };

    } catch (e) {
      console.error('Failed to connect:', e);
      setError('Failed to connect');
      setIsConnecting(false);
    }
  }, [handleMessage]);

  // Disconnect
  const disconnect = useCallback(() => {
    // Stop listening first
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (captureContextRef.current && captureContextRef.current.state !== 'closed') {
      captureContextRef.current.close();
      captureContextRef.current = null;
    }
    
    // Close WebSocket
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'close' }));
      } catch (e) {
        // Ignore send errors on close
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    setIsListening(false);
    setSessionId(null);
    audioChunkCountRef.current = 0;
  }, []);

  // Start listening (capture microphone)
  const startListening = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    try {
      console.log('🎤 Starting microphone capture...');
      audioChunkCountRef.current = 0;
      
      // Get microphone stream - request specific sample rate
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        } 
      });
      streamRef.current = stream;
      console.log('🎤 Microphone access granted');

      // Create audio context for capture
      const audioContext = new AudioContext();
      captureContextRef.current = audioContext;
      console.log(`🎤 AudioContext created, sample rate: ${audioContext.sampleRate}`);
      
      // Resume context if suspended
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
        console.log('🎤 AudioContext resumed');
      }

      // Create source from microphone
      const source = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // Use ScriptProcessor for audio capture
      const bufferSize = 4096;
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
      processorRef.current = processor;
      
      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }
        
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Check if there's actual audio data (not silence)
        let maxAmp = 0;
        for (let i = 0; i < inputData.length; i++) {
          const amp = Math.abs(inputData[i]);
          if (amp > maxAmp) maxAmp = amp;
        }
        
        // Skip very quiet chunks (noise floor)
        if (maxAmp < 0.001) {
          return;
        }
        
        // Resample to 24kHz
        const resampled = resampleTo24kHz(new Float32Array(inputData), audioContext.sampleRate);
        
        // Convert to PCM16
        const pcm16 = floatTo16BitPCM(resampled);
        
        // Send as binary ArrayBuffer
        try {
          wsRef.current.send(pcm16.buffer);
          audioChunkCountRef.current++;
          
          // Log every 10th chunk
          if (audioChunkCountRef.current % 10 === 0) {
            console.log(`🎵 Sent ${audioChunkCountRef.current} audio chunks, maxAmp: ${maxAmp.toFixed(3)}`);
          }
        } catch (e) {
          console.error('Failed to send audio:', e);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      
      console.log('🎤 Audio capture started');
      setIsListening(true);
      setError(null);
      
    } catch (e) {
      console.error('Failed to start listening:', e);
      setError('Failed to access microphone');
    }
  }, [floatTo16BitPCM, resampleTo24kHz]);

  // Stop listening
  const stopListening = useCallback(() => {
    console.log(`🛑 Stopping listening, sent ${audioChunkCountRef.current} chunks total`);
    
    // Stop processor first
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }

    // Stop microphone stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    // Close capture context
    if (captureContextRef.current && captureContextRef.current.state !== 'closed') {
      captureContextRef.current.close();
      captureContextRef.current = null;
    }

    // Send audio end signal AFTER stopping capture
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('📤 Sending audio_end signal');
      wsRef.current.send(JSON.stringify({ type: 'audio_end' }));
    }

    setIsListening(false);
  }, []);

  // Cancel current response
  const cancelResponse = useCallback(() => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsSpeaking(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (playbackContextRef.current && playbackContextRef.current.state !== 'closed') {
        playbackContextRef.current.close();
      }
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    isListening,
    isSpeaking,
    error,
    sessionId,
    connect,
    disconnect,
    startListening,
    stopListening,
    cancelResponse,
  };
}

export default useRealtimeVoice;
