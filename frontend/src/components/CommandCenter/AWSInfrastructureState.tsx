import React, { useState, useEffect, useRef } from 'react';
import { useIncident } from '../../context/IncidentContext';
import { Cloud, Server, Database, Zap, Repeat, Box, Lock, Network, Activity, Shield } from 'lucide-react';
import './EngineRoom.css';
import './AWSActivity.css';

const XRAY_TRACES = [
  { id: '1-60a6a000-11112222', time: '10:17:42.100', service: 'API Gateway', message: 'POST /v1/ingest/telemetry -> 200 OK' },
  { id: '1-60a6a000-11112222', time: '10:17:42.125', service: 'Lambda', message: 'InvokeFunction: medusa-ingest-handler (Duration: 42ms)' },
  { id: '1-60a6a000-11112223', time: '10:17:42.167', service: 'DynamoDB', message: 'PutItem: IncidentStateDB -> ConsumedCapacity: 1.5 WCU' },
  { id: '1-60a6a000-11112224', time: '10:17:42.204', service: 'EventBridge', message: 'PutEvents: medusa-event-bus -> matched_rule: trigger-workflow' },
  { id: '1-60a6a000-11112225', time: '10:17:42.310', service: 'Step Functions', message: 'StartExecution: arn:aws:states:ap-south-1:123456789012:stateMachine:MedusaOrchestrator' },
  { id: '1-60a6a000-11112226', time: '10:17:42.502', service: 'Bedrock', message: 'InvokeModel API -> anthropic.claude-3-sonnet-20240229-v1:0 (Input: 412 tokens)' },
  { id: '1-60a6a000-11112226', time: '10:17:42.744', service: 'Bedrock', message: 'InvokeModel API Response -> 200 OK (Output: 184 tokens, Latency: 242ms)' },
  { id: '1-60a6a000-11112227', time: '10:17:42.855', service: 'Lambda', message: 'InvokeFunction: medusa-notification-dispatcher' },
  { id: '1-60a6a000-11112228', time: '10:17:42.910', service: 'Cognito', message: 'AdminInitiateAuth -> SUCCESS (Client: MobileResponder)' },
];

const SERVICE_META: Record<string, any> = {
  'bedrock': { arn: 'arn:aws:bedrock:ap-south-1:123456789012:provisioned-model/medusa', role: 'arn:aws:iam::123456789012:role/MedusaAIExecution', region: 'ap-south-1' },
  'lambda': { arn: 'arn:aws:lambda:ap-south-1:123456789012:function:medusa-orchestrator', role: 'arn:aws:iam::123456789012:role/MedusaLambdaBasic', region: 'ap-south-1' },
  'apigateway': { arn: 'arn:aws:apigateway:ap-south-1::/restapis/abc123def4', role: 'arn:aws:iam::123456789012:role/MedusaAPIGatewayRole', region: 'ap-south-1' },
  'dynamodb': { arn: 'arn:aws:dynamodb:ap-south-1:123456789012:table/IncidentStateDB', role: 'arn:aws:iam::123456789012:role/MedusaDDBAccess', region: 'ap-south-1' },
  'stepfunctions': { arn: 'arn:aws:states:ap-south-1:123456789012:stateMachine:MedusaWorkflow', role: 'arn:aws:iam::123456789012:role/MedusaStepFuncRole', region: 'ap-south-1' },
  'eventbridge': { arn: 'arn:aws:events:ap-south-1:123456789012:event-bus/medusa-bus', role: 'arn:aws:iam::123456789012:role/MedusaEventBridgeRole', region: 'ap-south-1' },
  's3': { arn: 'arn:aws:s3:::medusa-handoff-artifacts-ap-south-1', role: 'arn:aws:iam::123456789012:role/MedusaS3Access', region: 'ap-south-1' },
  'cognito': { arn: 'arn:aws:cognito-idp:ap-south-1:123456789012:userpool/ap-south-1_aBcD1eF2G', role: 'arn:aws:iam::123456789012:role/MedusaAuthRole', region: 'ap-south-1' },
};

