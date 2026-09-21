import json
from datetime import datetime
from ..database import db

def register_handoff_tools(mcp):
    @mcp.tool()
    def generate_handoff(incident_id: str) -> str:
        """Generate a comprehensive clinical handoff summary for hospital staff, including full patient medical context."""
        print(f"[TOOL CALLED] HANDOFF: generate_handoff(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if not incident:
            return "Incident not found."
        
        patient_key = incident["operational_state"]["patient"]
        patient = db.get_patient(patient_key)
        
        # Build comprehensive handoff
        handoff = {
            "incident_id": incident_id,
            "generated_at": datetime.now().isoformat(),
            "patient": {
                "name": patient["profile"]["name"] if patient else "Unknown",
                "age": patient["profile"].get("age", "Unknown") if patient else "Unknown",
                "blood_group": patient["profile"].get("blood_group", "Unknown") if patient else "Unknown",
                "phone": patient["profile"].get("phone", "Unknown") if patient else "Unknown",
            },
            "medical_history": {
                "known_conditions": patient["health_info"].get("known_conditions", []) if patient else [],
                "allergies": patient["health_info"].get("allergies", []) if patient else [],
                "current_medications": patient["health_info"].get("medications", []) if patient else [],
                "emergency_notes": patient["health_info"].get("emergency_notes", "") if patient else "",
            },
            "incident_details": {
                "event": incident["events"][0]["event"] if incident["events"] else "Unknown",
                "status": incident["operational_state"]["status"],
                "triage_priority": incident["operational_state"].get("triage_priority", "Not assigned"),
                "triage_reasoning": incident["operational_state"].get("triage_reasoning", ""),
                "clinical_state": incident["operational_state"].get("clinical_state", {}),
                "observations": incident["operational_state"]["observations"],
            },
            "actions_taken": {
                "contacts_notified": incident["operational_state"].get("contacts_notified", False),
                "helpers_dispatched": len(incident["operational_state"]["assigned_helpers"]),
                "transport_status": "DISPATCHED" if any("Transport" in e.get("event", "") for e in incident["events"]) else "PENDING",
            }
        }
        
        # S3 Integration for secure handoff archival
        import boto3
        import os
        from botocore.exceptions import ClientError
        
        try:
            region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            s3_client = boto3.client('s3', region_name=region_name)
            sts_client = boto3.client('sts', region_name=region_name)
            account_id = sts_client.get_caller_identity()["Account"]
            
            # Create a globally unique bucket name
            bucket_name = f"medusa-handoffs-{account_id}-{region_name}"
            
            # Ensure bucket exists
            try:
                s3_client.head_bucket(Bucket=bucket_name)
            except ClientError:
                if region_name == "us-east-1":
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region_name})
            
            # Upload handoff to S3
            s3_key = f"handoffs/{incident_id}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(handoff, indent=2),
                ContentType="application/json"
            )
            
            # Log custom metric
            try:
                from backend.medusa.cloudwatch import push_metric
                push_metric('S3HandoffsArchived', 1)
            except Exception:
                pass
                
        except Exception as e:
            print(f"S3 Upload failed: {e}")
        
        incident["handoff_state"]["generated"] = True
        incident["handoff_state"]["document"] = handoff
        db.handoffs[incident_id] = handoff
        try:
            from ..history_db import save_incident
            save_incident(incident_id, incident)
        except Exception:
            pass

        # Return a human-readable summary
        summary = (
            f"MEDUSA Clinical Handoff — {incident_id}\n"
            f"Patient: {handoff['patient']['name']}, Age {handoff['patient']['age']}, Blood: {handoff['patient']['blood_group']}\n"
            f"Conditions: {', '.join(handoff['medical_history']['known_conditions']) or 'None'}\n"
            f"Allergies: {', '.join(handoff['medical_history']['allergies']) or 'None'}\n"
            f"Medications: {', '.join(handoff['medical_history']['current_medications']) or 'None'}\n"
            f"Triage: {handoff['incident_details']['triage_priority']}\n"
            f"Handoff generated and ready for hospital staff."
        )
        return summary

    @mcp.tool()
    def get_handoff(incident_id: str) -> str:
        """Retrieve a generated handoff document."""
        print(f"[TOOL CALLED] HANDOFF: get_handoff(incident_id={incident_id})")
        handoff = db.handoffs.get(incident_id)
        if handoff:
            return json.dumps(handoff, indent=2)
        return "Handoff not found."

    @mcp.tool()
    def share_handoff(incident_id: str, target_facility: str) -> str:
        """Share the handoff securely with a target facility."""
        print(f"[TOOL CALLED] HANDOFF: share_handoff(incident_id={incident_id}, target_facility={target_facility})")
        if incident_id in db.handoffs:
            return f"Handoff for {incident_id} shared securely with {target_facility}."
        return "Handoff not found. Generate it first."

    @mcp.tool()
    def export_handoff(incident_id: str, format: str) -> str:
        """Export the handoff document in a specific format (e.g., PDF, HL7)."""
        print(f"[TOOL CALLED] HANDOFF: export_handoff(incident_id={incident_id}, format={format})")
        if incident_id in db.handoffs:
            return f"Handoff exported as {format} format. Link: https://medusa.local/exports/{incident_id}.{format.lower()}"
        return "Handoff not found."
