import { useIncident } from '../../context/IncidentContext';
import { User, Activity, AlertCircle, MapPin, Phone, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { EmergencyContactsWidget, CareResourceWidget, TransportWidget, HandoffSummaryWidget } from './ResponseWidgets';
import './IncidentDetailPanel.css';

export function IncidentDetailPanel() {
  const { incidents, activeIncidentId, pipeline } = useIncident();
  
  const incident = incidents.find(i => i.id === activeIncidentId);
  if (!incident) return null;

  return (
    <div className="incident-detail-panel">
      {/* Header */}
      <div className="idp-header glass-panel">
        <div className="idp-header-main">
          <div className="idp-title-row">
            <h1>{incident.id}</h1>
            <span className={`idp-badge ${incident.severity?.toLowerCase() || 'unknown'}`}>
              {incident.severity === 'CRITICAL' && <ShieldAlert size={14} />}
              {incident.severity || 'UNKNOWN'}
            </span>
            <span className={`idp-badge status-${incident.status?.toLowerCase() || 'unknown'}`}>
              {incident.status || 'UNKNOWN'}
            </span>
          </div>
          <h2>{incident.title}</h2>
        </div>
        <div className="idp-header-meta">
          <div className="meta-item">
            <span className="label">Reported</span>
            <span className="value">{incident.timestamp}</span>
          </div>
        </div>
      </div>

      <div className="idp-grid top-grid">
        {/* Patient Profile */}
        <div className="idp-card glass-panel">
          <div className="card-header">
            <User size={16} />
            <h3>PATIENT / PERSON</h3>
          </div>
          <div className="card-content">
            <div className="data-row">
              <span className="label">Name</span>
              <span className="value highlight">{incident.patient.name}</span>
            </div>
            <div className="data-row">
              <span className="label">Age</span>
              <span className="value">{incident.patient.age}</span>
            </div>
            <div className="data-row">
              <span className="label">Location</span>
              <span className="value"><MapPin size={12} className="inline-icon" /> {incident.patient.location}</span>
            </div>
            <div className="data-row">
              <span className="label">Address</span>
              <span className="value blur-text">{incident.patient.address}</span>
            </div>
          </div>
        </div>

        {/* Situation */}
        <div className="idp-card glass-panel">
          <div className="card-header">
            <AlertCircle size={16} />
            <h3>CURRENT SITUATION</h3>
          </div>
          <div className="card-content">
            <div className="data-row">
              <span className="label">Reported Event</span>
              <span className="value text-wrap highlight">{incident.situation.reported}</span>
            </div>
            <div className="data-row">
              <span className="label">Conscious</span>
              {incident.situation.conscious === 'Unknown' ? (
                <span className="value pending-text">Pending Assessment</span>
              ) : (
                <span className="value">{incident.situation.conscious}</span>
              )}
            </div>
            <div className="data-row">
              <span className="label">Breathing</span>
              {incident.situation.breathing === 'Unknown' ? (
                <span className="value pending-text">Pending Assessment</span>
              ) : (
                <span className="value">{incident.situation.breathing}</span>
              )}
            </div>
            <div className="data-row">
              <span className="label">Severity Assessment</span>
              <span className={`value ${incident.severity?.toLowerCase() || 'unknown'}`}>{incident.severity || 'Unknown'}</span>
            </div>
          </div>
        </div>

        {/* Contact Info (Column 3) */}
        <div className="idp-card glass-panel">
          <div className="card-header">
            <Phone size={16} />
            <h3>EMERGENCY CONTACT</h3>
          </div>
          <div className="card-content">
            <div className="data-row">
              <span className="label">Primary Contact</span>
              <span className="value highlight">{incident.patient.emergencyContact}</span>
            </div>
            <div className="data-row">
              <span className="label">Relationship</span>
              <span className="value">{incident.patient.relationship}</span>
            </div>
            <div className="data-row">
              <span className="label">Phone Number</span>
              <span className="value"><Phone size={12} className="inline-icon" /> {incident.patient.phone}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Critical Alert Banner */}
      <div className="critical-alert-banner">
        <ShieldAlert size={18} />
        <div className="banner-text">
          <span className="banner-title">CRITICAL ADVISORY</span>
          <span className="banner-desc">Immediate medical evaluation required. Do not attempt diagnosis.</span>
        </div>
      </div>

      {/* Response Pipeline */}
      <div className="idp-card glass-panel full-width">
        <div className="card-header">
          <Activity size={16} />
          <h3>RESPONSE PROGRESS</h3>
        </div>
        <div className="pipeline-track">
          <PipelineStep label="Incident Created" active={pipeline?.created || false} />
          <PipelineStep label="Situation Assessed" active={pipeline?.assessed || false} />
          <PipelineStep label="Patient Context" active={pipeline?.patientRetrieved || false} />
          <PipelineStep label="Workflow Started" active={pipeline?.workflowStarted || false} />
          <PipelineStep label="Family Notified" active={pipeline?.familyNotified || false} />
          <PipelineStep label="Resource Discovery" active={pipeline?.resourcesDiscovered || false} />
          <PipelineStep label="Transport Request" active={pipeline?.transportRequested || false} />
          <PipelineStep label="Handoff Generation" active={pipeline?.handoffGenerated || false} />
        </div>
      </div>

      {/* Response Outputs */}
      <div className="idp-grid">
        <EmergencyContactsWidget />
        <CareResourceWidget />
        <TransportWidget />
        <HandoffSummaryWidget />
      </div>
    </div>
  );
}

function PipelineStep({ label, active }: { label: string, active: boolean }) {
  return (
    <div className={`pipeline-step ${active ? 'active' : ''}`}>
      <div className="step-icon">
        {active ? <CheckCircle2 size={16} /> : <div className="dot-empty" />}
      </div>
      <div className="step-label">{label}</div>
    </div>
  );
}
