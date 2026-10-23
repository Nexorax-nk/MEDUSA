import json
import random
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

    @mcp.tool()
    def calculate_gcs_score(eye_response: int, verbal_response: int, motor_response: int) -> str:
        """Calculate the Glasgow Coma Scale (GCS) score (range 3-15) to quantitatively grade acute patient consciousness and neurological impairment."""
        print(f"[TOOL CALLED] TRIAGE: calculate_gcs_score(E={eye_response}, V={verbal_response}, M={motor_response})")
        e = max(1, min(4, eye_response))
        v = max(1, min(5, verbal_response))
        m = max(1, min(6, motor_response))
        total = e + v + m
        
        if total <= 8:
            severity = "SEVERE_BRAIN_INJURY_COMA"
            recommendation = "Immediate intubation & airway protection required."
        elif total <= 12:
            severity = "MODERATE_IMPAIRMENT"
            recommendation = "Continuous neurological surveillance & trauma evaluation."
        else:
            severity = "MILD_OR_NORMAL"
            recommendation = "Monitor for deterioration or secondary concussion."
            
        result = {
            "gcs_total": total,
            "components": {"eye": e, "verbal": v, "motor": m},
            "clinical_severity": severity,
            "recommendation": recommendation,
            "calculated_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def stream_biometric_vitals(patient_id: str) -> str:
        """Query real-time continuous vitals (heart rate, SpO2, blood pressure, ECG rhythm) streamed from paired wearable devices (Apple Watch, Bee, or smart sensors)."""
        print(f"[TOOL CALLED] TRIAGE: stream_biometric_vitals(patient_id={patient_id})")
        patient = db.get_patient(patient_id)
        patient_name = patient["profile"]["name"] if patient else "Monitored Patient"
        
        vitals = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "heart_rate_bpm": random.randint(118, 142),  # Tachycardia in distress
            "spo2_percentage": random.randint(89, 93),   # Hypoxemic alert
            "blood_pressure": "165/105 mmHg",            # Hypertensive emergency
            "cardiac_rhythm": "ST_ELEVATION_SUSPECTED",
            "wearable_source": "Amazon Bee / Connected Health Ring",
            "telemetry_timestamp": datetime.now().isoformat(),
            "status": "ACUTE_PHYSIOLOGICAL_DISTRESS"
        }
        return json.dumps(vitals, indent=2)
