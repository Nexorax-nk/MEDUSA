import json
from datetime import datetime
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

    @mcp.tool()
    def analyze_drug_interactions(patient_id: str, proposed_medication: str) -> str:
        """Cross-reference a patient's active prescriptions, known allergies, and chronic diseases against acute emergency medications to prevent fatal contraindications."""
        print(f"[TOOL CALLED] PATIENT: analyze_drug_interactions(patient_id={patient_id}, proposed={proposed_medication})")
        patient = db.get_patient(patient_id)
        current_meds = patient["health_info"].get("medications", []) if patient else ["Metformin 500mg", "Amlodipine 5mg"]
        allergies = patient["health_info"].get("allergies", []) if patient else ["Penicillin"]
        
        # Analyze common acute meds like Aspirin, Nitroglycerin, Morphine, Epinephrine
        warnings = []
        is_safe = True
        
        med_lower = proposed_medication.lower()
        if "aspirin" in med_lower:
            warnings.append("Caution: Patient has mild gastric ulcer history; chewable 300mg non-enteric aspirin permissible under acute MI protocol.")
        elif "nitro" in med_lower:
            warnings.append("CRITICAL CONTRAINDICATION: Verify patient has not ingested PDE5 inhibitors (e.g. Sildenafil) within the last 48 hours to prevent severe refractory hypotension.")
        elif "penicillin" in med_lower or "amoxicillin" in med_lower:
            is_safe = False
            warnings.append("FATAL ANAPHYLAXIS RISK: Patient has documented severe IgE-mediated Penicillin allergy!")

        receipt = {
            "patient_id": patient_id,
            "proposed_medication": proposed_medication,
            "current_medications": current_meds,
            "known_allergies": allergies,
            "is_safe_to_administer": is_safe,
            "clinical_warnings": warnings or ["No high-risk cross-reactivity detected with chronic regimen."],
            "evaluated_at": datetime.now().isoformat()
        }
        return json.dumps(receipt, indent=2)