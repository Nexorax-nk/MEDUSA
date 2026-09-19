import json
from ..database import db

def register_community_tools(mcp):
    @mcp.tool()
    def find_nearby_helpers(location: str, radius_km: float) -> str:
        """Find nearby community responders and helpers."""
        print(f"[TOOL CALLED] COMMUNITY: find_nearby_helpers(location={location}, radius_km={radius_km})")
        # Just return the mock helpers that fit within radius
        available = [h for h in db.helpers.values() if h["status"] == "AVAILABLE" and h["distance_km"] <= radius_km]
        return json.dumps(available, indent=2)

    @mcp.tool()
    def request_helper_assistance(incident_id: str, helper_id: str) -> str:
        """Dispatch a specific community helper to an incident."""
        print(f"[TOOL CALLED] COMMUNITY: request_helper_assistance(incident_id={incident_id}, helper_id={helper_id})")
        incident = db.get_incident(incident_id)
        helper = db.helpers.get(helper_id)
        if incident and helper and helper["status"] == "AVAILABLE":
            helper["status"] = "DISPATCHED"
            incident["operational_state"]["assigned_helpers"].append(helper_id)
            db.record_observation(incident_id, f"Helper {helper['name']} dispatched.")
            return f"Helper {helper['name']} requested successfully."
        return "Failed to request helper. Either incident/helper not found or helper busy."

    @mcp.tool()
    def get_helper_status(helper_id: str) -> str:
        """Get the current status of a community helper."""
        print(f"[TOOL CALLED] COMMUNITY: get_helper_status(helper_id={helper_id})")
        helper = db.helpers.get(helper_id)
        if helper:
            return f"Helper {helper['name']} Status: {helper['status']}"
        return "Helper not found."
