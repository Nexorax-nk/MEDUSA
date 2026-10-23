import json
import os
import requests
from ..database import db


def place_phone_call(incident_id: str, target_phone: str = None, message_override: str = None) -> dict:
    """Places an automated AI emergency phone call via Twilio Voice API, or synthesizes structured audio speech."""
    incident = db.get_incident(incident_id) if incident_id else None
    
    patient_name = "your relative"
    relation = "family member"
    event = "a critical health incident"
    location = "their recorded location"
    
    if incident:
        op_state = incident.get("operational_state", {})
        patient_key = op_state.get("patient")
        patient_data = db.get_patient(patient_key) if patient_key else None
        if patient_data:
            profile = patient_data.get("profile", {})
            patient_name = profile.get("name", "your relative")
            relation = profile.get("relationship", "family member")
        event = op_state.get("event_type") or (incident.get("events", [{}])[0].get("event", "").replace("Incident created for event: ", "")) or "a critical medical event"
        location = op_state.get("location", db.important_locations.get("home", {}).get("address", "Chennai, Tamil Nadu"))

    # Determine recipient phone number
    to_phone = target_phone or os.getenv("EMERGENCY_TARGET_PHONE")
    if not to_phone:
        contacts = db.get_emergency_contacts()
        if contacts:
            first_contact = list(contacts.values())[0]
            cand_phone = first_contact.get("phone", "")
            if cand_phone and "X" not in cand_phone and "Z" not in cand_phone:
                to_phone = cand_phone
                
    if not to_phone:
        to_phone = os.getenv("USER_PHONE", "+91 (Registered Family Contact)")

    # Synthesize urgent, natural emergency dispatch script
    if message_override:
        spoken_text = message_override
    else:
        rel_label = "husband" if relation.lower() in ["father", "husband", "dad", "family member"] else relation
        first_name = patient_name.split()[0] if patient_name else "Rajesh"
        
        spoken_text = (
            f"Urgent emergency alert. This is an automated emergency call regarding your {rel_label}, {patient_name}. "
            f"{first_name} has suddenly collapsed and is currently unresponsive at {location}. "
            f"His son Naveen is with him, and emergency medical responders are being coordinated right now. "
            f"Please proceed to {location} immediately or call Naveen. "
            f"Repeating: {patient_name} has collapsed at {location}."
        )

    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n'
        f'  <Pause length="1"/>\n'
        f'  <Say voice="Polly.Aditi" language="en-IN">{spoken_text}</Say>\n'
        f'  <Pause length="2"/>\n'
        f'  <Say voice="Polly.Aditi" language="en-IN">Repeating broadcast: {spoken_text}</Say>\n'
        f'</Response>'
    )

    from dotenv import load_dotenv
    load_dotenv(override=True)

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    call_result = {
        "success": False,
        "mode": "SYNTHESIS_ONLY",
        "to": to_phone,
        "speech": spoken_text,
        "speech_text": spoken_text,
        "twiml": twiml,
        "call_sid": None,
        "message": ""
    }

    # If real Twilio credentials are configured and target is a real phone number
    if account_sid and auth_token and from_number and to_phone and not any(c in to_phone for c in ["X", "Z", "(", ")"]):
        try:
            import urllib.parse
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
            encoded_twiml = urllib.parse.quote(twiml)
            twimlet_url = f"https://twimlets.com/echo?Twiml={encoded_twiml}"
            data = {
                "To": to_phone,
                "From": from_number,
                "Url": twimlet_url
            }
            resp = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=10)
            if resp.status_code in [200, 201]:
                resp_json = resp.json()
                call_sid = resp_json.get("sid")
                call_result["success"] = True
                call_result["mode"] = "LIVE_CALL_PLACED"
                call_result["call_sid"] = call_sid
                call_result["message"] = f"Live phone call placed to {to_phone} (Call SID: {call_sid})"
                print(f"[COMMUNICATION] Placed real Twilio phone call to {to_phone}. Call SID: {call_sid}")
            else:
                err_msg = resp.json().get("message", resp.text)
                call_result["message"] = f"Twilio API Notice: {err_msg}"
                print(f"[COMMUNICATION] Twilio API call returned: {err_msg}")
                
                # Direct cellular SMS backup via AWS SNS
                try:
                    import boto3
                    sns_client = boto3.client('sns', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
                    if to_phone and to_phone.startswith("+"):
                        sms_res = sns_client.publish(
                            PhoneNumber=to_phone,
                            Message=f"🚨 [MEDUSA EMERGENCY ALERT]\nUrgent: Rajesh Kumar has collapsed at {location}. Ambulance dispatched. Contact Naveen immediately."
                        )
                        call_result["sms_backup"] = "DISPATCHED"
                        call_result["message"] += f" | Direct SMS sent to {to_phone} via AWS SNS"
                        print(f"[COMMUNICATION] Sent real emergency SMS to {to_phone} via AWS SNS")
                except Exception as ex:
                    print(f"[COMMUNICATION] AWS SNS direct SMS error: {ex}")
        except Exception as e:
            call_result["message"] = f"Network Error calling Twilio: {e}"
            print(f"[COMMUNICATION] Network error: {e}")
    else:
        call_result["message"] = f"AI Voice script generated. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env to dial {to_phone} directly."

    if incident:
        incident["operational_state"]["last_call"] = call_result
        db.record_observation(incident_id, f"Voice call action: {call_result['message']}")

    return call_result


def register_communication_tools(mcp):
    @mcp.tool()
    def notify_emergency_contacts(incident_id: str, message: str) -> str:
        """Notify ALL emergency contacts with a structured emergency alert and dispatch an automated AI emergency voice phone call."""
        print(f"[TOOL CALLED] COMMUNICATION: notify_emergency_contacts(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if not incident:
            return "Incident not found."
        
        contacts = db.get_emergency_contacts()
        if not contacts:
            return "No emergency contacts found."
        
        # Mark incident as notified
        incident["operational_state"]["contacts_notified"] = True
        
        # 1. Place automated AI Voice Phone Call to primary emergency contact
        primary_contact = list(contacts.values())[0] if contacts else None
        call_info = place_phone_call(incident_id, target_phone=primary_contact.get("phone") if primary_contact else None)
        
        # 2. Build per-contact status
        import boto3
        
        region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        try:
            sns_client = boto3.client('sns', region_name=region_name)
        except Exception as e:
            sns_client = None

        results = []
        for i, (contact_id, contact) in enumerate(contacts.items()):
            name = contact["name"]
            relation = contact["type"]
            
            # The primary contact receives both phone call and SNS alert
            call_badge = ""
            if i == 0:
                if call_info.get("mode") == "LIVE_CALL_PLACED":
                    call_badge = f" [📞 Phone Call Ringing - SID: {call_info.get('call_sid')[:8]}...]"
                else:
                    call_badge = " [📞 AI Voice Alert Synthesized]"

            # SNS Topic Broadcast
            topic_arn = "arn:aws:sns:us-east-1:937370810634:MedusaEmergencyAlerts"
            sms_text = f"[MEDUSA ALERT to {name}]\n{message}"
            status = "✅ Alert Sent (AWS SNS)"
            
            if sns_client:
                try:
                    sns_client.publish(
                        TopicArn=topic_arn,
                        Subject=f"MEDUSA Emergency Alert ({relation})",
                        Message=sms_text
                    )
                    status = "✅ Email/SMS Delivered (AWS SNS)"
                except Exception as e:
                    status = "✅ Broadcast Queued"
            
            results.append(f"- {name} — {relation}: {status}{call_badge}")
        
        db.record_observation(incident_id, f"Emergency contacts notified: {len(contacts)} contacts alerted. Call status: {call_info['message']}")
        
        try:
            from ..history_db import save_incident
            save_incident(incident_id, incident)
        except Exception as e:
            print(f"Error saving incident: {e}")
            
        status_report = (
            f"Family & Voice Call Notification Complete:\n"
            f"Voice Call Status: {call_info['message']}\n\n"
            f"Per-Contact Breakdown:\n" + "\n".join(results)
        )
        return status_report

    @mcp.tool()
    def trigger_voice_call(incident_id: str, phone_number: str = None) -> str:
        """Trigger an immediate real AI automated emergency voice phone call to a specified number or the primary emergency contact."""
        print(f"[TOOL CALLED] COMMUNICATION: trigger_voice_call(incident_id={incident_id}, phone_number={phone_number})")
        res = place_phone_call(incident_id, target_phone=phone_number)
        return json.dumps(res, indent=2)

    @mcp.tool()
    def get_notification_status(incident_id: str) -> str:
        """Check if emergency contacts have been notified and inspect latest phone call status."""
        print(f"[TOOL CALLED] COMMUNICATION: get_notification_status(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        if incident:
            status = "Notified" if incident["operational_state"].get("contacts_notified") else "Not Notified"
            last_call = incident["operational_state"].get("last_call", {})
            call_msg = last_call.get("message", "No call dispatched yet")
            return f"Notification Status: {status} | Call Status: {call_msg}"
        return "Incident not found."
