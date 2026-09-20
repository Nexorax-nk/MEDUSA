import React, { useState, useEffect } from 'react';
import { useIncident } from '../../context/IncidentContext';
import { Network, CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react';
import './MCPActivity.css';

type ToolCall = {
  id: string;
  time: string;
  status: 'success' | 'running' | 'failed' | 'queued';
  tool: string;
  incidentId: string;
  agent: string;
  latency: string;
};

export function MCPActivityFeed() {
  const { mcpCalls, activeIncidentId } = useIncident();
  const [registry, setRegistry] = useState<Record<string, {name: string, desc: string}[]>>({});
  const [totalCalls, setTotalCalls] = useState(0);

  useEffect(() => {
    // Fetch live registry from the backend
    fetch('http://localhost:8000/api/mcp/tools')
      .then(res => res.json())
      .then(data => setRegistry(data))
      .catch(err => console.error("Failed to fetch tool registry:", err));
  }, []);

  useEffect(() => {
    // Keep total calls counter in sync with our mcpCalls
    setTotalCalls(prev => prev < mcpCalls.length ? mcpCalls.length : prev);
  }, [mcpCalls]);

  const renderStatusIcon = (status: 'success' | 'running' | 'failed' | 'queued' | 'EXECUTED' | 'PENDING' | 'ERROR') => {
    switch (status) {
      case 'success':
      case 'EXECUTED': return <div className="status-icon success"><CheckCircle2 /></div>;
      case 'running':
      case 'PENDING': return <div className="status-icon running"><Loader2 className="spinning" /></div>;
      case 'failed':
      case 'ERROR': return <div className="status-icon failed"><XCircle /></div>;
      case 'queued': return <div className="status-icon queued"><Clock /></div>;
      default: return null;
    }
  };

  return (
    <div className="mcp-dashboard">
      
      {/* Horizontal Health Strip */}
      <div className="mcp-health-strip">
        <div className="mcp-brand">
          <Network size={16} /> MCP SERVER
        </div>
        <div className="mcp-status-pill">
          <div className="dot pulsing" /> CONNECTED
        </div>
        
        <div className="mcp-health-divider" />
        
        <div className="mcp-health-metrics">
          <div className="mcp-health-stat">
            <span className="label">Transport</span>
            <span className="value">Streamable HTTP</span>
          </div>
          <div className="mcp-health-stat">
            <span className="label">Authentication</span>
            <span className="value active">✓ Active</span>
          </div>
          <div className="mcp-health-stat">
            <span className="label">Active Connections</span>
            <span className="value">03</span>
          </div>
          <div className="mcp-health-stat">
            <span className="label">Requests / min</span>
            <span className="value">24</span>
          </div>
          <div className="mcp-health-stat">
            <span className="label">Avg Latency</span>
            <span className="value">184 ms</span>
          </div>
          <div className="mcp-health-stat">
            <span className="label">Total Calls</span>
            <span className="value active">{totalCalls.toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div className="mcp-content-split">
        
        {/* Left: Live Feed */}
        <div className="mcp-live-panel">
          <div className="mcp-section-header">
            LIVE MCP TOOL CALLS
          </div>
          <div className="mcp-live-list">
            {mcpCalls.length === 0 && (
              <div style={{ padding: '20px', color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--mono)', fontSize: '12px', textAlign: 'center' }}>
                No active MCP tool calls detected in the current session.
              </div>
            )}
            {mcpCalls.map((call) => {
              if (!call) return null;
              return (
                <div key={call.id} className="mcp-live-row">
                  <span className="time">[{call.time}]</span>
                  {renderStatusIcon(call.status)}
                  <span className="tool">{call.tool}()</span>
                  <span className="incident">{activeIncidentId || 'N/A'}</span>
                  <span className="latency">{call.status === 'PENDING' ? '--' : '230 ms'}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Tool Registry Grid */}
        <div className="mcp-panel">
          <div className="mcp-section-header">
            TOOL REGISTRY
          </div>
          <div className="mcp-registry-scroll">
            <div className="mcp-registry-grid">
              {Object.entries(registry).length === 0 && (
                <div style={{ padding: '20px', color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--mono)', fontSize: '12px' }}>
                  Loading Tool Registry...
                </div>
              )}
              {Object.entries(registry).map(([category, tools]) => (
                <div key={category} className="mcp-category">
                  <span className="mcp-category-title">{category}</span>
                  {tools.map(tool => (
                    <div key={tool.name} className="mcp-registry-item">
                      <span className="tool-name">{tool.name}</span>
                      <span className="tool-desc">{tool.desc}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}