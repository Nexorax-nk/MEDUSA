import json
from ..database import db

def register_patient_tools(mcp):
    @mcp.tool()
    def resolve_kinship(relation: str) -> str:
        """Resolve a natural language relationship (e.g. 'my father') to a specific patient identity in the Patient Memory."""
        print(f"[TOOL CALLED] PATIENT: resolve_kinship(relation={relation})")
        relation_key = db.resolve_kinship(relation)
        if relation_key:
            patient = db.get_patient(relation_key)
            return f"Identity Resolved: {patient['profile']['name']}. IMPORTANT: For all subsequent tool calls, you MUST use patient_id: '{relation_key}'."
        return f"Identity not found for relation: {relation}"

    @mcp.tool()
    def get_patient_context(patient_id: str) -> str:
        """Retrieve the full profile and health context for a given patient from Patient Memory."""
        print(f"[TOOL CALLED] PATIENT: get_patient_context(patient_id={patient_id})")
        patient = db.get_patient(patient_id)
        if patient:
            return json.dumps(patient, indent=2)
        return "Patient context not found."

    @mcp.tool()
    def get_emergency_contacts() -> str:
        """Fetch the prioritized list of emergency contacts for the user from User Memory."""
        print(f"[TOOL CALLED] PATIENT: get_emergency_contacts()")
        contacts = db.get_emergency_contacts()
        if contacts:
            return json.dumps(contacts, indent=2)
        return "No emergency contacts found."

    @mcp.tool()
    def get_important_location(location_name: str) -> str:
        """Fetch the exact address and coordinates for a named location (e.g., 'home', 'parents home') from User Memory."""
        print(f"[TOOL CALLED] PATIENT: get_important_location(location_name={location_name})")
        loc = db.get_important_location(location_name)
        if loc:
            return json.dumps(loc, indent=2)
        return f"Location '{location_name}' not found in User Memory."
        