import React, { useState, useEffect, useRef } from 'react';
import { useIncident } from '../../context/IncidentContext';
import { Cpu, CheckCircle2, PlayCircle, Clock, AlertCircle, Terminal as TerminalIcon, Database, Activity, Radio } from 'lucide-react';
import './EngineRoom.css'; // Shared CSS for the lower panels
import './AgentWorkspace.css';

// Generic logs for others
const GENERIC_LOGS = [
  "> Initializing agent processes...",
  "> Establishing secure MCP handshake...",
  "> Awaiting task assignments...",
  "> Polling memory grid for updates..."
];

export function AgentStatusGrid() {
  const { agents, incidents, activeIncidentId } = useIncident();
  const [selectedAgent, setSelectedAgent] = useState<string>('situation');
  
  const incident = incidents.find(i => i.id === activeIncidentId);
  const isActive = incident?.status === 'ACTIVE';
  
  // Real terminal logs from backend
  const targetLogs = incident?.agent_logs?.[selectedAgent];
  const logs = (targetLogs && targetLogs.length > 0) ? targetLogs : GENERIC_LOGS;
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto scroll when logs update
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ACTIVE':
      case 'EXECUTING': return <PlayCircle size={14} className="icon-executing" />;
      case 'DONE': return <CheckCircle2 size={14} className="icon-done" />;
      case 'ERROR': return <AlertCircle size={14} className="icon-error" />;
      default: return <Clock size={14} className="icon-standby" />;
    }
  };

  const renderAgent = (name: string, key: keyof typeof agents) => {
    const status = agents[key];
    const isSelected = selectedAgent === key;
    
    return (
      <div 
        className={`agent-row ${status.toLowerCase()} ${isSelected ? 'selected' : ''}`}
        onClick={() => setSelectedAgent(key)}
      >
        <div className="agent-name">
          <Cpu size={14} />
          {name}
        </div>
        <div className="agent-status-badge">
          {getStatusIcon(status)}
          <span>{status}</span>
        </div>
      </div>
    );
  };

  const activeCount = Object.values(agents).filter(a => a === 'EXECUTING' || a === 'ACTIVE').length;

  return (
    <div className="agent-workspace">
      
      {/* Left Panel: The Roster */}
      <div className="aw-roster glass-panel">
        <div className="engine-header">
          <h3>AGENT ROSTER</h3>
          <span className="count">{activeCount} ACTIVE</span>
        </div>
        <div className="engine-content" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div className="agent-list">
            {renderAgent('Situation Agent', 'situation')}
            {renderAgent('Patient Agent', 'patient')}
            {renderAgent('Response Agent', 'response')}
            {renderAgent('Communication Agent', 'communication')}
            {renderAgent('Resource Agent', 'resource')}
            {renderAgent('Transport Agent', 'transport')}
          </div>
          
          <div className={`active-mission-brief ${isActive ? 'live-emergency' : 'still'}`}>
             <div className="mission-header">
                <Radio size={12} /> {isActive ? 'ACTIVE DIRECTIVE' : 'STANDBY MODE'}
             </div>
             <div className="mission-content">
                <div className="mission-title">{isActive ? 'INCIDENT RESPONSE' : 'MONITORING'}</div>
                {incident && <div className="mission-id">ID: {incident.id}</div>}
                <div className="mission-desc">
                  {isActive 
                    ? `Actively coordinating response for ${incident?.title}. Awaiting agent execution logs.`
                    : 'Continuous monitoring of patient vitals and environment telemetry. Awaiting anomaly detection.'}
                </div>
                
                <div className="mission-status-graph">
                   {[...Array(16)].map((_, i) => (
                     <div 
                        key={i} 
                        className="graph-bar" 
                        style={{
                           height: `${20 + Math.random() * 80}%`, 
                           animationDelay: `${i * 0.1}s`
                        }}
                     ></div>
                   ))}
                </div>
             </div>
          </div>
        </div>
      </div>

      {/* Right Panel: The Inspector */}
      <div className="aw-inspector">
        
        {/* Telemetry Bar */}
        <div className="aw-telemetry">
          <div className="telemetry-badge">
            <Cpu size={12} />
            <span>Model: Claude 3.5 Sonnet</span>
          </div>
          <div className="telemetry-badge">
            <Activity size={12} />
            <span>Latency: 240ms</span>
          </div>
          <div className="telemetry-badge">
            <Database size={12} />
            <span>Tokens: 1,420</span>
          </div>
        </div>

        {/* Live Terminal */}
        <div className="aw-terminal glass-panel">
          <div className="engine-header">
            <h3><TerminalIcon size={12} style={{marginRight: '6px'}}/> LIVE TERMINAL ({selectedAgent.toUpperCase()})</h3>
          </div>
          <div className="terminal-screen">
            {logs.map((log: string, idx: number) => {
              if (!log) return null; // Safe check for undefined logs
              // Parse log to highlight keywords
              const parts = log.split(/(\[.*?\]|CRITICAL:|Action:|Outcome:|>)/g);
              return (
                <div key={idx} className="term-line">
                  <span className="term-content">
                    {parts.map((part: string, i: number) => {
                      if (!part) return null; // Safe check for empty strings or undefined
                      if (part === 'CRITICAL:') return <span key={i} style={{color: 'var(--accent-orange)', textShadow: '0 0 8px rgba(255, 94, 0, 0.8)', fontWeight: 700}}>{part}</span>;
                      if (part === 'Action:' || part === 'Outcome:') return <span key={i} style={{color: '#fff', textShadow: '0 0 4px rgba(255, 255, 255, 0.4)'}}>{part}</span>;
                      if (part.startsWith('[') && part.endsWith(']')) return <span key={i} style={{color: 'rgba(255, 255, 255, 0.7)'}}>{part}</span>;
                      if (part === '>') return <span key={i} style={{color: 'var(--accent-orange)'}}>{part}</span>;
                      return <span key={i}>{part}</span>;
                    })}
                  </span>
                </div>
              );
            })}
            {isActive && (
              <div className="term-cursor">_</div>
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>

        {/* Memory Context */}
        <div className="aw-memory glass-panel">
          <div className="engine-header">
            <h3><Database size={12} style={{marginRight: '6px'}}/> SHORT-TERM MEMORY</h3>
          </div>
          <div className="memory-content">
            <pre className="json-viewer">
{JSON.stringify(
  incident ? {
    incident_id: incident.id,
    status: incident.status,
    patient_context: incident.patient,
    situation_assessment: incident.situation,
    pipeline_state: incident.pipeline,
    active_agent: selectedAgent
  } : {
    system_state: "AWAITING_INCIDENT",
    active_agent: selectedAgent,
    listening: true
  }
, null, 2)}
            </pre>
          </div>
        </div>

      </div>
    </div>
  );
}
