import React, { useEffect, useRef } from 'react';
import { useIncident } from '../../context/IncidentContext';
import { Terminal } from 'lucide-react';
import './EngineRoom.css';

export function RuntimeTerminal() {
  const { runtimeLogs } = useIncident();
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [runtimeLogs]);

  // Reverse so newest is at the bottom visually
  const logsToRender = [...runtimeLogs].reverse();

  return (
    <div className="engine-card glass-panel terminal-card">
      <div className="engine-header terminal-header">
        <Terminal size={14} />
        <h3>MEDUSA RUNTIME CONSOLE</h3>
      </div>
      <div className="engine-content p-0">
        <div className="terminal-feed" ref={terminalRef}>
          {logsToRender.length === 0 ? (
            <div className="terminal-line placeholder">&gt; System ready. Waiting for input...</div>
          ) : (
            logsToRender.map(log => (
              <div key={log.id} className={`terminal-line ${log.level.toLowerCase()}`}>
                <span className="term-time">{log.time}</span>
                <span className={`term-level ${log.level.toLowerCase()}`}>{log.level.padEnd(5)}</span>
                <span className="term-source">[{log.source}]</span>
                <span className="term-msg">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
