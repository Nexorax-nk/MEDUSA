import json
from ..database import db

def register_incident_tools(mcp):
    @mcp.tool()
    def create_incident(patient_id: str, event_type: str) -> str:
        """Create a new emergency incident and trigger response workflows."""
        print(f"[TOOL CALLED] INCIDENT: create_incident(patient_id={patient_id}, event_type={event_type})")
        incident_id = db.create_incident(patient_id, event_type)
        return f"Incident Created: {incident_id}. Status: ACTIVE. Event: {event_type}."

    @mcp.tool()
    def get_incident_status(incident_id: str) -> str:
        """Get the current status of an incident."""
        print(f"[TOOL CALLED] INCIDENT: get_incident_status(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if incident:
            return f"Incident {incident_id} Status: {incident['operational_state']['status']}"
        return "Incident not found."

    @mcp.tool()
    def update_incident(incident_id: str, status: str) -> str:
        """Update the status of an incident (e.g., ACTIVE, RESOLVED, ESCALATED)."""
        print(f"[TOOL CALLED] INCIDENT: update_incident(incident_id={incident_id}, status={status})")
        if db.update_incident_status(incident_id, status):
            return f"Incident {incident_id} updated to {status}."
        return "Incident not found."

    @mcp.tool()
    def get_incident_timeline(incident_id: str) -> str:
        """Get the timeline of events for an incident."""
        print(f"[TOOL CALLED] INCIDENT: get_incident_timeline(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if incident:
            return json.dumps(incident["events"], indent=2)
        return "Incident not found."

    @mcp.tool()
    def close_incident(incident_id: str) -> str:
        """Close an incident."""
        print(f"[TOOL CALLED] INCIDENT: close_incident(incident_id={incident_id})")
        if db.update_incident_status(incident_id, "CLOSED"):
            return f"Incident {incident_id} successfully closed."
        return "Incident not found."

    @mcp.tool()
    def update_clinical_state(incident_id: str, conscious: str, breathing: str, condition_description: str) -> str:
        """Record structured clinical observations for an incident. conscious: 'yes'/'no'/'unknown'. breathing: 'normal'/'abnormal'/'absent'/'unknown'. condition_description: brief description of the patient's current state."""
        print(f"[TOOL CALLED] INCIDENT: update_clinical_state(incident_id={incident_id}, conscious={conscious}, breathing={breathing})")
        incident = db.get_incident(incident_id)
        if not incident:
            return "Incident not found."
        
        clinical_state = {
            "conscious": conscious.lower(),
            "breathing": breathing.lower(),
            "condition": condition_description,
            "recorded_at": __import__('datetime').datetime.now().isoformat()
        }
        incident["operational_state"]["clinical_state"] = clinical_state
        db.record_observation(incident_id, f"Clinical state: conscious={conscious}, breathing={breathing}, condition={condition_description}")
        
        try:
            from ..history_db import save_incident
            save_incident(incident_id, incident)
        except Exception as e:
            print(f"Error saving clinical state: {e}")
            
        return f"Clinical state recorded for {incident_id}: conscious={conscious}, breathing={breathing}."
