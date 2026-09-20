import React, { useState, useEffect, useRef } from 'react';
import { VoiceHero } from '../components/VoiceHero';
import { useIncident } from '../context/IncidentContext';
import { TypewriterText } from '../components/TypewriterText';
import { Mic, Send, Square, Clock, MessageSquare, Zap, CheckCircle2, Loader2, Trash2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Navigation } from '../App';
import './VoiceConsole.css';

export function VoiceConsole() {
  const { status, triggerEmergency, toolEvents, addLog } = useIncident();
  const [transcript, setTranscript] = useState<{ id: string, speaker: 'USER' | 'ALEXA'; text: string; isError?: boolean }[]>([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [inputText, setInputText] = useState('');
  const [showHero, setShowHero] = useState(false);
  
  // History Modal State
  const [showHistory, setShowHistory] = useState(false);
  const [historySessions, setHistorySessions] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [isVideoFading, setIsVideoFading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      // Start fade out 0.8s before the video ends to soften the loop
      if (video.duration - video.currentTime < 0.8) {
        setIsVideoFading(true);
      } else if (video.currentTime < 0.8) {
        // Fade back in at start
        setIsVideoFading(false);
      }
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, []);

  const scrollToBottom = (smooth = true) => {
    chatEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [transcript, isProcessing]);

  const openHistory = async () => {
    setShowHistory(true);
    setLoadingHistory(true);
    try {
      const res = await fetch('http://localhost:8000/api/history');
      if (res.ok) {
        const data = await res.json();
        setHistorySessions(data.conversations || []);
      }
    } catch(err) {
      console.error(err);
    }
    setLoadingHistory(false);
  };

  const deleteSession = async (sessionId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/history/${sessionId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setHistorySessions(prev => prev.filter(s => s.session_id !== sessionId));
        if (addLog) {
          addLog('EVENT', 'system', `Chat session deleted [${sessionId}]`);
        }
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const loadSession = (session: any) => {
    const newTranscript = session.messages.map((msg: any) => ({
      id: Math.random().toString(36).substr(2, 9),
      speaker: msg.role === 'user' ? 'USER' : 'ALEXA',
      text: msg.content
    }));
    setTranscript(newTranscript);
    setShowHistory(false);
  };

  const handleSend = async (e?: React.FormEvent, overridePrompt?: string) => {
    e?.preventDefault();
    const prompt = overridePrompt || inputText;
    if (!prompt.trim() && transcript.length > 0) return;
    
    setInputText('');
    
    // Add user message
    const updatedTranscript = [...transcript, { id: Math.random().toString(36).substr(2, 9), speaker: 'USER' as const, text: prompt }];
    setTranscript(updatedTranscript);
    
    // Set processing state
    setIsSpeaking(false);
    setIsProcessing(true);
    
    try {
      // Send to backend and wait for final text
      const history = updatedTranscript.map(t => ({ speaker: t.speaker, text: t.text }));
      const responseText = await triggerEmergency(prompt, history);
      
      setIsProcessing(false);
      // Add ALEXA response
      setTranscript(prev => [...prev, { id: Math.random().toString(36).substr(2, 9), speaker: 'ALEXA' as const, text: responseText }]);
      
      // Flash speaking UI
      setIsSpeaking(true);
      setTimeout(() => setIsSpeaking(false), 3000);
      
    } catch (err) {
      console.error(err);
      setIsProcessing(false);
      setTranscript(prev => [...prev, { id: Math.random().toString(36).substr(2, 9), speaker: 'ALEXA' as const, text: "I'm sorry, I'm having trouble connecting to the MEDUSA network.", isError: true }]);
    }
  };

  return (
    <div className="voice-console-container">
      <Navigation onOpenHistory={openHistory} />
      <video 
        ref={videoRef}
        className={`video-bg ${isVideoFading ? 'fading' : ''}`} 
        src="/vbg.mp4" 
        autoPlay 
        loop 
        muted 
        playsInline 
      />
      
      <div className="status-badge">
        <span className="dot" />
        <span className="status-text">MEDUSA CONNECTED</span>
      </div>

      <div className="secure-channel-overlay">
        <div className="sc-indicator" />
        <span>UTF-07</span>
      </div>

      {/* Top Section: AI Status */}
      <div className="visualizer-header">
        <div className={`orb-label ${isSpeaking ? 'speaking' : (isProcessing ? 'processing' : 'idle')}`}>
          {isSpeaking ? 'SPEAKING' : (isProcessing ? 'PROCESSING' : 'LISTENING')}
        </div>
      </div>

      {/* Center Section: The Chat Interface */}
      <div className="chat-window">
        <div className="chat-fade-top" />
        
        <AnimatePresence>
          {showHero && (
            <VoiceHero 
              isConversationActive={transcript.length > 0}
              onComplete={(voiceText) => {
                handleSend(undefined, voiceText);
              }} 
              onCancel={() => setShowHero(false)}
            />
          )}
        </AnimatePresence>

        <div className="chat-scroll-area">
          <AnimatePresence initial={false}>
            {transcript.map((line, index) => {
              // Only animate typewriter on the very last ALEXA message
              const isLatestAlexa = line.speaker === 'ALEXA' && index === transcript.length - 1;
              return (
                <motion.div 
                  key={line.id} 
                  className={`chat-bubble-wrapper ${line.speaker.toLowerCase()}`}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                >
                  <div className={`chat-bubble ${line.speaker.toLowerCase()} ${line.isError ? 'error-bubble' : ''}`}>
                    {line.speaker === 'ALEXA' ? (
                      <TypewriterText 
                        text={line.text} 
                        animate={isLatestAlexa} 
                        speed={12}
                        onTyping={() => scrollToBottom(false)}
                        onComplete={scrollToBottom}
                      />
                    ) : (
                      line.text
                    )}
                  </div>
                </motion.div>
              );
            })}
            {isProcessing && (
              <motion.div 
                key="processing"
                className="chat-bubble-wrapper alexa"
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <div className="chat-bubble alexa typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Tool Activity Panel */}
          <AnimatePresence>
            {toolEvents.length > 0 && (
              <motion.div
                className="tool-activity-panel"
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <div className="tool-panel-header">
                  <Zap size={14} color="#ff8c00" />
                  <span>MEDUSA Tools</span>
                </div>
                <div className="tool-panel-items">
                  {toolEvents.map((te) => (
                    <motion.div
                      key={te.id}
                      className={`tool-item ${te.status}`}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <div className="tool-item-icon">
                        {te.status === 'running' ? (
                          <Loader2 size={14} className="tool-spinner" />
                        ) : (
                          <CheckCircle2 size={14} />
                        )}
                      </div>
                      <span className="tool-item-name">{te.name.replace(/_/g, ' ')}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={chatEndRef} style={{ height: showHero && transcript.length > 0 ? '280px' : '150px', flexShrink: 0, width: '100%' }} />
        </div>
      </div>

      {/* Bottom Section: The Input Controls / Omnibar */}
      <AnimatePresence>
        {!showHero && (
          <motion.div 
            className={`input-area ${transcript.length === 0 ? 'omnibar-mode' : ''}`}
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            {transcript.length === 0 && (
              <motion.div className="omnibar-greeting" layout>
                <h2>How can I help?</h2>
                <p>Speak naturally. I’m listening.</p>
              </motion.div>
            )}

            <motion.form layout onSubmit={handleSend} className="input-bar glass-panel">
              <button 
                type="button"
                className={`mic-button ${isSpeaking ? 'active' : ''}`} 
                onClick={() => setShowHero(true)}
              >
                {isSpeaking ? <Square size={20} /> : <Mic size={20} />}
              </button>
              
              <input 
                type="text" 
                placeholder="Ask MEDUSA or describe the emergency..." 
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={isSpeaking || isProcessing}
              />
              
              <button type="submit" className="send-button" disabled={isSpeaking || isProcessing}>
                <Send size={20} />
              </button>
            </motion.form>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showHistory && (
          <motion.div 
            className="history-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowHistory(false)}
          >
            <motion.div 
              className="history-modal-content glass-panel"
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="history-modal-header">
                <div className="header-title">
                  <MessageSquare size={18} color="#ff8c00" />
                  <h2>Recent Chats</h2>
                </div>
                <button className="close-btn" onClick={() => setShowHistory(false)}>✕</button>
              </div>
              
              <div className="history-modal-body">
                {loadingHistory ? (
                  <div className="loading-state">
                    <span className="spinner"></span>
                    <p className="loading-text">Loading past emergencies...</p>
                  </div>
                ) : historySessions.length === 0 ? (
                  <p className="empty-text">No previous conversations found.</p>
                ) : (
                  historySessions.map(session => {
                    const isEmergency = session.messages.some((m: any) => 
                      m.role === 'assistant' && (
                        m.content.toLowerCase().includes('triage:') || 
                        m.content.toLowerCase().includes('incident') ||
                        m.content.toLowerCase().includes('emergency')
                      )
                    );
                    
                    return (
                    <div 
                      key={session.session_id} 
                      className={`history-session-item ${isEmergency ? 'emergency-session' : ''}`}
                      onClick={() => loadSession(session)}
                    >
                      <div className={`session-icon ${isEmergency ? 'emergency' : ''}`}>
                        {isEmergency ? <AlertTriangle size={16} /> : <MessageSquare size={16} />}
                      </div>
                      <div className="session-details">
                        <div className="session-preview">
                          {session.messages[0]?.content.substring(0, 80)}{session.messages[0]?.content.length > 80 ? '...' : ''}
                        </div>
                        <div className="session-meta">
                          <div className="session-date">
                            <Clock size={12} />
                            {new Date(session.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                          </div>
                        </div>
                      </div>
                      <button 
                        className="delete-session-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(session.session_id);
                        }}
                        title="Delete Chat"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                    );
                  })
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
