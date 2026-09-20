import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

// --- Types ---
export type IncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'RESOLVED';
export type IncidentStatus = 'ACTIVE' | 'RESOLVED' | 'PENDING';
export type AgentStatus = 'INACTIVE' | 'ACTIVE' | 'EXECUTING' | 'DONE' | 'ERROR' | 'STANDBY';
export type AWSStatus = 'HEALTHY' | 'RUNNING' | 'SYNCED' | 'ACTIVE' | 'ERROR' | 'PENDING';

export interface Incident {
  id: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  title: string;
  timestamp: string;
  patient: {
    name: string;
    age: number;
    location: string;
    address: string;
    phone: string;
    relationship: string;
    emergencyContact: string;
  };
  situation: {
    reported: string;
    conscious: string;
    breathing: string;
    confidence: string;
  };
  pipeline?: {
    created: boolean;
    assessed: boolean;
    patientRetrieved: boolean;
    workflowStarted: boolean;
    familyNotified: boolean;
    resourcesDiscovered: boolean;
    transportRequested: boolean;
    handoffGenerated: boolean;
  };
  widgets?: {
    contacts: Record<string, any>;
    hospitals: any[];
    transport: any | null;
    handoff: {
      generated: boolean;
      document: any | null;
    };
  };
  agent_logs?: Record<string, string[]>;
}

export interface MCPCall {
  id: string;
  time: string;
  server: string;
  tool: string;
  status: 'EXECUTED' | 'PENDING' | 'ERROR';
  input: string;
  result: string;
}

export interface ToolEvent {
  id: string;
  name: string;
  status: 'running' | 'done';
  args?: any;
  result?: string;
}

export interface RuntimeLog {
  id: string;
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'EVENT' | 'MCP' | 'AWS' | 'AGENT';
  source: string;
  message: string;
}

export interface IncidentState {
  // Global State
  systemStatus: 'OPERATIONAL' | 'STANDBY';
  incidents: Incident[];
  activeIncidentId: string | null;
  
  // Active Incident Data
  agents: Record<string, AgentStatus>;
  aws: Record<string, AWSStatus>;
  mcpCalls: MCPCall[];
  runtimeLogs: RuntimeLog[];
  
  // Pipeline Progress
  pipeline: {
    created: boolean;
    assessed: boolean;
    patientRetrieved: boolean;
    workflowStarted: boolean;
    familyNotified: boolean;
    resourcesDiscovered: boolean;
    transportRequested: boolean;
    handoffGenerated: boolean;
  };

  // Tool Events for live activity panel
  toolEvents: ToolEvent[];

  // Actions
  setActiveIncident: (id: string) => void;
  triggerEmergency: (prompt?: string, history?: any[]) => Promise<string>;
  confirmEmergency: () => void;
  reset: () => void;
  addLog: (level: RuntimeLog['level'], source: string, message: string) => void;
  
  // Backwards Compatibility for VoiceConsole
  status: 'IDLE' | 'DETECTING' | 'CRITICAL' | 'HANDOFF' | 'RESOLVED';
  incidentId: string | null;
  patient: any; // For old code
  logs: any[]; // For old code
  notifyFamily: () => void;
  findResources: () => void;
  requestTransport: () => void;
  generateHandoff: () => void;
}

const IncidentContext = createContext<IncidentState | undefined>(undefined);

