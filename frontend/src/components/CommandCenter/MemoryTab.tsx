import React, { useState, useEffect } from 'react';
import './MemoryTab.css';

export function MemoryTab() {
  const [activeSector, setActiveSector] = useState('PROFILE');
  const [memoryData, setMemoryData] = useState<any>(null);

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const [userRes, patientRes, incRes] = await Promise.all([
          fetch('https://medusa-v8l9.onrender.com/api/memory/user'),
          fetch('https://medusa-v8l9.onrender.com/api/memory/patient?patient_id=father'),
          fetch('https://medusa-v8l9.onrender.com/api/incidents')
        ]);
        
        const userData = await userRes.json();
        const patientData = await patientRes.json();
        const incData = await incRes.json();
        
        setMemoryData({ user: userData, patient: patientData, incidents: incData });
      } catch (err) {
        console.error("Failed to fetch memory", err);
      }
    };
    
    fetchMemory();
    const interval = setInterval(fetchMemory, 5000);
    return () => clearInterval(interval);
  }, []);

  const sectors = [
    { id: 'PROFILE', label: '01 / PRIMARY_PROFILE' },
    { id: 'EMERGENCY', label: '02 / EMERGENCY_PROTOCOL' },
    { id: 'KINSHIP', label: '03 / KINSHIP_MATRIX' },
    { id: 'MEDICAL', label: '04 / MEDICAL_CONTEXT' },
    { id: 'PREFERENCES', label: '05 / CORE_PREFERENCES' },
    { id: 'INCIDENTS', label: '06 / INCIDENT_MEMORY' },
    { id: 'CARE', label: '07 / CARE_NETWORK' },
  ];

  return (
    <div className="memory-dashboard">
      
      {/* Top Header Breadcrumb */}
      <div className="memory-core-header">
        <div className="core-title">
          / MEMORY BANK / <span>ENTITY_NAVEEN</span> / {activeSector}
        </div>
        <div className="core-meta">
          <span>STATUS: <span className="active">SYNCHRONIZED</span></span>
          <span>CAPACITY: 42.8 MB</span>
          <span>ENCRYPTION: AES-256</span>
        </div>
      </div>

      {/* Split Layout */}
      <div className="memory-bank-layout">
        
        {/* Left Navigation: Memory Index */}
        <div className="memory-index">
          <div className="index-title">INDEX DIRECTORY</div>
          <div className="index-list">
            {sectors.map((sector) => (
              <button 
                key={sector.id} 
                className={`index-item ${activeSector === sector.id ? 'active' : ''}`}
                onClick={() => setActiveSector(sector.id)}
              >
                {sector.label}
              </button>
            ))}
          </div>
        </div>

        {/* Right Content: Memory Buffer */}
        <div className="memory-buffer" key={activeSector}> 
          
          {activeSector === 'PROFILE' && memoryData?.user && (
            <div className="memory-section">
              <div className="section-label">01 / PRIMARY_PROFILE</div>
              
              <div className="sub-section-label">IDENTITY</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Name</span><span className="kv-value highlight">{memoryData.user.profile?.name}</span></div>
                <div className="kv-pair"><span className="kv-key">Phone</span><span className="kv-value">{memoryData.user.profile?.phone}</span></div>
              </div>

              <div className="sub-section-label">HOME</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Address</span><span className="kv-value">{memoryData.user.important_locations?.home?.address}</span></div>
                <div className="kv-pair"><span className="kv-key">Latitude</span><span className="kv-value">{memoryData.user.important_locations?.home?.lat}</span></div>
                <div className="kv-pair"><span className="kv-key">Longitude</span><span className="kv-value">{memoryData.user.important_locations?.home?.lng}</span></div>
              </div>
            </div>
          )}

          {activeSector === 'EMERGENCY' && memoryData?.user?.emergency_protocol && (
            <div className="memory-section">
              <div className="section-label">02 / EMERGENCY_PROTOCOL</div>
              
              <div className="sub-section-label">EMERGENCY RESPONSE</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Default Protocol</span><span className="kv-value critical">{memoryData.user.emergency_protocol.default_protocol}</span></div>
                <div className="kv-pair"><span className="kv-key">Emergency Mode</span><span className="kv-value">{memoryData.user.emergency_protocol.emergency_mode}</span></div>
                <div className="kv-pair"><span className="kv-key">Auto Escalation</span><span className="kv-value highlight">{memoryData.user.emergency_protocol.auto_escalation}</span></div>
              </div>

              <div className="sub-section-label">ESCALATION RULES</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Critical Incident</span><span className="kv-value">{memoryData.user.emergency_protocol.escalation_rules.critical_incident}</span></div>
                <div className="kv-pair"><span className="kv-key">Unresponsive Patient</span><span className="kv-value">{memoryData.user.emergency_protocol.escalation_rules.unresponsive_patient}</span></div>
                <div className="kv-pair"><span className="kv-key">Breathing Difficulty</span><span className="kv-value">{memoryData.user.emergency_protocol.escalation_rules.breathing_difficulty}</span></div>
                <div className="kv-pair"><span className="kv-key">Severe Injury</span><span className="kv-value">{memoryData.user.emergency_protocol.escalation_rules.severe_injury}</span></div>
              </div>

              <div className="sub-section-label">COMMUNICATION</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Primary Contact</span><span className="kv-value highlight">{memoryData.user.emergency_protocol.communication.primary_contact}</span></div>
                <div className="kv-pair"><span className="kv-key">Secondary Contact</span><span className="kv-value">{memoryData.user.emergency_protocol.communication.secondary_contact}</span></div>
                <div className="kv-pair"><span className="kv-key">Emergency Contact</span><span className="kv-value">{memoryData.user.emergency_protocol.communication.emergency_contact}</span></div>
              </div>

              <div className="sub-section-label">LOCATION & PREFERENCES</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Share Location</span><span className="kv-value">{memoryData.user.emergency_protocol.location_preferences.share_location}</span></div>
                <div className="kv-pair"><span className="kv-key">Location Precision</span><span className="kv-value highlight">{memoryData.user.emergency_protocol.location_preferences.location_precision}</span></div>
                <div className="kv-pair"><span className="kv-key">Keep User Updated</span><span className="kv-value">{memoryData.user.emergency_protocol.location_preferences.keep_user_updated}</span></div>
                <div className="kv-pair"><span className="kv-key">Family Notification</span><span className="kv-value">{memoryData.user.emergency_protocol.location_preferences.family_notification}</span></div>
                <div className="kv-pair"><span className="kv-key">Status Updates</span><span className="kv-value">{memoryData.user.emergency_protocol.location_preferences.status_updates}</span></div>
              </div>
            </div>
          )}

          {activeSector === 'KINSHIP' && memoryData?.user && (
            <div className="memory-section">
              <div className="section-label">03 / KINSHIP_MATRIX</div>
              
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Relation</th>
                    <th>Name</th>
                    <th>Contact</th>
                    <th>Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(memoryData.user.emergency_contacts || {}).map(([key, contact]: [string, any]) => (
                    <tr key={key}>
                      <td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>{contact.type}</td>
                      <td className={contact.priority === 'Primary' ? 'highlight' : ''}>{contact.name}</td>
                      <td style={{ fontFamily: 'var(--mono)' }}>{contact.phone}</td>
                      <td className={contact.priority === 'Primary' ? 'highlight' : ''}>{contact.priority}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeSector === 'MEDICAL' && memoryData?.patient && (
            <div className="memory-section">
              <div className="section-label">04 / MEDICAL_CONTEXT</div>
              
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Known Conditions</span><span className="kv-value highlight">{(memoryData.patient.father?.health_info?.known_conditions || []).join(', ') || 'None'}</span></div>
                <div className="kv-pair"><span className="kv-key">Allergies</span><span className="kv-value">{(memoryData.patient.father?.health_info?.allergies || []).join(', ') || 'None'}</span></div>
                <div className="kv-pair"><span className="kv-key">Current Medications</span><span className="kv-value">{(memoryData.patient.father?.health_info?.medications || []).join(', ') || 'None'}</span></div>
                <div className="kv-pair"><span className="kv-key">Special Considerations</span><span className="kv-value highlight">{memoryData.patient.father?.health_info?.emergency_notes || 'None'}</span></div>
              </div>

              <div className="medical-disclaimer">
                ⚠ MEDUSA DOES NOT DIAGNOSE<br/>
                <span>Medical context is used to inform response coordination only.</span>
              </div>
            </div>
          )}

          {activeSector === 'PREFERENCES' && memoryData?.user?.core_preferences && (
            <div className="memory-section">
              <div className="section-label">05 / CORE_PREFERENCES</div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>System Setting</th>
                    <th>Configured Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>RESPONSE STYLE</td><td className="highlight">{memoryData.user.core_preferences.response_style}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>NOTIFICATION LEVEL</td><td className="highlight">{memoryData.user.core_preferences.notification_level}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>FAMILY UPDATES</td><td className="highlight">{memoryData.user.core_preferences.family_updates}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>LOCATION SHARING</td><td className="highlight">{memoryData.user.core_preferences.location_sharing}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>VOICE CONFIRMATION</td><td className="highlight">{memoryData.user.core_preferences.voice_confirmation}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>LANGUAGE</td><td className="highlight">{memoryData.user.core_preferences.language}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>EMERGENCY LANGUAGE</td><td className="highlight">{memoryData.user.core_preferences.emergency_language}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>STATUS UPDATES</td><td className="highlight">{memoryData.user.core_preferences.status_updates}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>UI THEME</td><td className="highlight">{memoryData.user.core_preferences.ui_theme}</td></tr>
                  <tr><td style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)' }}>STATUS</td><td className="critical">{memoryData.user.core_preferences.status}</td></tr>
                </tbody>
              </table>
            </div>
          )}

          {activeSector === 'INCIDENTS' && memoryData?.incidents && (
            <div className="memory-section">
              <div className="section-label">06 / INCIDENT_MEMORY</div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Incident ID</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Event</th>
                    <th>Location</th>
                  </tr>
                </thead>
                <tbody>
                  {memoryData.incidents.map((inc: any) => (
                    <tr key={inc.id}>
                      <td className="highlight" style={{ fontFamily: 'var(--mono)' }}>{inc.id}</td>
                      <td style={{ fontFamily: 'var(--mono)' }}>{inc.timestamp ? new Date(inc.timestamp).toLocaleDateString() : 'Unknown Date'}</td>
                      <td className={inc.status === 'ACTIVE' ? 'critical' : ''}>{inc.status}</td>
                      <td>{inc.situation?.reported || 'Emergency Incident'}</td>
                      <td>{inc.patient?.address || 'Unknown Location'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="sub-section-label">ACTIVE INCIDENT DETAIL</div>
              <div className="kv-grid">
                {memoryData.incidents.filter((inc: any) => inc.status === 'ACTIVE').map((inc: any) => (
                  <React.Fragment key={inc.id}>
                    <div className="kv-pair"><span className="kv-key">Patient</span><span className="kv-value highlight">{inc.patient?.name || 'Unknown'}</span></div>
                    <div className="kv-pair"><span className="kv-key">Event</span><span className="kv-value critical">{inc.situation?.reported || 'Emergency'}</span></div>
                    <div className="kv-pair"><span className="kv-key">Location</span><span className="kv-value">{inc.patient?.address || 'Unknown'}</span></div>
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          {activeSector === 'CARE' && memoryData?.user?.care_network && (
            <div className="memory-section">
              <div className="section-label">07 / CARE_NETWORK</div>
              
              <div className="sub-section-label">PRIMARY PHYSICIAN</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Name</span><span className="kv-value highlight">{memoryData.user.care_network.primary_physician.name}</span></div>
                <div className="kv-pair"><span className="kv-key">Specialty</span><span className="kv-value">{memoryData.user.care_network.primary_physician.specialty}</span></div>
                <div className="kv-pair"><span className="kv-key">Phone</span><span className="kv-value">{memoryData.user.care_network.primary_physician.phone}</span></div>
              </div>

              <div className="sub-section-label">PREFERRED FACILITY</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Facility</span><span className="kv-value highlight">{memoryData.user.care_network.preferred_facility.facility}</span></div>
                <div className="kv-pair"><span className="kv-key">Reason</span><span className="kv-value">{memoryData.user.care_network.preferred_facility.reason}</span></div>
              </div>

              <div className="sub-section-label">LOCAL SUPPORT</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">{memoryData.user.care_network.local_support.relation}</span><span className="kv-value highlight">{memoryData.user.care_network.local_support.name}</span></div>
                <div className="kv-pair"><span className="kv-key">Phone</span><span className="kv-value">{memoryData.user.care_network.local_support.phone}</span></div>
              </div>

              <div className="sub-section-label">EMERGENCY SERVICES</div>
              <div className="kv-grid">
                <div className="kv-pair"><span className="kv-key">Local Emergency</span><span className="kv-value critical">{memoryData.user.care_network.emergency_services.local_emergency}</span></div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
