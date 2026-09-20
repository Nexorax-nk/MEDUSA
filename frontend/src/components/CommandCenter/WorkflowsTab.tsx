import React, { useEffect, useCallback } from 'react';
import { useIncident } from '../../context/IncidentContext';
import { ReactFlow, Background, useNodesState, useEdgesState } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import { CustomAgentNode } from './CustomAgentNode';
import '@xyflow/react/dist/style.css';
import './WorkflowsGraph.css';

const nodeTypes = {
  custom: CustomAgentNode
};

const initialNodes: Node[] = [
  { id: 'medusa', position: { x: 320, y: 0 }, data: { label: 'MEDUSA Orchestrator', type: 'orchestrator', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'situation', position: { x: 0, y: 160 }, data: { label: 'Situation Agent', type: 'agent', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'patient', position: { x: 320, y: 160 }, data: { label: 'Patient Agent', type: 'agent', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'response', position: { x: 640, y: 160 }, data: { label: 'Response Agent', type: 'agent', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'communication', position: { x: 0, y: 320 }, data: { label: 'Communication Agent', type: 'agent', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'resource', position: { x: 320, y: 320 }, data: { label: 'Resource Agent', type: 'agent', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'transport', position: { x: 640, y: 320 }, data: { label: 'Transport Agent', type: 'agent', status: 'STANDBY', activeTool: null }, type: 'custom' },
  { id: 'aws', position: { x: 320, y: 480 }, data: { label: 'AWS Infrastructure', type: 'aws', status: 'ACTIVE' }, type: 'custom' },
];

const initialEdges: Edge[] = [
  { id: 'e1', source: 'medusa', target: 'situation' },
  { id: 'e2', source: 'medusa', target: 'patient' },
  { id: 'e3', source: 'medusa', target: 'response' },
  { id: 'e4', source: 'medusa', target: 'communication' },
  { id: 'e5', source: 'medusa', target: 'resource' },
  { id: 'e6', source: 'medusa', target: 'transport' },
  { id: 'e7', source: 'communication', target: 'aws', style: { strokeDasharray: '5 5' } },
  { id: 'e8', source: 'resource', target: 'aws', style: { strokeDasharray: '5 5' } },
  { id: 'e9', source: 'transport', target: 'aws', style: { strokeDasharray: '5 5' } },
];

export function WorkflowsTab() {
  const { agents, mcpCalls } = useIncident();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const getActiveTool = useCallback((agentType: string) => {
    // Map agents to tools by reversing the logic in IncidentContext
    const toolToAgentMap: Record<string, string> = {
      'resolve_kinship': 'patient', 'get_patient_context': 'patient',
      'create_incident': 'situation', 'assign_triage_priority': 'situation', 'update_clinical_state': 'situation',
      'notify_emergency_contacts': 'communication',
      'search_care_resources': 'resource',
      'coordinate_transport': 'transport', 'generate_handoff': 'transport'
    };
    
    // Find the most recent active call for this agent
    const call = [...mcpCalls].reverse().find(c => {
      const agent = toolToAgentMap[c.tool] || 'response';
      return agent === agentType && c.status === 'PENDING';
    });
    
    return call ? `${call.tool}()` : null;
  }, [mcpCalls]);

  useEffect(() => {
    const isOrchestratorActive = Object.values(agents).some(s => s === 'EXECUTING');

    setNodes((nds) => 
      nds.map((node) => {
        if (node.id === 'medusa') {
          return { ...node, data: { ...node.data, status: isOrchestratorActive ? 'EXECUTING' : (agents.orchestrator || 'STANDBY'), activeTool: isOrchestratorActive ? 'Orchestrating...' : null } };
        } else if (node.id === 'aws') {
          return node;
        } else {
          return { ...node, data: { ...node.data, status: agents[node.id] || 'STANDBY', activeTool: getActiveTool(node.id) } };
        }
      })
    );

    setEdges((eds) => 
      eds.map((edge) => {
        if (edge.source === 'medusa') {
          return { ...edge, className: agents[edge.target] === 'EXECUTING' ? 'animated' : (agents[edge.target] === 'DONE' ? 'done-edge' : '') };
        } else if (edge.target === 'aws') {
          return { ...edge, className: agents[edge.source] === 'DONE' ? 'animated' : edge.className };
        }
        return edge;
      })
    );
  }, [agents, getActiveTool, setNodes, setEdges]);

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h3 className="panel-title" style={{ padding: '24px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>LIVE ORCHESTRATION GRAPH</h3>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReactFlow 
          nodes={nodes} 
          edges={edges} 
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView 
          fitViewOptions={{ padding: 0.1 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#333" gap={16} />
        </ReactFlow>
      </div>
    </div>
  );
}
