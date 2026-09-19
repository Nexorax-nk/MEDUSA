from ..database import db

def register_situation_tools(mcp):
    @mcp.tool()
    def record_observation(incident_id: str, observation: str) -> str:
        """Record a situational observation to the incident log (e.g., 'patient is unresponsive')."""
        print(f"[TOOL CALLED] SITUATION: record_observation(incident_id={incident_id}, observation={observation})")
        if db.record_observation(incident_id, observation):
            return f"Observation recorded for incident {incident_id}."
        return "Failed to record observation. Incident not found."
