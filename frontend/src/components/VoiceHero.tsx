import React, { useState, useEffect, useRef } from 'react';
import { Mic } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './VoiceHero.css';

// Declare Web Speech API types for TypeScript
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface VoiceHeroProps {
  isConversationActive?: boolean;
  onComplete: (text: string) => void;
  onCancel: () => void;
}

export function VoiceHero({ isConversationActive, onComplete, onCancel }: VoiceHeroProps) {
  const [isListening, setIsListening] = useState(false);
  const [transcriptText, setTranscriptText] = useState('');
  const recognitionRef = useRef<any>(null);

  const handleClick = () => {
    if (isListening) {
      // If already listening, stop it manually
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    // Not using continuous=true because we want it to stop automatically when the user pauses
    recognition.continuous = false; 
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    setIsListening(true);
    setTranscriptText('');

    let finalTranscript = '';

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }
      setTranscriptText(finalTranscript + interimTranscript);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error", event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      // Wait a tiny bit for state to settle, then complete
      setTimeout(() => {
        if (finalTranscript.trim()) {
            onComplete(finalTranscript.trim());
        } else {
            // If nothing was captured, just cancel back to keyboard
            onCancel();
        }
      }, 100);
    };

    try {
      recognition.start();
    } catch (e) {
      console.error(e);
      setIsListening(false);
    }
  };

  // Generate random heights for waveform bars
  const generateWaveform = (count: number) => {
    return Array.from({ length: count }).map((_, i) => (
      <motion.div
        key={i}
        className="waveform-bar"
        animate={isListening ? {
          height: [10, Math.random() * 50 + 20, 10],
        } : { height: 4 }}
        transition={{
          repeat: Infinity,
          duration: Math.random() * 0.5 + 0.3,
          ease: 'easeInOut',
        }}
      />
    ));
  };

  return (
    <motion.div 
      className={`voice-hero-container ${isConversationActive ? 'docked-bottom' : 'centered'}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1, filter: 'blur(10px)' }}
      transition={{ duration: 0.5 }}
    >
      <div className="voice-hero-content">
        {/* Left Waveform */}
        <div className="waveform left">
          {generateWaveform(12)}
        </div>

        {/* Central Mic Button */}
        <div className={`mic-center-wrapper ${isListening ? 'listening' : ''}`} onClick={handleClick}>
          <div className="pulse-ring ring-1" />
          <div className="pulse-ring ring-2" />
          <div className="pulse-ring ring-3" />
          
          <div className="mic-center-button">
            <Mic size={48} className="mic-icon" />
          </div>
        </div>

        {/* Right Waveform */}
        <div className="waveform right">
          {generateWaveform(12)}
        </div>
      </div>

      <div className="voice-hero-status">
        <h2 className="status-title">{isListening ? 'Listening...' : 'Tap to speak'}</h2>
        {!isListening && (
          <button className="switch-to-text-button" onClick={onCancel}>
            Switch to Keyboard
          </button>
        )}
        {isListening && (
          <p className="status-subtitle">{transcriptText || "Tell me what's happening..."}</p>
        )}
      </div>
    </motion.div>
  );
}
