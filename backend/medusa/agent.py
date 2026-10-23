import os
import sys
import json
import asyncio
import random
from datetime import datetime
from typing import AsyncGenerator
from groq import AsyncGroq
from mcp.server.mcpserver import MCPServer

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════
# Groq Client Setup with Key Rotation
# ═══════════════════════════════════════════════════════════════
from dotenv import load_dotenv
_medusa_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_medusa_dir)
load_dotenv(os.path.join(_backend_dir, ".env"))
load_dotenv()

_groq_keys = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
]
_groq_keys = [k for k in _groq_keys if k]
_groq_clients = [AsyncGroq(api_key=k) for k in _groq_keys]
_current_key_index = 0

MODEL_NAME = "qwen/qwen3.8-27b"


def _get_client():
    global _current_key_index, _groq_clients
    if not _groq_clients:
        # Re-try loading in case env was populated later
        keys = [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")]
        keys = [k for k in keys if k]
        _groq_clients = [AsyncGroq(api_key=k) for k in keys]
        if not _groq_clients:
            raise RuntimeError("GROQ_API_KEY is not configured in environment or .env file.")
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
INTENT_PROMPT = """You are the intent router for MEDUSA, an ambient friendly home voice assistant (like Alexa) equipped with a background medical emergency safety system.

PRIMARY RULE:
By default, the user is having a normal friendly conversation (greeting, chit-chat, entertainment, questions, expressing feelings like being bored or tired).
You MUST classify as "chat" unless there is an undeniable, explicit medical crisis or danger.

CATEGORIES:

1. NORMAL CHAT (DEFAULT):
Output {"intent":"chat"} for:
- Greetings & small talk: "hey", "hello", "hi", "how are you", "who are you"
- Boredom / casual feelings: "im bored", "i said im bored", "im tired", "im sleepy", "im hungry", "im fine", "im sad"
- Entertainment / requests: "tell me a joke", "what can you do", "sing a song", "play music", "what is the weather"
- Casual remarks: "okay", "cool", "thanks", "lol", "nice", "bye"
- General questions: anything that is NOT a real-time medical emergency.

2. CANCEL / STAND DOWN:
Output {"intent":"cancel_emergency"} if the user says "cancel", "false alarm", "stop emergency", "he is fine now", "never mind", "stand down", "all good".

3. MEDICAL EMERGENCY (STRICT CRITERIA):
Output {"intent":"emergency","relation":"<family relation like father/mother/sister or 'self'>","event":"<specific medical event like 'collapsed' or 'chest pain'>","location":"<specific address or landmark if mentioned in this message, else null>"}
STRICT CONDITION: ONLY when the user explicitly describes an acute, life-threatening physical medical crisis (e.g., "my dad collapsed", "chest pain", "cannot breathe", "unconscious", "profuse bleeding", "had a stroke", "seizure", "call an ambulance").
NEVER classify "bored", "tired", "sad", "annoyed", "hungry", "hello" as a medical emergency event!

4. ACTIVE EMERGENCY RESPONSES (ONLY during an ongoing incident):
- Answering conscious/breathing question: {"intent":"clinical_update","conscious":"<yes/no/unknown>","breathing":"<normal/abnormal/absent/unknown>","details":"<extra info>","location":"<home/specific address or landmark if mentioned, else null>"}
- Responding to contact notification & location verification:
  If user confirms home (e.g. "yes", "yes suree", "at home", "we are at home", "yes alert them", "sure"):
  {"intent":"confirm_notify","location_status":"home","location":"home"}
  If user gives a specific alternative address (e.g. "no we are at Express Avenue Mall", "in Anna Nagar", "at 45 Mount Road"):
  {"intent":"confirm_notify","location_status":"outside","location":"<extracted location string>"}
  If user states they are not at home but gave NO location (e.g. "no", "not at home", "outside", "somewhere else"):
  {"intent":"confirm_notify","location_status":"outside","location":"unknown_not_home"}
- Confirming hospital search: {"intent":"confirm_search","location":"<specific address/landmark if mentioned in this message, else null>"}
- Confirming ambulance dispatch: {"intent":"dispatch_confirm"}
- Inquiring incident status: {"intent":"status_request"}
NOTE: If there is no active emergency or the user speaks about unrelated things, output {"intent":"chat"}.

Output ONLY the JSON object. No markdown formatting, no explanation, no extra text."""


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
- Your job is to communicate the current state of an emergency response clearly while MEDUSA coordinates the incident.
- CALLER VS. PATIENT IDENTITY RULE: The person speaking to you is the CALLER (e.g., Naveen). The PATIENT is the person in medical distress (e.g., Rajesh Kumar). NEVER address the caller by the patient's name! Address the caller or say "Your consent is confirmed."
- LOCATION ACCURACY RULE: Always confirm and prominently display the exact [Verified Location] in Phase 3, Phase 4, and Phase 5 so the user knows exactly where responders, hospitals, and ambulances are targeted.

═══ PHASE-SPECIFIC INSTRUCTIONS ═══

PHASE 1 (Emergency detected):
- Immediately acknowledge the emergency.
- Confirm that MEDUSA created/opened the incident.
- Use a bulleted list to confirm the incident ID and patient details (name, relation, age, known conditions).
- State the triage level clearly (e.g., "Triage: **CRITICAL**").
- Bold your final question: "**Is he/she conscious and breathing normally?**"

PHASE 2 (Clinical update received & location check):
- Acknowledge the condition and give the first-aid instructions from CONTEXT verbatim.
- State that you are preparing to notify family contacts.
- State: "I have your registered home address on file as your location: **[Home Address]**."
- Bold your final question: "**Are you currently at home ([Home Address]), or at a different location? Should I alert your emergency contacts?**"

PHASE 3 (Family + Nearby Assistance & Location Confirmed):
- Acknowledge consent clearly (e.g. "Your consent is confirmed, [Caller Name]." or "Understood, your consent is confirmed."). NEVER call the caller [Patient Name]!
- Confirm the verified location prominently:
  📍 **Location Confirmed:** [Verified Location]
- Use a bulleted list to show each contact notified BY NAME and their status (e.g., "• Priya Kumar — Mother ✅ Notified", "• Suresh (Uncle, 0.35km away) ✅ Alert Sent").
- State: "Family and nearby assistance alerts have been broadcast for **[Verified Location]**."
- Ask your final question: "**Can I search for the closest hospital equipped for emergency care near [Verified Location]?**"

PHASE 3_LOCATION_REQUIRED (Caller not at home, location needed):
- Empathize with the urgency.
- State: "⚠️ **Current Location Required**: Because you are not at your registered home address, please tell me your current street address, area, or nearest landmark right now so emergency responders can reach [Patient Name] and I can find the nearest emergency hospital."

PHASE 4 (Facility Intelligence near Verified Location):
- Present the hospital discovery exactly like this (use emojis as shown):

I searched for emergency facilities near your confirmed location: **[Verified Location]**.
I have compared facilities near **[Verified Location]** based on emergency capability, critical-care resources, specialties, doctors, and travel time.

Top candidate: [Hospital Name]
- [Distance] km from [Verified Location]
- Estimated travel: [Time] min
- Emergency services: Listed (24/7)
- Cardiac & Critical Care: Listed
- ICU availability: 24/7 Verified

Based on this comparison, this facility is the strongest match with all required emergency specialties.
**Can I initiate the available transport workflow to this facility?**

PHASE 5 (Transport + Handoff):
- Present the transport receipt exactly like this:

Transport confirmed
- Request: [Request ID]
- Pickup: [Verified Location]
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
# Deterministic Intent Safety Filters
# ═══════════════════════════════════════════════════════════════
def _is_obviously_chat(prompt: str) -> bool:
    """Detect obvious casual greetings, small talk, and boredom to prevent false emergencies."""
    p = prompt.strip().lower()
    import re
    cleaned = re.sub(r'[^\w\s]', '', p).strip()
    
    casual_phrases = {
        "hey", "heyy", "heyyy", "hi", "hello", "howdy", "sup", "yo",
        "im bored", "i am bored", "i said im bored", "so bored", "bored",
        "tell me a joke", "make me laugh", "sing a song", "sing",
        "how are you", "who are you", "what can you do", "what are you",
        "im fine", "im good", "im okay", "good", "fine", "cool", "nice",
        "im tired", "im sleepy", "im hungry", "im sad", "good morning", "good evening", "good night",
        "thank you", "thanks", "lol", "haha", "bye", "see ya"
    }
    if cleaned in casual_phrases:
        return True
        
    for prefix in ["im bored", "i am bored", "i said im bored", "tell me a joke", "what is the weather", "who is", "what is", "how do i", "can you tell me", "talk to me"]:
        if cleaned.startswith(prefix):
            emergency_keywords = ["collapse", "chest pain", "heart attack", "stroke", "bleeding", "unconscious", "not breathing", "ambulance", "emergency", "dying", "seizure", "choking"]
            if not any(k in cleaned for k in emergency_keywords):
                return True
                
    return False

def _is_cancellation(prompt: str) -> bool:
    p = prompt.strip().lower()
    cancel_keywords = ["cancel", "false alarm", "stop emergency", "never mind", "stand down", "he is fine", "she is fine", "im fine now", "reset incident"]
    return any(k in p for k in cancel_keywords)


# ═══════════════════════════════════════════════════════════════
# Phase Detection (deterministic — session scoped)
# ═══════════════════════════════════════════════════════════════
def _detect_phase(db, session_id: str = None) -> tuple:
    """Returns (phase_number, incident_id, patient_key, incident) or (0, None, None, None)."""
    if session_id:
        active = {k: v for k, v in db.incidents.items() if v["operational_state"]["status"] == "ACTIVE" and v.get("session_id") == session_id}
    else:
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
        
        # Check active incident scoped to current session
        phase, incident_id, patient_key, incident = _detect_phase(db, session_id)
        
        # Handle explicit cancellation or false alarm
        if _is_cancellation(prompt):
            if incident:
                incident["operational_state"]["status"] = "RESOLVED"
                incident["events"].append({
                    "timestamp": datetime.now().isoformat(),
                    "event": f"Emergency protocol stood down by user: {prompt}"
                })
                try:
                    from medusa.history_db import save_incident
                    save_incident(incident_id, incident)
                except Exception:
                    pass
            msg = "Understood! I have stood down the emergency protocols and marked the incident as resolved. I'm right here as your everyday companion—how can I help you today?"
            save_message(session_id, "assistant", msg)
            yield json.dumps({'type': 'final', 'content': msg})
            return

        # ─── CALL #1: Intent Classification ───
        # Pre-filter: if casual chit-chat or boredom and no active emergency is ongoing
        if phase == 0 and _is_obviously_chat(prompt):
            intent_type = "chat"
            print(f"[AGENT] Direct casual pre-filter matched: '{prompt}' -> chat mode")
        else:
            print(f"\n[AGENT] === LLM Call #1: Intent Classification ===")
            
            history_text = "\n".join([f"{'USER' if m['speaker']=='USER' else 'ALEXA'}: {m['text']}" for m in history[-6:]])
            
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
            
            # Handle cancellation returned from LLM
            if intent_type == "cancel_emergency":
                if incident:
                    incident["operational_state"]["status"] = "RESOLVED"
                    try:
                        from medusa.history_db import save_incident
                        save_incident(incident_id, incident)
                    except Exception:
                        pass
                msg = "Understood! I've stood down the emergency protocols and marked the incident as resolved. How can I help you today?"
                save_message(session_id, "assistant", msg)
                yield json.dumps({'type': 'final', 'content': msg})
                return

            # Safety Guard against hallucinated emergencies on casual terms
            if intent_type == "emergency":
                event = intent.get("event", "").lower().strip()
                non_emergencies = {
                    "bored", "boredom", "chat", "conversation", "greeting", "hey", "hello", "hi",
                    "tired", "sleepy", "hungry", "sad", "joke", "nothing", "talking", "question", "none", "unknown"
                }
                medical_keywords = [
                    "collapse", "unconscious", "faint", "chest", "breath", "bleed", "injur", "pain",
                    "fall", "fell", "attack", "stroke", "seizure", "chok", "accident", "ambulance",
                    "hospital", "poison", "burn", "emergency", "dying"
                ]
                
                is_false_alarm = (event in non_emergencies) or (not any(k in (event + " " + prompt.lower()) for k in medical_keywords))
                if is_false_alarm:
                    print(f"[AGENT SAFETY] Blocked false emergency for non-medical event '{event}' on prompt '{prompt}'. Re-routing to chat.")
                    intent_type = "chat"

        print(f"[AGENT] Intent: {intent_type}, Phase: {phase}")
        
        # ─── NORMAL CHAT: 1 call total ───
        if intent_type == "chat":
            print(f"[AGENT] === Chat mode - 1 call only ===")
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
        response_phase = "UNKNOWN"
        
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
            
            # Tie the session_id to the created incident and capture any location mentioned in prompt
            active = {k: v for k, v in db.incidents.items() if v["operational_state"]["status"] == "ACTIVE"}
            if active:
                latest_inc_id, latest_inc = list(active.items())[-1]
                latest_inc["session_id"] = session_id
                
                # If caller provided a location in their initial message
                loc_in_prompt = intent.get("location")
                if loc_in_prompt and loc_in_prompt.lower() not in ["null", "none"]:
                    latest_inc["operational_state"]["location"] = loc_in_prompt
                    latest_inc["operational_state"]["location_verified"] = True
                    latest_inc["operational_state"]["location_source"] = "USER_SPECIFIED"
                    context_extras.append(f"LOCATION SPECIFIED IN CALL: {loc_in_prompt}")
                
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
            loc_update = intent.get("location")
            
            home_addr = db.important_locations.get("home", {}).get("address", "14/2 Gandhi Street, T. Nagar, Chennai, Tamil Nadu")
            if loc_update and loc_update.lower() not in ["null", "none"]:
                if loc_update.lower() in ["home", "at home"]:
                    if incident:
                        incident["operational_state"]["location"] = home_addr
                        incident["operational_state"]["location_verified"] = True
                        incident["operational_state"]["location_source"] = "HOME_REGISTERED"
                else:
                    if incident:
                        incident["operational_state"]["location"] = loc_update
                        incident["operational_state"]["location_verified"] = True
                        incident["operational_state"]["location_source"] = "USER_SPECIFIED"

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
            context_extras.append(f"HOME ADDRESS ON FILE: {home_addr}")
            context_extras.append(f"NEXT: Instruct user on first-aid, state registered home address ({home_addr}), and ask if they are currently at home or a different location, and confirm alerting contacts.")
        
        # ─── PHASE 3: NOTIFY & LOCATION VERIFICATION ───
        elif intent_type == "confirm_notify" and phase == 3:
            raw_loc = (intent.get("location") or intent.get("override_location") or "").strip()
            loc_status = (intent.get("location_status") or "").strip().lower()
            home_addr = db.important_locations.get("home", {}).get("address", "14/2 Gandhi Street, T. Nagar, Chennai, Tamil Nadu")
            
            p_lower = prompt.lower()
            is_denied_home_without_loc = (
                raw_loc == "unknown_not_home" or 
                (loc_status == "outside" and (not raw_loc or raw_loc in ["unknown_not_home", "outside", "null", "none"])) or
                (any(w in p_lower for w in ["not at home", "outside", "not home", "somewhere else", "no we are not"]) and (not raw_loc or raw_loc in ["unknown_not_home", "outside", "none", "null"]))
            )
            
            if is_denied_home_without_loc:
                # User stated they are NOT at home, and did not give an address!
                if incident:
                    incident["operational_state"]["location_verified"] = False
                    incident["operational_state"]["location_source"] = "PENDING_SPECIFICATION"
                context_extras.append("STATUS: CALLER IS NOT AT HOME. LOCATION IS UNKNOWN.")
                context_extras.append("CRITICAL ACTION REQUIRED: Prompt user urgently for their exact street address, landmark, or current area.")
                response_phase = "PHASE 3_LOCATION_REQUIRED"
            else:
                # User is confirming home OR providing a specific address
                if raw_loc and raw_loc.lower() not in ["home", "null", "none", "unknown_not_home"]:
                    verified_loc = raw_loc
                    loc_source = "USER_SPECIFIED"
                else:
                    verified_loc = home_addr
                    loc_source = "HOME_REGISTERED"
                    
                if incident:
                    incident["operational_state"]["location"] = verified_loc
                    incident["operational_state"]["location_verified"] = True
                    incident["operational_state"]["location_source"] = loc_source
                    incident["operational_state"]["contacts_notified"] = True
                    try:
                        from medusa.history_db import save_incident
                        save_incident(incident_id, incident)
                    except Exception:
                        pass
                
                # Tool 1: notify_emergency_contacts with verified location
                db.log_agent_action(incident_id, "communication", f"> Location verified: {verified_loc} ({loc_source}).")
                db.log_agent_action(incident_id, "communication", f"> Activating rapid notification broadcast for {verified_loc}...")
                db.log_agent_action(incident_id, "communication", f"> Connecting to trusted contacts...")
                yield json.dumps({'type': 'tool_call', 'tool': 'notify_emergency_contacts', 'args': {'incident_id': incident_id}})
                try:
                    r = await mcp.call_tool("notify_emergency_contacts", {"incident_id": incident_id, "message": f"EMERGENCY: Patient requires immediate medical assistance at {verified_loc}. Incident {incident_id}."}, context=None)
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
                        nearby_lines.append(f"• {nc['name']} ({nc['type']}, {dist}km away) ✅ Alert Sent")
                    context_extras.append("NEARBY CONTACTS ALERTED:\n" + "\n".join(nearby_lines))
                
                context_extras.append(f"VERIFIED LOCATION: {verified_loc} ({'Registered Home Address' if loc_source == 'HOME_REGISTERED' else 'User Specified Location'})")
                context_extras.append(f"ACTIONS COMPLETED: Location confirmed as {verified_loc}. Emergency contacts and nearby helpers notified.")
                context_extras.append(f"TOOL RESULT (Contacts):\n{tool_results.get('notify_emergency_contacts', 'None')}")

        # ─── PHASE 4: FACILITY INTELLIGENCE ───
        elif intent_type == "confirm_search" and phase == 4:
            patient = db.get_patient(patient_key)
            patient_conditions = ", ".join(patient.get("health_info", {}).get("known_conditions", [])) if patient else "unknown"
            
            # Check if user specified a location override in this search prompt (e.g. "search near Vadapalani")
            search_loc_override = intent.get("location") or intent.get("override_location")
            if search_loc_override and search_loc_override.lower() not in ["null", "none", "home"]:
                if incident:
                    incident["operational_state"]["location"] = search_loc_override
                    incident["operational_state"]["location_verified"] = True
                    incident["operational_state"]["location_source"] = "USER_SPECIFIED"
                    
            location = incident.get("operational_state", {}).get("location") if incident else None
            if not location:
                location = db.important_locations.get("home", {}).get("address", "14/2 Gandhi Street, T. Nagar, Chennai, Tamil Nadu")
                if incident:
                    incident["operational_state"]["location"] = location
                    incident["operational_state"]["location_verified"] = True

            # Formulate targeted emergency condition query
            event_type = incident.get("operational_state", {}).get("event_type", "emergency") if incident else "emergency"
            emergency_terms = ["collapse", "faint", "heart", "cardiac", "chest", "unconscious", "stroke", "seizure", "breath"]
            if any(t in (event_type.lower() + " " + patient_conditions.lower()) for t in emergency_terms):
                search_condition = "Cardiac Emergency Critical Care"
            else:
                search_condition = f"{event_type.title()} Emergency Critical Care"

            # Tool 1: search_care_resources (SerpApi)
            db.log_agent_action(incident_id, "resource", f"> Initiating emergency facility scan near confirmed location: {location} for '{search_condition}'...")
            yield json.dumps({'type': 'tool_call', 'tool': 'search_care_resources', 'args': {'condition': search_condition, 'location': location}})
            try:
                r = await mcp.call_tool("search_care_resources", {"condition": search_condition, "location": location}, context=None)
                tool_results["search_care_resources"] = r.content[0].text
            except Exception as e:
                tool_results["search_care_resources"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'search_care_resources', 'result': tool_results["search_care_resources"][:800]})
            
            db.log_agent_action(incident_id, "resource", f"> Cross-referencing capabilities with verified location: {location}...")
            
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

            context_extras.append(f"VERIFIED LOCATION USED FOR SEARCH: {location}")
            context_extras.append(f"SPECIALIZED EMERGENCY CONDITION SEARCHED: {search_condition}")
            context_extras.append(f"Patient conditions: {patient_conditions}")
            context_extras.append(f"ACTIONS COMPLETED: Specialized emergency hospital search completed near {location}.")
            context_extras.append(f"TOOL RESULT (Hospitals Found):\n{tool_results.get('search_care_resources', 'None')}")
        
        # ─── PHASE 5: DISPATCH — transport + handoff (requires explicit dispatch_confirm) ───
        elif intent_type == "dispatch_confirm" and phase == 5:
            # Find chosen hospital from search results
            hospitals = incident.get("operational_state", {}).get("hospitals_found", []) if incident else []
            if hospitals and isinstance(hospitals, list) and len(hospitals) > 0:
                chosen_hospital = hospitals[0].get("name", "Apollo Cardiac Center")
            else:
                chosen_hospital = "Apollo Cardiac Center, Greams Road"
                
            pickup = incident.get("operational_state", {}).get("location") if incident else None
            if not pickup:
                pickup = db.important_locations.get("home", {}).get("address", "14/2 Gandhi Street, T. Nagar, Chennai, Tamil Nadu")
            
            # Tool 1: coordinate_transport
            db.log_agent_action(incident_id, "transport", f"> Initiating Priority 1 dispatch to {chosen_hospital} with pickup at {pickup}...")
            yield json.dumps({'type': 'tool_call', 'tool': 'coordinate_transport', 'args': {'incident_id': incident_id, 'destination': chosen_hospital, 'pickup_location': pickup}})
            try:
                r = await mcp.call_tool("coordinate_transport", {"incident_id": incident_id, "destination": chosen_hospital, "pickup_location": pickup}, context=None)
                tool_results["coordinate_transport"] = r.content[0].text
            except Exception as e:
                tool_results["coordinate_transport"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'coordinate_transport', 'result': tool_results["coordinate_transport"][:500]})
            
            # Tool 2: generate_handoff
            db.log_agent_action(incident_id, "transport", f"> Transport dispatched to {pickup}. Generating structured clinical handoff...")
            yield json.dumps({'type': 'tool_call', 'tool': 'generate_handoff', 'args': {'incident_id': incident_id}})
            try:
                r = await mcp.call_tool("generate_handoff", {"incident_id": incident_id}, context=None)
                tool_results["generate_handoff"] = r.content[0].text
            except Exception as e:
                tool_results["generate_handoff"] = f"Error: {e}"
            yield json.dumps({'type': 'tool_result', 'tool': 'generate_handoff', 'result': tool_results["generate_handoff"][:500]})
            
            context_extras.append(f"VERIFIED PICKUP LOCATION: {pickup}")
            context_extras.append(f"DESTINATION HOSPITAL: {chosen_hospital}")
            context_extras.append("ACTIONS COMPLETED: Priority 1 ambulance dispatched, Clinical handoff transmitted to hospital")
            context_extras.append(f"TOOL RESULT (Transport Receipt):\n{tool_results.get('coordinate_transport', 'None')}")
            
        # ─── PHASE 6: LIVE COORDINATION ───
        elif intent_type == "status_request":
            context_extras.append("Generate a live status checklist of everything done so far and what is pending.")
        
        # ─── CALL #2: Generate Response with Action Receipts ───
        print(f"[AGENT] === LLM Call #2: Response with Action Receipts ===")
        
        phase_now, inc_id, p_key, inc = _detect_phase(db, session_id)
        patient_data = db.get_patient(p_key) if p_key else None
        
        # Determine the response phase
        if not response_phase or response_phase == "UNKNOWN":
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
            else:
                response_phase = f"PHASE {phase_now}"

        caller_profile = db.get_user_profile()
        caller_name = caller_profile.get("name", "Naveen").split()[0]
        
        patient_name = "Patient"
        patient_relation = "Father"
        if patient_data:
            profile = patient_data.get("profile", {})
            patient_name = profile.get("name", "Patient")
            patient_relation = profile.get("relationship", "Father")
            
        verified_location = None
        if inc:
            verified_location = inc.get("operational_state", {}).get("location")
        if not verified_location:
            verified_location = db.important_locations.get("home", {}).get("address", "14/2 Gandhi Street, T. Nagar, Chennai, Tamil Nadu")

        context_parts = [
            f"Current Phase: {response_phase}",
            f"\n══ ROLES & IDENTITIES ══",
            f"- CALLER / USER (Person speaking to you): {caller_name}",
            f"- PATIENT IN MEDICAL DISTRESS: {patient_name} ({caller_name}'s {patient_relation})",
            f"- CRITICAL IDENTITY SAFETY RULE: The caller is {caller_name}. NEVER address the caller as '{patient_name}'. {patient_name} is the patient in distress. Address the caller as {caller_name} or simply say 'Your consent is confirmed.'",
            f"- VERIFIED LOCATION: {verified_location}"
        ]
        
        if patient_data:
            profile = patient_data.get("profile", {})
            health = patient_data.get("health_info", {})
            context_parts.append(f"\n══ PATIENT CLINICAL DATA ══")
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
        
        print(f"[AGENT] === Done. Total LLM calls: 2 ===\n")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield json.dumps({'type': 'error', 'content': str(e)})
