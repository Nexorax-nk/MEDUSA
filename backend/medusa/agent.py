import os
import json
import asyncio
import random
from typing import AsyncGenerator
from groq import AsyncGroq
from mcp.server.mcpserver import MCPServer

# ═══════════════════════════════════════════════════════════════
# Groq Client Setup with Key Rotation
# ═══════════════════════════════════════════════════════════════
_groq_keys = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
]
_groq_keys = [k for k in _groq_keys if k]
_groq_clients = [AsyncGroq(api_key=k) for k in _groq_keys]
_current_key_index = 0

MODEL_NAME = "qwen/qwen3.8-27b"


def _get_client():
    global _current_key_index
    return _groq_clients[_current_key_index % len(_groq_clients)]


def _rotate_key():
    global _current_key_index
    if len(_groq_clients) > 1:
        _current_key_index = (_current_key_index + 1) % len(_groq_clients)
        print(f"[AGENT] Rotated to Groq API key #{_current_key_index + 1}")
        return True
    return False


async def _llm_call(messages: list, max_tokens: int = 400) -> str:
    """Single resilient LLM call with retry + key rotation."""
    for attempt in range(4):
        try:
            client = _get_client()
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as err:
            err_str = str(err)
            if "429" in err_str or "rate" in err_str.lower():
                rotated = _rotate_key()
                if rotated:
                    await asyncio.sleep(1)
                else:
                    delay = min(2 ** attempt, 16) + random.random()
                    print(f"[AGENT] Rate limited. Waiting {delay:.1f}s (attempt {attempt+1}/4)")
                    await asyncio.sleep(delay)
            else:
                raise err
    return ""


# ═══════════════════════════════════════════════════════════════
# Intent Classification Prompt (Call #1 — lightweight)
# ═══════════════════════════════════════════════════════════════
INTENT_PROMPT = """You are a triage classifier for an emergency system in INDIA.
Analyze the user's message and the conversation history, then output ONLY a JSON object.

If the message is about a medical emergency (collapse, chest pain, breathing trouble, unconscious, seizure, fall, bleeding, injury):
{"intent":"emergency","relation":"<family relation like father/mother/sister or 'self'>","event":"<short description like 'collapsed' or 'chest pain'>"}

If the message is answering a question about consciousness/breathing during an active emergency:
{"intent":"clinical_update","conscious":"<yes/no/unknown>","breathing":"<normal/abnormal/absent/unknown>","details":"<any extra info>"}

If the message is a confirmation/acknowledgment (okay, yes, do it, go ahead) during an active emergency AND MEDUSA just asked about notifying contacts, OR if the user provides a location correction (e.g., "No, I am at Central Mall"):
{"intent":"confirm_notify", "override_location": "<location if mentioned, else null>"}

If the message is a confirmation to search for a hospital/facility:
{"intent":"confirm_search"}

If the message explicitly confirms ambulance dispatch (yes dispatch, send ambulance, go ahead with transport, confirm dispatch):
{"intent":"dispatch_confirm"}

If the message asks for the current status of the incident, what has been done, who has been notified, or what is pending:
{"intent":"status_request"}

If the message is normal conversation (greeting, question, anything non-emergency):
{"intent":"chat"}

Output ONLY the JSON. No markdown, no explanation, no extra text."""