export const IncidentProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Global
  const [systemStatus, setSystemStatus] = useState<'OPERATIONAL' | 'STANDBY'>('STANDBY');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);
  
  // Active Data
  const [agents, setAgents] = useState<Record<string, AgentStatus>>({
    orchestrator: 'ACTIVE',
    situation: 'STANDBY',
    patient: 'STANDBY',
    response: 'STANDBY',
    communication: 'STANDBY',
    resource: 'STANDBY',
    transport: 'STANDBY',
    handoff: 'STANDBY'
  });
  
  const [aws, setAws] = useState<Record<string, AWSStatus>>({
    bedrock: 'HEALTHY',
    lambda: 'HEALTHY',
    apigateway: 'HEALTHY',
    dynamodb: 'HEALTHY',
    stepfunctions: 'PENDING',
    eventbridge: 'HEALTHY',
    s3: 'HEALTHY',
    cognito: 'HEALTHY'
  });

  const [mcpCalls, setMcpCalls] = useState<MCPCall[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [runtimeLogs, setRuntimeLogs] = useState<RuntimeLog[]>([]);
  
  const [pipeline, setPipeline] = useState({
    created: false,
    assessed: false,
    patientRetrieved: false,
    workflowStarted: false,
    familyNotified: false,
    resourcesDiscovered: false,
    transportRequested: false,
    handoffGenerated: false
  });

  // Legacy state
  const [legacyStatus, setLegacyStatus] = useState<'IDLE' | 'DETECTING' | 'CRITICAL' | 'HANDOFF' | 'RESOLVED'>('IDLE');
  
  // Session tracking for history
  const [sessionId, setSessionId] = useState<string>(Math.random().toString(36).substring(2, 15));

  const addLog = (level: RuntimeLog['level'], source: string, message: string) => {
    const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' }) + '.' + Math.floor(Math.random()*900+100);
    setRuntimeLogs(prev => [{ id: Math.random().toString(), time, level, source, message }, ...prev]);
  };

  useEffect(() => {
    const fetchHistoryLogs = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/history');
        if (res.ok) {
          const data = await res.json();
          const rawLogs: { date: Date, id: string, time: string, level: string, source: string, message: string }[] = [];
          
          if (data.incidents && Array.isArray(data.incidents)) {
            data.incidents.forEach((inc: any) => {
              if (inc.data && inc.data.agent_logs) {
                const incDate = new Date(inc.timestamp);
                Object.entries(inc.data.agent_logs).forEach(([agent, logs]) => {
                  (logs as string[]).forEach((logStr, index) => {
                    const match = logStr.match(/^\[(.*?)\] (.*)$/);
                    let timeStr = "";
                    let msg = logStr;
                    // Spread agent logs chronologically using index offset
                    let logDate = new Date(incDate.getTime() + index * 1000); 

                    if (match) {
                       timeStr = match[1];
                       msg = match[2];
                    } else {
                       timeStr = logDate.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
                    }

                    rawLogs.push({
                      date: logDate,
                      id: Math.random().toString(),
                      time: timeStr,
                      level: 'AGENT',
                      source: agent,
                      message: msg
                    });
                  });
                });
              }
            });
          }

          // Sort chronological (newest first, since addLog prepends)
          rawLogs.sort((a, b) => b.date.getTime() - a.date.getTime());
          
          const pastLogs: RuntimeLog[] = rawLogs.map(l => ({
            id: l.id,
            time: l.time,
            level: l.level as any,
            source: l.source,
            message: l.message
          }));
          
          setRuntimeLogs(prev => [...prev, ...pastLogs]);
        }
      } catch(err) {
        console.error("Failed to fetch historical logs:", err);
      }
    };
    fetchHistoryLogs();
  }, []);

  const addMCPCall = (tool: string, input: any, result: string) => {
    const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
    setMcpCalls(prev => [{
      id: Math.random().toString(), time, server: 'TRANSPORT', tool, status: 'EXECUTED', input: JSON.stringify(input, null, 2), result
    }, ...prev]);
  };

  const triggerEmergency = (prompt: string = "My father collapsed at home", history: any[] = []): Promise<string> => {
    return new Promise(async (resolve, reject) => {
      setSystemStatus('OPERATIONAL');
      setLegacyStatus('DETECTING');
      addLog('INFO', 'system', 'Processing request...');
      
      setPipeline(p => ({ ...p, created: true }));
      setAgents(a => ({ ...a, orchestrator: 'EXECUTING' }));

      let resolved = false;

      const parseSSELine = (line: string) => {
        // Strip "data: " prefix
        const trimmed = line.replace(/^data:\s*/, '').trim();
        if (!trimmed) return;
        
        try {
          const event = JSON.parse(trimmed);
          
          const getAgentForTool = (toolName: string) => {
            if (['resolve_kinship', 'get_patient_context'].includes(toolName)) return 'patient';
            if (['create_incident', 'assign_triage_priority', 'update_clinical_state'].includes(toolName)) return 'situation';
            if (['notify_emergency_contacts'].includes(toolName)) return 'communication';
            if (['search_care_resources'].includes(toolName)) return 'resource';
            if (['coordinate_transport', 'generate_handoff'].includes(toolName)) return 'transport';
            return 'response';
          };

          if (event.type === 'thought') {
            addLog('AGENT', 'orchestrator', event.content);
          } else if (event.type === 'tool_call') {
            const agentKey = getAgentForTool(event.tool);
            setAgents(a => ({ ...a, [agentKey]: 'EXECUTING' }));
            
            addMCPCall(event.tool, event.args, 'Pending...');
            addLog('MCP', 'tool', `Executing ${event.tool}...`);
            // Add to live tool events
            setToolEvents(prev => [...prev, { id: Math.random().toString(36).substr(2, 9), name: event.tool, status: 'running', args: event.args }]);
          } else if (event.type === 'tool_result') {
            setMcpCalls(prev => {
              const updated = [...prev];
              const callIndex = updated.findIndex(c => c.tool === event.tool && c.status === 'PENDING');
              if (callIndex !== -1) {
                updated[callIndex] = { ...updated[callIndex], status: 'EXECUTED', result: event.result };
              } else {
                addMCPCall(event.tool, {}, event.result);
              }
              return updated;
            });
            // Update tool event status to done
            setToolEvents(prev => {
              const updated = [...prev];
              const idx = updated.findIndex(t => t.name === event.tool && t.status === 'running');
              if (idx !== -1) {
                updated[idx] = { ...updated[idx], status: 'done', result: event.result };
              }
              return updated;
            });
            
            addLog('MCP', 'tool', `${event.tool} completed`);
            const agentKey = getAgentForTool(event.tool);
            setAgents(a => ({ ...a, [agentKey]: 'DONE' }));
            
            fetchLiveState();
          } else if (event.type === 'final') {
            setLegacyStatus('RESOLVED');
            setAgents(a => ({ ...a, orchestrator: 'DONE' }));
            // Keep toolEvents visible briefly, then clear
            setTimeout(() => setToolEvents([]), 3000);
            resolved = true;
            resolve(event.content || '');
          } else if (event.type === 'error') {
            addLog('ERROR', 'system', event.content);
            resolved = true;
            resolve(event.content || 'An error occurred.');
          }
        } catch (e) {
          console.warn("SSE parse skip:", trimmed);
        }
      };

      try {
        const response = await fetch('http://localhost:8000/api/trigger-emergency', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, history, session_id: sessionId }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        if (!response.body) throw new Error('No readable stream');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          // Split on \r\n\r\n OR \n\n to handle both Windows and Unix SSE framing
          const chunks = buffer.split(/\r?\n\r?\n/);
          buffer = chunks.pop() || '';

          for (const chunk of chunks) {
            // Each chunk may contain one or more "data: ..." lines
            const dataLines = chunk.split(/\r?\n/).filter(l => l.startsWith('data:'));
            for (const line of dataLines) {
              parseSSELine(line);
              if (resolved) return;
            }
          }
        }

        // Stream ended — try to parse anything left in the buffer
        if (!resolved && buffer.trim()) {
          const remaining = buffer.split(/\r?\n/).filter(l => l.startsWith('data:'));
          for (const line of remaining) {
            parseSSELine(line);
            if (resolved) return;
          }
        }

        // Safety: if stream ended and we never got a 'final' event, resolve anyway
        if (!resolved) {
          setLegacyStatus('IDLE');
          resolve('I processed your request but received no final response.');
        }

      } catch (err) {
        console.error(err);
        addLog('ERROR', 'system', 'Failed to connect to backend.');
        if (!resolved) reject(err);
      }
    });
  };

  const fetchLiveState = async () => {
    try {
      const incRes = await fetch('http://localhost:8000/api/incidents');
      if (incRes.ok) {
        const data = await incRes.json();
        const incidentList = (Array.isArray(data) ? data : Object.values(data)) as Incident[];
        if (incidentList.length > 0) {
          setIncidents(incidentList);
          if (!activeIncidentId) {
            setActiveIncidentId(incidentList[0].id);
          } else {
            // Check if active incident is still in list, if not, reset it
            const exists = incidentList.find(i => i.id === activeIncidentId);
            if (!exists) setActiveIncidentId(incidentList[0].id);
          }
          
          // Sync pipeline with the active incident's pipeline
          const activeInc = incidentList.find(i => i.id === activeIncidentId) || incidentList[0];
          if (activeInc && activeInc.pipeline) {
            setPipeline(activeInc.pipeline);
          }
        } else {
          setIncidents([]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchLiveState(); // Fetch immediately on mount
    const interval = setInterval(fetchLiveState, 2000); // And poll every 2s
    return () => clearInterval(interval);
  }, [activeIncidentId]); // Re-bind if active incident changes

  const confirmEmergency = () => {};
  const notifyFamily = () => {};
  const findResources = () => {};
  const requestTransport = () => {};
  const generateHandoff = () => {};

  const reset = () => {
    setLegacyStatus('IDLE');
    setSystemStatus('STANDBY');
    setIncidents([]);
    setActiveIncidentId(null);
    setMcpCalls([]);
    setRuntimeLogs([]);
    setPipeline({ created: false, assessed: false, patientRetrieved: false, workflowStarted: false, familyNotified: false, resourcesDiscovered: false, transportRequested: false, handoffGenerated: false });
    setAws(a => ({ ...a, stepfunctions: 'PENDING' }));
    setAgents({ orchestrator: 'ACTIVE', situation: 'STANDBY', patient: 'STANDBY', response: 'STANDBY', communication: 'STANDBY', resource: 'STANDBY', transport: 'STANDBY', handoff: 'STANDBY' });
    setSessionId(Math.random().toString(36).substring(2, 15));
  };

  return (
    <IncidentContext.Provider value={{
      systemStatus, incidents, activeIncidentId, agents, aws, mcpCalls, runtimeLogs, pipeline, toolEvents,
      setActiveIncident: setActiveIncidentId,
      triggerEmergency, confirmEmergency, reset, addLog,
      status: legacyStatus, incidentId: activeIncidentId, patient: null, logs: runtimeLogs as any,
      notifyFamily, findResources, requestTransport, generateHandoff
    }}>
      {children}
    </IncidentContext.Provider>
  );
};

export const useIncident = () => {
  const context = useContext(IncidentContext);
  if (context === undefined) {
    throw new Error('useIncident must be used within an IncidentProvider');
  }
  return context;
};
