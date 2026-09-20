import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Cpu, Clock, CheckCircle2, Loader2, Database, Network } from 'lucide-react';
import './WorkflowsGraph.css';

export function CustomAgentNode({ data }: any) {
  const { label, type, status, activeTool } = data;

  const renderIcon = () => {
    if (type === 'orchestrator') return <Network size={16} />;
    if (type === 'aws') return <Database size={16} />;
    return <Cpu size={16} />;
  };

  const renderStatus = () => {
    if (status === 'ACTIVE' || status === 'EXECUTING') {
      return (
        <div className="agent-node-status executing">
          <Loader2 size={12} className="spinning" />
          <span>{status}</span>
        </div>
      );
    }
    if (status === 'DONE') {
      return (
        <div className="agent-node-status done">
          <CheckCircle2 size={12} />
          <span>DONE</span>
        </div>
      );
    }
    return (
      <div className="agent-node-status standby">
        <Clock size={12} />
        <span>STANDBY</span>
      </div>
    );
  };

  return (
    <div className={`custom-agent-node ${status?.toLowerCase() || 'standby'} ${type}`}>
      <Handle type="target" position={Position.Top} className="node-handle" />
      
      <div className="agent-node-header">
        <div className="agent-node-icon">
          {renderIcon()}
        </div>
        <div className="agent-node-label">{label}</div>
      </div>
      
      {type !== 'aws' && (
        <div className="agent-node-body">
          {renderStatus()}
          {activeTool && (
            <div className="agent-node-tool">
              <span className="tool-label">Running:</span>
              <span className="tool-name">{activeTool}</span>
            </div>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="node-handle" />
    </div>
  );
}
