import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

interface TypewriterTextProps {
  text: string;
  speed?: number;
  animate?: boolean;
  onComplete?: () => void;
  onTyping?: () => void;
}

export function TypewriterText({ text, speed = 12, animate = true, onComplete, onTyping }: TypewriterTextProps) {
  const [displayedLength, setDisplayedLength] = useState(animate ? 0 : text.length);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!animate) {
      setDisplayedLength(text.length);
      return;
    }

    setDisplayedLength(0);
    intervalRef.current = setInterval(() => {
      setDisplayedLength(prev => {
        const next = prev + 1;
        if (next >= text.length) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          onComplete?.();
          return text.length;
        }
        if (next % 3 === 0) {
            onTyping?.();
        }
        return next;
      });
    }, speed);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [text, speed, animate]);

  const visibleText = text.slice(0, displayedLength);
  const isTyping = displayedLength < text.length;

  return (
    <div className={`typewriter-container ${isTyping ? 'is-typing' : ''}`}>
      <ReactMarkdown>{visibleText}</ReactMarkdown>
      {isTyping && <span className="typewriter-cursor" />}
    </div>
  );
}