export function AWSInfrastructureState() {
  const { aws } = useIncident();
  const [selectedService, setSelectedService] = useState<string>('bedrock');
  const [traces, setTraces] = useState<typeof XRAY_TRACES>([]);
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTraces([]);
    let currentIndex = 0;
    
    const interval = setInterval(() => {
      if (currentIndex < XRAY_TRACES.length) {
        setTraces(prev => [...prev, XRAY_TRACES[currentIndex]]);
        currentIndex++;
        if (terminalRef.current) {
          terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
      } else {
        clearInterval(interval);
      }
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  const renderAWSNode = (name: string, key: keyof typeof aws, icon: React.ReactNode, subtitle: string) => {
    const status = aws[key] || 'PENDING';
    const isSelected = selectedService === key;
    return (
      <div 
        key={key}
        className={`aws-service-node selectable ${status.toLowerCase()} ${isSelected ? 'selected' : ''}`}
        onClick={() => setSelectedService(key)}
      >
        <div className="aws-icon">{icon}</div>
        <div className="aws-details">
          <span className="aws-name">{name}</span>
          <span className="aws-subtitle">{subtitle}</span>
        </div>
        <div className="aws-status">● {status}</div>
      </div>
    );
  };

  const meta = SERVICE_META[selectedService] || SERVICE_META['bedrock'];

  return (
    <div className="aws-dashboard-wrapper">
      <div className="engine-card glass-panel full-width" style={{ flex: 'none' }}>
        <div className="engine-header">
          <h3>AWS INFRASTRUCTURE</h3>
          <span className="count">ALL SYSTEMS NOMINAL</span>
        </div>
        <div className="engine-content aws-grid">
          {renderAWSNode('Amazon Bedrock', 'bedrock', <Box size={16} />, 'Agent reasoning')}
          {renderAWSNode('AWS Lambda', 'lambda', <Server size={16} />, 'Tool execution')}
          {renderAWSNode('API Gateway', 'apigateway', <Network size={16} />, 'MCP/API ingress')}
          {renderAWSNode('DynamoDB', 'dynamodb', <Database size={16} />, 'Incident state')}
          {renderAWSNode('Step Functions', 'stepfunctions', <Repeat size={16} />, 'Emergency workflow')}
          {renderAWSNode('EventBridge', 'eventbridge', <Zap size={16} />, 'Event routing')}
          {renderAWSNode('Amazon S3', 's3', <Cloud size={16} />, 'Handoff artifacts')}
          {renderAWSNode('Cognito', 'cognito', <Lock size={16} />, 'Authentication')}
        </div>
      </div>

      <div className="aws-ops-panel">
        
        {/* Left: Metadata & CloudWatch */}
        <div className="aws-meta-section">
          <div className="aws-meta-card">
            <div className="aws-meta-header">
              <Shield size={14} /> Service Identity & Access
            </div>
            <div className="aws-meta-grid">
              <div className="aws-meta-row">
                <span className="aws-meta-label">Resource ARN</span>
                <span className="aws-meta-value accent" title={meta.arn}>{meta.arn}</span>
              </div>
              <div className="aws-meta-row">
                <span className="aws-meta-label">Execution Role (IAM)</span>
                <span className="aws-meta-value" title={meta.role}>{meta.role}</span>
              </div>
              <div className="aws-meta-row">
                <span className="aws-meta-label">Region</span>
                <span className="aws-meta-value" title={meta.region}>{meta.region}</span>
              </div>
            </div>
          </div>

          <div className="aws-meta-card">
            <div className="aws-meta-header">
              <Activity size={14} /> CloudWatch Live Telemetry
            </div>
            <div className="cw-grid">
              <div className="cw-metric-card">
                <span className="cw-metric-label">Latency (ms)</span>
                <span className="cw-metric-value">{Math.floor(Math.random() * 40) + 200}</span>
                <div className="cw-chart-sparkline" />
              </div>
              <div className="cw-metric-card">
                <span className="cw-metric-label">Invocations / sec</span>
                <span className="cw-metric-value">{Math.floor(Math.random() * 15) + 120}</span>
                <div className="cw-chart-sparkline" />
              </div>
              <div className="cw-metric-card">
                <span className="cw-metric-label">Error Rate</span>
                <span className="cw-metric-value" style={{ color: '#00ff64' }}>0.00%</span>
                <div className="cw-chart-sparkline" />
              </div>
              <div className="cw-metric-card">
                <span className="cw-metric-label">Active Connections</span>
                <span className="cw-metric-value" style={{ color: 'var(--accent-orange)' }}>8</span>
                <div className="cw-chart-sparkline" style={{ background: 'linear-gradient(180deg, transparent 0%, rgba(255, 94, 0, 0.1) 100%)', borderTop: '1px dashed rgba(255, 94, 0, 0.3)' }}/>
              </div>
            </div>
          </div>
        </div>

        {/* Right: X-Ray Stream */}
        <div className="xray-panel">
          <div className="xray-header">
            <span className="xray-title"><Zap size={14} style={{ color: '#00e5ff' }}/> AWS X-Ray Trace Stream</span>
            <span className="xray-badge">LIVE TRACING</span>
          </div>
          <div className="xray-terminal" ref={terminalRef}>
            {traces.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'var(--mono)', fontSize: '11px', textAlign: 'center', marginTop: '40px' }}>
                Awaiting backend trace signals...
              </div>
            ) : (
              traces.map((trace, i) => {
                if (!trace) return null;
                return (
                  <div key={i} className="xray-log-line">
                    <span className="xray-time">[{trace.time}]</span>
                    <span className="xray-id">{trace.id}</span>
                    <span className="xray-service">[{trace.service}]</span>
                    <span className="xray-message">{trace.message}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}