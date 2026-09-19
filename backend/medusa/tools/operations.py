import json
from ..database import db

def register_operations_tools(mcp):
    @mcp.tool()
    def get_incident_activity(incident_id: str) -> str:
        """Get a full activity report for operations/command center dashboard."""
        print(f"[TOOL CALLED] OPERATIONS: get_incident_activity(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if incident:
            activity = {
                "active": incident["operational_state"]["status"] == "ACTIVE",
                "helpers_dispatched": len(incident["operational_state"]["assigned_helpers"]),
                "contacts_notified": incident["operational_state"].get("contacts_notified", False),
                "timeline_events": len(incident["events"])
            }
            return json.dumps(activity, indent=2)
        return "Incident not found."
