import React, { useState } from 'react';
import { useIncident } from '../context/IncidentContext';
import { WorkflowsTab } from '../components/CommandCenter/WorkflowsTab';
import { IncidentDetailPanel } from '../components/CommandCenter/IncidentDetailPanel';
import { AgentStatusGrid } from '../components/CommandCenter/AgentStatusGrid';
import { MCPActivityFeed } from '../components/CommandCenter/MCPActivityFeed';
import { AWSInfrastructureState } from '../components/CommandCenter/AWSInfrastructureState';
import { RuntimeTerminal } from '../components/CommandCenter/RuntimeTerminal';
import { MemoryTab } from '../components/CommandCenter/MemoryTab';
import { 
  AlertTriangle, 
  Cpu, 
  Network, 
  Cloud, 
  GitMerge, 
  Activity, 
  Terminal,
  Database
} from 'lucide-react';
import { Navigation } from '../App';
import './CommandCenter.css';

export function CommandCenter() {
  const { systemStatus, incidents, activeIncidentId, setActiveIncident, aws, agents } = useIncident();
  const [activeTab, setActiveTab] = useState('incidents');

  const navItems = [
    { id: 'incidents', label: 'Incidents', icon: AlertTriangle },
    { id: 'agents', label: 'Agents', icon: Cpu },
    { id: 'mcp', label: 'MCP Activity', icon: Network },
    { id: 'aws', label: 'AWS Infrastructure', icon: Cloud },
    { id: 'workflows', label: 'Workflows', icon: GitMerge },
    { id: 'memory', label: 'Memory', icon: Database },
    { id: 'terminal', label: 'Runtime Console', icon: Terminal },
  ];

  return (
    <div className="cc-dashboard">
      
      {/* Top System Bar */}
      <div className="cc-top-bar">
        <div className="cc-brand">
          <div className="brand-logo-wrapper">
            <div className={`status-pulse-ring ${systemStatus.toLowerCase()}`} />
            <div className={`status-dot ${systemStatus.toLowerCase()}`} />
          </div>
          <span className="brand-text">MEDUSA <span className="brand-highlight">COMMAND CENTER</span></span>
        </div>
        
        <div className="cc-global-stats-inline">
          <div className="stat-inline">
            <AlertTriangle size={12} className="stat-icon incidents" />
            <span className="stat-label">ACTIVE INCIDENTS</span>
            <span className="stat-value highlight">{incidents.filter(i => i.status === 'ACTIVE').length.toString().padStart(2, '0')}</span>
          </div>
          <div className="stat-divider" />

          <div className="stat-inline">
            <Cpu size={12} className="stat-icon agents" />
            <span className="stat-label">AGENT FLEET</span>
            <span className="stat-value">{Object.values(agents).filter(a => a === 'ACTIVE' || a === 'EXECUTING' || a === 'DONE').length} <span className="stat-total">/ 8</span></span>
          </div>
          <div className="stat-divider" />

          <div className="stat-inline">
            <Network size={12} className="stat-icon mcp" />
            <span className="stat-label">MCP STATUS</span>
            <span className="stat-value success">CONNECTED</span>
          </div>
          <div className="stat-divider" />

          <div className="stat-inline">
            <Cloud size={12} className="stat-icon aws" />
            <span className="stat-label">AWS INFRASTRUCTURE</span>
            <span className="stat-value success">{aws.bedrock === 'ACTIVE' || aws.bedrock === 'RUNNING' ? 'HEALTHY' : aws.bedrock}</span>
          </div>
        </div>
      </div>

      <div className="cc-main-layout">
        
        {/* Left Navigation Rail */}
        <div className="cc-sidebar">
          <div className="cc-sidebar-nav">
            <Navigation />
          </div>

          <div className="sidebar-section">
            <h4 className="sidebar-section-title">SYSTEM</h4>
            {navItems.map(item => (
              <button
                key={item.id}
                className={`cc-nav-item ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => setActiveTab(item.id)}
              >
                <item.icon size={18} />
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Content Area */}
        <div className="cc-content-area">
          {activeTab === 'incidents' && (
            <div className="incidents-view full-width flex-col">
              {/* Sleek Incident Selector Dropdown */}
              <div className="incident-selector-bar glass-panel">
                <span className="selector-label">VIEWING INCIDENT:</span>
                <select 
                  className="incident-dropdown"
                  value={activeIncidentId || ''}
                  onChange={(e) => setActiveIncident(e.target.value)}
                >
                  <option value="" disabled>Select an incident...</option>
                  {incidents.map(inc => (
                    <option key={inc.id} value={inc.id}>
                      {inc.id} - {inc.title} ({inc.status})
                    </option>
                  ))}
                </select>
              </div>

              {activeIncidentId ? (
                <div className="active-incident-dashboard">
                  <IncidentDetailPanel />
                </div>
              ) : (
                <div className="empty-state">Select an incident to view details.</div>
              )}
            </div>
          )}

          {activeTab === 'workflows' && (
            <WorkflowsTab />
          )}

          {activeTab === 'agents' && (
            <div className="tab-content-wrapper">
              <AgentStatusGrid />
            </div>
          )}
          
          {activeTab === 'mcp' && (
            <div className="tab-content-wrapper glass-panel">
              <MCPActivityFeed />
            </div>
          )}

          {activeTab === 'memory' && (
            <div className="tab-content-wrapper glass-panel">
              <MemoryTab />
            </div>
          )}
          
          {activeTab === 'aws' && (
            <div className="tab-content-wrapper glass-panel">
              <AWSInfrastructureState />
            </div>
          )}

          {activeTab === 'terminal' && (
            <div className="tab-content-wrapper glass-panel">
              <RuntimeTerminal />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
