import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useIncident } from '../../context/IncidentContext';
import { Phone, Users, MapPin, Download, CheckCircle2, CircleDashed, AlertTriangle } from 'lucide-react';
import './ResponseWidgets.css';

export function EmergencyContactsWidget() {
  const { pipeline, incidents, activeIncidentId } = useIncident();
  const incident = incidents.find(i => i.id === activeIncidentId);
  const contacts = incident?.widgets?.contacts || {};

  return (
    <div className="idp-card glass-panel rw-card">
      <div className="card-header">
        <Users size={16} />
        <h3>EMERGENCY CONTACTS</h3>
      </div>
      <div className="card-content">
        {Object.entries(contacts).map(([id, contact]: [string, any]) => (
          <div className="rw-row" key={id}>
            <div className="rw-info">
              <span className="rw-title">{contact.type} - {contact.name}</span>
              <span className="rw-meta">
                {pipeline?.familyNotified ? <><CheckCircle2 size={12} className="icon-done" /> Notification SENT</> : <><CircleDashed size={12} /> PENDING</>}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function CareResourceWidget() {
  const { pipeline, incidents, activeIncidentId } = useIncident();
  const incident = incidents.find(i => i.id === activeIncidentId);
  const hospitals = incident?.widgets?.hospitals || [];

  return (
    <div className="idp-card glass-panel rw-card">
      <div className="card-header">
        <MapPin size={16} />
        <h3>CARE RESOURCE DISCOVERY</h3>
      </div>
      <div className="card-content">
        {!pipeline?.resourcesDiscovered || hospitals.length === 0 ? (
          <div className="rw-empty">Awaiting resource discovery...</div>
        ) : (
          <>
            {hospitals.map((hospital: any, idx: number) => (
              <div className={`rw-facility ${idx === 0 ? 'primary' : ''}`} key={idx}>
                <span className="rw-title">{hospital.name}</span>
                <span className="rw-meta">
                  Distance: {hospital.distance_km} km | Status: <span className="status-green">AVAILABLE</span>
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export function TransportWidget() {
  const { pipeline, incidents, activeIncidentId } = useIncident();
  const incident = incidents.find(i => i.id === activeIncidentId);
  const transport = incident?.widgets?.transport;
  const [showSimModal, setShowSimModal] = useState(false);

  return (
    <div className="idp-card glass-panel rw-card">
      <div className="card-header">
        <Phone size={16} />
        <h3>AMBULANCE REQUEST</h3>
      </div>
      <div className="card-content">
        {!pipeline?.transportRequested || !transport ? (
          <div className="rw-empty">Awaiting transport request...</div>
        ) : (
          <div className="transport-details">
            <div className="transport-badge requested">
              <span className="status-dot pulse"></span> {transport.status}
            </div>
            <div className="data-row">
              <span className="label">Reference</span>
              <span className="value mono">{transport.request_id}</span>
            </div>
            <div className="data-row">
              <span className="label">Destination</span>
              <span className="value text-wrap highlight">{transport.destination}</span>
            </div>
            <div className="data-row">
              <span className="label">ETA</span>
              <span className="value highlight" style={{ color: 'var(--accent-orange)' }}>{transport.eta_minutes} mins</span>
            </div>
            <button className="rw-btn outline w-full mt-4" onClick={() => setShowSimModal(true)}>VIEW LIVE TRACKING</button>
            
            {showSimModal && createPortal(
              <div className="sim-modal-overlay" onClick={() => setShowSimModal(false)}>
                <div className="sim-modal-content" onClick={e => e.stopPropagation()}>
                  <div className="sim-header">
                    <AlertTriangle size={24} className="sim-icon" />
                    <h4>SIMULATION MODE</h4>
                  </div>
                  <div className="sim-body">
                    <p>This is a simulated demonstration for the hackathon.</p>
                    <div className="sim-alert-box">
                      <strong>IN CASE OF REAL EMERGENCY</strong>
                      <div className="sim-numbers">Call <span>108</span> or <span>112</span></div>
                    </div>
                    <button className="rw-btn w-full mt-4" onClick={() => setShowSimModal(false)}>UNDERSTOOD</button>
                  </div>
                </div>
              </div>,
              document.body
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function HandoffSummaryWidget() {
  const { activeIncidentId, pipeline, incidents } = useIncident();
  const incident = incidents.find(i => i.id === activeIncidentId);
  const handoff = incident?.widgets?.handoff;
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!handoff) return;
    const text = `MEDUSA INCIDENT HANDOFF\n` +
      `ID: ${activeIncidentId}\n` +
      `Patient Profile: ${handoff.document?.patient?.name || 'Retrieved'}\n` +
      `Conditions: ${handoff.document?.medical_history?.known_conditions?.join(', ') || 'None'}\n` +
      `Triage: ${handoff.document?.incident_details?.triage_priority || 'Assigned'}\n`;
      
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportPDF = () => {
    if (!handoff) return;
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;
    
    printWindow.document.write(`
      <html>
        <head>
          <title>Medusa Incident Handoff - ${activeIncidentId}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; color: #1a1a1a; max-width: 800px; margin: 0 auto; }
            h1 { color: #ff3c00; border-bottom: 2px solid #eee; padding-bottom: 16px; margin-bottom: 8px; font-weight: 800; letter-spacing: -0.5px; }
            .meta { font-family: monospace; color: #666; margin-bottom: 40px; font-size: 14px; }
            .section { margin-bottom: 24px; background: #f9f9f9; padding: 16px; border-radius: 8px; border: 1px solid #eee; }
            .label { font-size: 12px; text-transform: uppercase; font-weight: 700; color: #888; margin-bottom: 6px; letter-spacing: 0.5px; }
            .value { font-size: 18px; font-weight: 500; }
            .footer { margin-top: 60px; font-size: 12px; color: #999; text-align: center; border-top: 1px dashed #ddd; padding-top: 20px; }
          </style>
        </head>
        <body>
          <h1>MEDUSA EMERGENCY HANDOFF</h1>
          <div class="meta">Incident ID: ${activeIncidentId} &bull; Generated: ${new Date().toLocaleString()}</div>
          
          <div class="section">
            <div class="label">Patient Profile</div>
            <div class="value">${handoff.document?.patient?.name || 'Retrieved'}</div>
          </div>
          
          <div class="section">
            <div class="label">Known Medical Conditions</div>
            <div class="value">${handoff.document?.medical_history?.known_conditions?.join(', ') || 'None'}</div>
          </div>
          
          <div class="section">
            <div class="label">Assigned Triage Priority</div>
            <div class="value" style="font-weight: 800; color: #ff3c00;">${handoff.document?.incident_details?.triage_priority || 'Assigned'}</div>
          </div>
          
          <div class="footer">
            Automated dispatch generation by MEDUSA AI Emergency Response System
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    
    // Slight delay to ensure styles are applied before print dialog opens
    setTimeout(() => {
      printWindow.print();
    }, 250);
  };

  return (
    <div className="idp-card glass-panel rw-card">
      <div className="card-header">
        <Download size={16} />
        <h3>INCIDENT HANDOFF</h3>
      </div>
      <div className="card-content">
        {!pipeline?.handoffGenerated || !handoff?.generated ? (
          <div className="rw-empty">Awaiting handoff generation...</div>
        ) : (
          <div className="handoff-content">
            <div className="handoff-doc">
              <div className="doc-id">{activeIncidentId}</div>
              <div>Patient Profile: {handoff.document?.patient?.name || 'Retrieved'}</div>
              <div>Conditions: {handoff.document?.medical_history?.known_conditions?.join(', ') || 'None'}</div>
              <div>Triage: {handoff.document?.incident_details?.triage_priority || 'Assigned'}</div>
            </div>
            <div className="rw-actions">
              <button className="rw-btn outline flex-1" onClick={handleCopy}>
                {copied ? 'COPIED!' : 'COPY'}
              </button>
              <button className="rw-btn flex-1" onClick={handleExportPDF}>EXPORT PDF</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