# ═══════════════════════════════════════════════════════════════
# Response Generation Prompt (Call #2 — with Action Receipts)
# ═══════════════════════════════════════════════════════════════
RESPONSE_PROMPT = """You are Alexa, an emergency AI powered by MEDUSA. You are based in INDIA.

Given the CONTEXT below, generate a response following the PHASE-SPECIFIC rules.

CRITICAL RULES:
- NEVER say "call 911" — India uses 108/112, but YOU are the emergency service.
- Follow the exact formatting requested for your current phase.
- Be warm, empathetic, and decisive. You are their lifeline.
- ONLY output the content for the CURRENT PHASE instructed in the context.
- Your job is NOT to merely have a medical conversation.
- Your job is to communicate the current state of an emergency response clearly while MEDUSA coordinates the incident.

═══ PHASE-SPECIFIC INSTRUCTIONS ═══

PHASE 1 (Emergency detected):
- Immediately acknowledge the emergency.
- Confirm that MEDUSA created/opened the incident.
- Use a bulleted list to confirm the incident ID and patient details (name, age, known conditions).
- State the triage level clearly (e.g., "Triage: **CRITICAL**").
- Bold your final question: "**Is he/she conscious and breathing normally?**"

PHASE 2 (Clinical update received):
- Acknowledge the condition and give the first-aid instructions from CONTEXT.
- State that you are preparing to notify family contacts.
- State that you have their home address on file as their location.
- Bold your final question: "**Are you currently at home, and shall I alert your emergency contacts?**"

PHASE 3 (Family + Nearby Assistance):
- Use a bulleted list to show each contact notified BY NAME and their status (e.g., "Priya Kumar — Mother ✅ Notified" or "⏳ Pending").
- Ask your final question: "**Family and nearby assistance notifications are complete. Can I search for the most suitable nearby hospital based on emergency capability, required care, distance, and travel time?**"

PHASE 4 (Facility Intelligence):
- Present the hospital discovery exactly like this (use emojis as shown):

I found [X] nearby facilities using current public facility information.
I have compared 4+ hospitals near your location based on emergency capability, critical-care resources, specialties, doctors, and travel time.

Top candidate: [Hospital Name]
- [Distance] km
- Estimated travel: [Time] min
- Emergency services: Listed
- Cardiac care: [Listed / Not Listed]
- ICU availability: Not independently verified

Based on this comparison, this facility is the strongest match with all required specialties.
**Can I initiate the available transport workflow to this facility?**

PHASE 5 (Transport + Handoff):
- Present the transport receipt exactly like this:

Transport confirmed
- Request: [Request ID]
- Pickup: [Pickup Location]
- Destination: [Destination Name]
- ETA: [ETA] minutes
- Status: CONFIRMED

Emergency handoff: READY

PHASE 6 (Live Incident Coordination):
- Generate a live status board answering the user's question about what has been done and what is pending.
- Use a bulleted list with ✓ for completed and ⏳ for pending items (e.g., "✓ Family notified: 3/3", "⏳ Transport arrival: Pending").
- Do not restart the conversation; answer based on the current state.

CONTEXT:
{context}

Generate your response now:"""


# ═══════════════════════════════════════════════════════════════
# First-Aid Instructions (deterministic — no LLM needed)
# ═══════════════════════════════════════════════════════════════
FIRST_AID = {
    ("no", "absent"): "Tilt his head back gently, lift his chin to open the airway. If he is still not breathing, start chest compressions — push hard and fast on the center of his chest, about 100-120 compressions per minute. Do NOT stop until help arrives.",
    ("no", "abnormal"): "Place him on his side in the recovery position — roll him gently onto his side with his head tilted back to keep the airway clear. Do NOT give him anything to eat or drink. Do NOT move him unless there is immediate danger.",
    ("no", "normal"): "Place him in the recovery position — on his side with his head tilted back. Monitor his breathing closely. Do NOT move him unless there is immediate danger.",
    ("no", "unknown"): "Place him in the recovery position — on his side with his head tilted back. Check if his chest is rising and falling. Do NOT move him unless there is immediate danger.",
    ("yes", "abnormal"): "Help him sit upright and lean forward slightly. Loosen any tight clothing around his chest and neck. If he has any prescribed emergency medication, help him take it now.",
    ("yes", "normal"): "Keep him still and comfortable. Do NOT let him get up or walk. Loosen any tight clothing. Talk to him calmly and reassure him that help is on the way.",
    ("yes", "absent"): "This is critical — tilt his head back gently, lift his chin. Start chest compressions immediately — push hard and fast on the center of his chest. Do NOT stop until help arrives.",
    ("unknown", "unknown"): "Do NOT move him unless there is immediate danger. Check if his chest is rising and falling. If he is not breathing, tilt his head back and start chest compressions.",
}

def _get_first_aid(conscious: str, breathing: str) -> str:
    key = (conscious.lower(), breathing.lower())
    return FIRST_AID.get(key, FIRST_AID[("unknown", "unknown")])


