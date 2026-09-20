import json
from ..database import db

def register_communication_tools(mcp):
    @mcp.tool()
    def notify_emergency_contacts(incident_id: str, message: str) -> str:
        """Notify ALL emergency contacts with a structured emergency alert. Returns per-contact notification status."""
        print(f"[TOOL CALLED] COMMUNICATION: notify_emergency_contacts(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if not incident:
            return "Incident not found."
        
        contacts = db.get_emergency_contacts()
        if not contacts:
            return "No emergency contacts found."
        
        # Mark incident as notified
        incident["operational_state"]["contacts_notified"] = True
        
        # Build per-contact status
        import boto3
        import os
        
        region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        try:
            sns_client = boto3.client('sns', region_name=region_name)
        except Exception as e:
            return f"Error initializing AWS SNS: {e}"

        results = []
        for contact_id, contact in contacts.items():
            name = contact["name"]
            relation = contact["type"]
            priority = contact["priority"]
            
            # Hackathon Demo: Use SNS Topic to bypass Indian SMS telecom regulations
            topic_arn = "arn:aws:sns:us-east-1:937370810634:MedusaEmergencyAlerts"
            
            sms_text = f"[MEDUSA ALERT to {name}]\n{message}"
            
            try:
                sns_client.publish(
                    TopicArn=topic_arn,
                    Subject=f"MEDUSA Emergency Alert ({relation})",
                    Message=sms_text
                )
                status = "✅ Email Delivered (AWS SNS)"
                
                try:
                    from backend.medusa.cloudwatch import push_metric
                    push_metric('SMSAlertsSent', 1)
                except Exception:
                    pass
            except Exception as e:
                # E.g. Missing permissions
                status = f"❌ AWS SNS Failed: {e}"
                
            results.append(f"- {name} — {relation}: {status}")
        
        db.record_observation(incident_id, f"Emergency contacts notified: {len(contacts)} contacts alerted.")
        
        try:
            from ..history_db import save_incident
            save_incident(incident_id, incident)
        except Exception as e:
            print(f"Error saving incident: {e}")
            
        status_report = f"Family Notification Complete — {len(contacts)} contacts alerted:\n" + "\n".join(results)
        return status_report

    @mcp.tool()
    def get_notification_status(incident_id: str) -> str:
        """Check if emergency contacts have been notified."""
        print(f"[TOOL CALLED] COMMUNICATION: get_notification_status(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if incident:
            status = "Notified" if incident["operational_state"].get("contacts_notified") else "Not Notified"
            return f"Notification Status: {status}"
        return "Incident not found."
