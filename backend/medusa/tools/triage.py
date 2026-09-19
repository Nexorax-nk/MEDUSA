from datetime import datetime
from ..database import db

def register_triage_tools(mcp):
    @mcp.tool()
    def assign_triage_priority(incident_id: str, priority_level: str, medical_reasoning: str) -> str:
        """Analyze the emergency and assign a formal clinical triage priority (CRITICAL, HIGH, MEDIUM, LOW)."""
        print(f"[TOOL CALLED] TRIAGE: assign_triage_priority(incident_id={incident_id}, priority_level={priority_level})")
        incident = db.get_incident(incident_id)
        if incident:
            incident["operational_state"]["triage_priority"] = priority_level.upper()
            incident["operational_state"]["triage_reasoning"] = medical_reasoning
            incident["events"].append(
                {"timestamp": datetime.now().isoformat(), "event": f"Triage assigned: {priority_level} - {medical_reasoning}"}
            )
            try:
                from ..history_db import save_incident
                save_incident(incident_id, incident)
            except Exception as e:
                print(f"Error saving triage: {e}")
            return f"Incident {incident_id} triaged as {priority_level.upper()} priority."
        return "Incident not found."