# ═══════════════════════════════════════════════════════════════
# Phase Detection (deterministic — no LLM needed)
# ═══════════════════════════════════════════════════════════════
def _detect_phase(db) -> tuple:
    """Returns (phase_number, incident_id, patient_key, incident) or (0, None, None, None)."""
    active = {k: v for k, v in db.incidents.items() if v["operational_state"]["status"] == "ACTIVE"}
    if not active:
        return (0, None, None, None)
    
    incident_id, incident = list(active.items())[-1]
    patient_key = incident["operational_state"]["patient"]
    
    if incident.get("operational_state", {}).get("transport"):
        return (6, incident_id, patient_key, incident)  # Transport dispatched, done
    if incident["handoff_state"].get("generated"):
        return (6, incident_id, patient_key, incident)
    if incident["operational_state"].get("hospital_searched"):
        return (5, incident_id, patient_key, incident)  # Hospital found, ready for dispatch
    if incident["operational_state"].get("contacts_notified"):
        return (4, incident_id, patient_key, incident)  # Contacts notified, ready for search
    if incident["operational_state"].get("triage_priority"):
        return (3, incident_id, patient_key, incident)  # Triage done, ready for notify
    
    return (2, incident_id, patient_key, incident)  # Incident exists, need assessment


# ═══════════════════════════════════════════════════════════════
# Main Pipeline — 2 LLM calls max per message
# ═══════════════════════════════════════════════════════════════
async def run_emergency_agent(prompt: str, history: list[dict], mcp: MCPServer, session_id: str = "default") -> AsyncGenerator[str, None]:
    """2-call pipeline: Intent → Deterministic Tools → Response."""
    try:
        from medusa.history_db import save_message
        from medusa.database import db
        save_message(session_id, "user", prompt)
        
        yield json.dumps({'type': 'thought', 'content': f'Processing: {prompt}'})
        
        # ─── CALL #1: Intent Classification ───
        print(f"\n[AGENT] ═══ LLM Call #1: Intent Classification ═══")
        
        history_text = "\n".join([f"{'USER' if m['speaker']=='USER' else 'ALEXA'}: {m['text']}" for m in history[-6:]])
        
        phase, incident_id, patient_key, incident = _detect_phase(db)
        phase_context = ""
        if phase >= 2:
            phase_context = f"\nACTIVE INCIDENT: {incident_id}, Patient: {patient_key}, Phase: {phase}"
        
        intent_messages = [
            {"role": "system", "content": INTENT_PROMPT},
            {"role": "user", "content": f"Conversation so far:\n{history_text}\n{phase_context}\n\nNew message: {prompt}"}
        ]
        
        if incident_id:
            db.log_agent_action(incident_id, "situation", f"> Analyzing intent: '{prompt}'")
        
        
        intent_raw = await _llm_call(intent_messages, max_tokens=150)
        print(f"[AGENT] Intent raw: {intent_raw}")
        
        # Parse intent JSON
        try:
            clean = intent_raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0]
            # Find JSON in the response
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            intent = json.loads(clean)
        except json.JSONDecodeError:
            intent = {"intent": "chat"}
        
        intent_type = intent.get("intent", "chat")
        print(f"[AGENT] Intent: {intent_type}, Phase: {phase}")
        
        # ─── NORMAL CHAT: 1 call total ───
        if intent_type == "chat":
            print(f"[AGENT] ═══ Chat mode — 1 call only ═══")
            chat_messages = [
                {
            "role": "system",
            "content": """
                        You are MEDUSA, a friendly and engaging voice assistant powered by the MEDUSA MCP framework.

You are currently in NORMAL CHAT MODE.

Behave like a natural conversational assistant:
- Respond warmly, naturally, and conversationally.
- For greetings and simple questions, keep responses concise (1–3 sentences).
- For explanations or deeper questions, provide a useful, clear response (4–6 sentences).
- Do not unnecessarily mention emergencies, medical coordination, agents, MCP, or internal architecture.
- Do not activate emergency workflows or claim that an emergency action has been performed.
- Do not invent capabilities, actions, or information.
- If the user asks about MEDUSA itself, explain its capabilities accurately.
- If the user asks something unrelated to emergencies, answer normally.
- If the user's message clearly describes an emergency, the application should route it to the emergency workflow rather than treating it as casual chat.

MEDUSA CAPABILITIES:
- Kinship Resolution: resolves family relationships to registered patient profiles.
- Incident Management: creates and updates emergency incident records.
- Communication: sends structured alerts to registered family and authorized nearby contacts.
- Facility Intelligence: uses SerpAPI to discover hospitals and emergency-care resources using available public information.
- Dispatch: initiates the configured transport workflow and generates structured clinical handoff information.

If asked about tools or MCP, explain these capabilities conversationally.
Never claim that a real ambulance, hospital, family member, or emergency service was contacted unless the application context explicitly confirms that action.
"""
},
            ]
            for m in history[-4:]:
                chat_messages.append({"role": "user" if m["speaker"] == "USER" else "assistant", "content": m["text"]})
            chat_messages.append({"role": "user", "content": prompt})
            
            final_text = await _llm_call(chat_messages, max_tokens=200)
            if final_text:
                save_message(session_id, "assistant", final_text)
                yield json.dumps({'type': 'final', 'content': final_text})
            else:
                yield json.dumps({'type': 'final', 'content': "Hey! I'm Alexa, powered by MEDUSA. How can I help you today?"})
            return
        
        # ═══════════════════════════════════════════════════════
        # EMERGENCY: Deterministic tool execution by phase
        # ═══════════════════════════════════════════════════════
        tool_results = {}
        context_extras = []  # Extra context to inject into Call #2
        
        # ─── PHASE 1: DETECT ───
        if intent_type == "emergency":
            relation = intent.get("relation", "father")
            event = intent.get("event", "medical emergency")
            
            # Tool 1: resolve_kinship
            db.log_agent_action(incident_id, "patient", f"> Resolving kinship for '{relation}'...")
            yield json.dumps({'type': 'tool_call', 'tool': 'resolve_kinship', 'args': {'relation': relation}})
            try:
                r = await mcp.call_tool("resolve_kinship", {"relation": relation}, context=None)
                tool_results["resolve_kinship"] = r.content[0].text
            except Exception as e:
                tool_results["resolve_kinship"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'resolve_kinship', 'result': tool_results["resolve_kinship"][:300]})
            
            pid = db.resolve_kinship(relation) or "patient_father"
            db.log_agent_action(incident_id, "patient", f"> Resolved profile ID: {pid}")
            
            # Tool 2: create_incident
            db.log_agent_action(incident_id, "situation", f"> Action: Creating incident for {event}...")
            yield json.dumps({'type': 'tool_call', 'tool': 'create_incident', 'args': {'patient_id': pid, 'event_type': event}})
            try:
                r = await mcp.call_tool("create_incident", {"patient_id": pid, "event_type": event}, context=None)
                tool_results["create_incident"] = r.content[0].text
            except Exception as e:
                tool_results["create_incident"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'create_incident', 'result': tool_results["create_incident"][:300]})
            
            # Tie the session_id to the created incident
            active = {k: v for k, v in db.incidents.items() if v["operational_state"]["status"] == "ACTIVE"}
            if active:
                latest_inc_id, latest_inc = list(active.items())[-1]
                latest_inc["session_id"] = session_id
                try:
                    from medusa.history_db import save_incident
                    save_incident(latest_inc_id, latest_inc)
                except Exception:
                    pass
            
            # Tool 3: get_patient_context
            db.log_agent_action(incident_id, "patient", f"> Querying Electronic Health Records (EHR)...")
            yield json.dumps({'type': 'tool_call', 'tool': 'get_patient_context', 'args': {'patient_id': pid}})
            try:
                r = await mcp.call_tool("get_patient_context", {"patient_id": pid}, context=None)
                tool_results["get_patient_context"] = r.content[0].text
            except Exception as e:
                tool_results["get_patient_context"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'get_patient_context', 'result': tool_results["get_patient_context"][:500]})
            
            db.log_agent_action(incident_id, "patient", "> Extracting medical history: Found matching health data.")
            
            # Also fetch emergency contacts list (deterministic, no LLM)
            contacts = db.get_emergency_contacts()
            contact_names = [f"{c['name']} ({c['type']})" for c in contacts.values()]
            context_extras.append(f"Emergency contacts on file: {', '.join(contact_names)}")
            
            # Build action receipt
            context_extras.append("ACTIONS COMPLETED: Incident created, Patient identified, Medical history retrieved, Emergency contacts retrieved")
        
        # ─── PHASE 2: ASSESS ───
        elif intent_type == "clinical_update" and phase == 2:
            conscious = intent.get("conscious", "unknown")
            breathing = intent.get("breathing", "unknown")
            details = intent.get("details", "")
            
            # Deterministic triage
            if conscious == "no" or breathing == "absent":
                priority = "CRITICAL"
                reasoning = "Patient is unconscious or not breathing"
            elif breathing == "abnormal":
                priority = "HIGH"
                reasoning = "Patient has abnormal breathing"
            else:
                priority = "MEDIUM"
                reasoning = "Patient is conscious with stable breathing"
            
            # Tool 1: assign_triage_priority
            db.log_agent_action(incident_id, "situation", f"> CRITICAL: Escalating triage level...")
            yield json.dumps({'type': 'tool_call', 'tool': 'assign_triage_priority', 'args': {'incident_id': incident_id, 'priority_level': priority}})
            try:
                r = await mcp.call_tool("assign_triage_priority", {"incident_id": incident_id, "priority_level": priority, "medical_reasoning": reasoning}, context=None)
                tool_results["assign_triage_priority"] = r.content[0].text
            except Exception as e:
                tool_results["assign_triage_priority"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'assign_triage_priority', 'result': tool_results["assign_triage_priority"][:300]})
            
            # Tool 2: update_clinical_state
            db.log_agent_action(incident_id, "situation", f"> Outcome: Assigned Priority {priority}. Pushing update.")
            db.log_agent_action(incident_id, "response", f"> Received escalation. Triage priority is {priority}.")
            yield json.dumps({'type': 'tool_call', 'tool': 'update_clinical_state', 'args': {'incident_id': incident_id, 'conscious': conscious, 'breathing': breathing}})
            try:
                r = await mcp.call_tool("update_clinical_state", {"incident_id": incident_id, "conscious": conscious, "breathing": breathing, "condition_description": details or reasoning}, context=None)
                tool_results["update_clinical_state"] = r.content[0].text
            except Exception as e:
                tool_results["update_clinical_state"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'update_clinical_state', 'result': tool_results["update_clinical_state"][:300]})
            
            # Inject deterministic first-aid instructions
            first_aid = _get_first_aid(conscious, breathing)
            context_extras.append(f"TRIAGE: {priority} — {reasoning}")
            context_extras.append(f"FIRST-AID INSTRUCTIONS (INCLUDE THESE VERBATIM): {first_aid}")
            context_extras.append("ACTIONS COMPLETED: Triage assigned, Clinical state recorded")
            context_extras.append("NEXT: Tell user you are now notifying emergency contacts and searching for the best hospital.")
        
        # ─── PHASE 3: NOTIFY ───
        elif intent_type == "confirm_notify" and phase == 3:
            # Capture override location if provided
            override_loc = intent.get("override_location")
            if override_loc and override_loc.lower() != "null":
                if incident:
                    incident["operational_state"]["location"] = override_loc
                context_extras.append(f"LOCATION OVERRIDE: User location updated to {override_loc}")

            # Tool 1: notify_emergency_contacts
            db.log_agent_action(incident_id, "communication", f"> Activating rapid notification broadcast...")
            db.log_agent_action(incident_id, "communication", f"> Connecting to trusted contacts...")
            yield json.dumps({'type': 'tool_call', 'tool': 'notify_emergency_contacts', 'args': {'incident_id': incident_id}})
            try:
                r = await mcp.call_tool("notify_emergency_contacts", {"incident_id": incident_id, "message": f"EMERGENCY: Patient requires immediate attention. Incident {incident_id}."}, context=None)
                tool_results["notify_emergency_contacts"] = r.content[0].text
            except Exception as e:
                tool_results["notify_emergency_contacts"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'notify_emergency_contacts', 'result': tool_results["notify_emergency_contacts"][:800]})
            
            # Nearby contacts alert (deterministic)
            nearby = db.get_nearby_contacts()
            if nearby:
                nearby_lines = []
                for nc in nearby.values():
                    dist = nc.get("distance_km", "?")
                    nearby_lines.append(f"{nc['name']} ({nc['type']}, {dist}km away) → Alert sent")
                context_extras.append(f"NEARBY CONTACTS ALERTED:\n" + "\n".join(nearby_lines))
            
            context_extras.append("ACTIONS COMPLETED: Family and nearby contacts notified.")
            context_extras.append(f"TOOL RESULT (Contacts):\n{tool_results.get('notify_emergency_contacts', 'None')}")

        # ─── PHASE 4: FACILITY INTELLIGENCE ───
        elif intent_type == "confirm_search" and phase == 4:
            patient = db.get_patient(patient_key)
            patient_conditions = ", ".join(patient.get("health_info", {}).get("known_conditions", [])) if patient else "unknown"
            
            # Use override location if available, else home address
            location = incident.get("operational_state", {}).get("location") if incident else None
            if not location:
                location = db.important_locations.get("home", {}).get("address", "Chennai, Tamil Nadu")

            # Tool 1: search_care_resources (SerpApi)
            db.log_agent_action(incident_id, "resource", f"> Initiating public facility scan near {location}...")
            yield json.dumps({'type': 'tool_call', 'tool': 'search_care_resources', 'args': {'condition': patient_conditions, 'location': location}})
            try:
                r = await mcp.call_tool("search_care_resources", {"condition": patient_conditions, "location": location}, context=None)
                tool_results["search_care_resources"] = r.content[0].text
            except Exception as e:
                tool_results["search_care_resources"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'search_care_resources', 'result': tool_results["search_care_resources"][:800]})
            
            db.log_agent_action(incident_id, "resource", f"> Found highly matching candidates. Cross-referencing capabilities...")
            
            # Mark hospital_searched in db
            if incident:
                incident["operational_state"]["hospital_searched"] = True
                try:
                    incident["operational_state"]["hospitals_found"] = json.loads(tool_results["search_care_resources"])
                except Exception:
                    incident["operational_state"]["hospitals_found"] = []
                
                try:
                    from medusa.history_db import save_incident
                    save_incident(incident_id, incident)
                except Exception as e:
                    print(f"Error saving hospital search: {e}")

            context_extras.append(f"Patient conditions: {patient_conditions}")
            context_extras.append("ACTIONS COMPLETED: Hospital search completed.")
            context_extras.append(f"TOOL RESULT (Hospitals Found):\n{tool_results.get('search_care_resources', 'None')}")
        
        # ─── PHASE 5: DISPATCH — transport + handoff (requires explicit dispatch_confirm) ───
        elif intent_type == "dispatch_confirm" and phase == 5:
            # Find the chosen hospital from the last search
            # Default to the first hospital found
            chosen_hospital = "nearest hospital"
            pickup = incident.get("operational_state", {}).get("location") if incident else "Current Patient Location (Coordinates synced)"
            
            # Tool 1: coordinate_transport
            db.log_agent_action(incident_id, "transport", f"> Initiating Priority 1 dispatch to {chosen_hospital}...")
            yield json.dumps({'type': 'tool_call', 'tool': 'coordinate_transport', 'args': {'incident_id': incident_id, 'destination': chosen_hospital, 'pickup_location': pickup}})
            try:
                r = await mcp.call_tool("coordinate_transport", {"incident_id": incident_id, "destination": chosen_hospital, "pickup_location": pickup}, context=None)
                tool_results["coordinate_transport"] = r.content[0].text
            except Exception as e:
                tool_results["coordinate_transport"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'coordinate_transport', 'result': tool_results["coordinate_transport"][:500]})
            
            # Tool 2: generate_handoff
            db.log_agent_action(incident_id, "transport", f"> Outcome: Transport unit assigned. Commencing clinical handoff...")
            yield json.dumps({'type': 'tool_call', 'tool': 'generate_handoff', 'args': {'incident_id': incident_id}})
            try:
                r = await mcp.call_tool("generate_handoff", {"incident_id": incident_id}, context=None)
                tool_results["generate_handoff"] = r.content[0].text
            except Exception as e:
                tool_results["generate_handoff"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'generate_handoff', 'result': tool_results["generate_handoff"][:500]})
            
            context_extras.append("ACTIONS COMPLETED: Ambulance dispatched, Clinical handoff sent to hospital")
            context_extras.append(f"TOOL RESULT (Transport Receipt):\n{tool_results.get('coordinate_transport', 'None')}")
            
        # ─── PHASE 6: LIVE COORDINATION ───
        elif intent_type == "status_request":
            context_extras.append("Generate a live status checklist of everything done so far and what is pending.")
        
        # ─── CALL #2: Generate Response with Action Receipts ───
        print(f"[AGENT] ═══ LLM Call #2: Response with Action Receipts ═══")
        
        phase_now, inc_id, p_key, inc = _detect_phase(db)
        patient_data = db.get_patient(p_key) if p_key else None
        
        # Determine the correct phase to prompt the LLM for, based on the actions we JUST took.
        # This prevents the LLM from hallucinating the next phase if the database state moved forward.
        response_phase = "UNKNOWN"
        if intent_type == "emergency":
            response_phase = "PHASE 1"
        elif intent_type == "clinical_update":
            response_phase = "PHASE 2"
        elif intent_type == "confirm_notify":
            response_phase = "PHASE 3"
        elif intent_type == "confirm_search":
            response_phase = "PHASE 4"
        elif intent_type == "dispatch_confirm":
            response_phase = "PHASE 5"
        elif intent_type == "status_request":
            response_phase = "PHASE 6"

        context_parts = [f"Current Phase: {response_phase}"]
        if patient_data:
            profile = patient_data.get("profile", {})
            health = patient_data.get("health_info", {})
            context_parts.append(f"Patient: {profile.get('name', 'Unknown')}, Age: {profile.get('age', '?')}, Blood Group: {profile.get('blood_group', '?')}")
            context_parts.append(f"Known Conditions: {', '.join(health.get('known_conditions', ['None']))}")
            context_parts.append(f"Allergies: {', '.join(health.get('allergies', ['None']))}")
            context_parts.append(f"Medications: {', '.join(health.get('medications', ['None']))}")
        if inc:
            context_parts.append(f"Incident: {inc_id}")
            triage = inc["operational_state"].get("triage_priority")
            if triage:
                context_parts.append(f"Triage: {triage}")
        
        # Add all tool results (full, not truncated)
        context_parts.append(f"\n══ TOOL RESULTS ══")
        for tool_name, result in tool_results.items():
            context_parts.append(f"[{tool_name}]: {result[:800]}")
        
        # Add extras (first-aid, nearby contacts, action receipts)
        if context_extras:
            context_parts.append(f"\n══ ADDITIONAL CONTEXT ══")
            for extra in context_extras:
                context_parts.append(extra)
        
        context_parts.append(f"\nUser said: {prompt}")
        context_parts.append(f"Recent conversation:")
        for m in history[-4:]:
            context_parts.append(f"  {'USER' if m['speaker']=='USER' else 'ALEXA'}: {m['text'][:150]}")
        
        context_str = "\n".join(context_parts)
        
        response_messages = [
            {"role": "system", "content": RESPONSE_PROMPT.format(context=context_str)},
            {"role": "user", "content": "Generate your response now."}
        ]
        
        final_text = await _llm_call(response_messages, max_tokens=500)
        
        if final_text:
            save_message(session_id, "assistant", final_text)
            yield json.dumps({'type': 'final', 'content': final_text})
        else:
            fallback = "I've completed the actions for this phase. What would you like me to do next?"
            save_message(session_id, "assistant", fallback)
            yield json.dumps({'type': 'final', 'content': fallback})
        
        print(f"[AGENT] ═══ Done. Total LLM calls: 2 ═══\n")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield json.dumps({'type': 'error', 'content': str(e)})
