import os
import sys

# Ensure backend directory and project root are in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
for p in [backend_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.mcpserver import MCPServer
import uvicorn
import json
import asyncio
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)
load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

app = FastAPI(title="MEDUSA Command Center API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MCPServer
mcp = MCPServer("medusa-core", version="2.0.0")

# Import database
from medusa.database import db

# Import modular tools
from medusa.tools.patient import register_patient_tools
from medusa.tools.incident import register_incident_tools
from medusa.tools.situation import register_situation_tools
from medusa.tools.communication import register_communication_tools
from medusa.tools.community import register_community_tools
from medusa.tools.care import register_care_tools
from medusa.tools.transport import register_transport_tools
from medusa.tools.handoff import register_handoff_tools
from medusa.tools.operations import register_operations_tools
from medusa.tools.triage import register_triage_tools
from medusa.tools.smart_home import register_smart_home_tools

# Register all modular MCP capabilities
register_patient_tools(mcp)
register_incident_tools(mcp)
register_situation_tools(mcp)
register_communication_tools(mcp)
register_community_tools(mcp)
register_care_tools(mcp)
register_transport_tools(mcp)
register_handoff_tools(mcp)
register_operations_tools(mcp)
register_triage_tools(mcp)
register_smart_home_tools(mcp)

@app.get("/")
async def root_ping():
    return {"status": "alive"}

@app.get("/ping")
async def ping():
    return {"status": "alive"}

# REST APIs for Memory Visualizer
@app.get("/api/memory/user")
async def get_user_memory():
    return db.memory["USER_MEMORY"]

@app.get("/api/memory/patient")
async def get_patient_memory():
    return db.patients

@app.get("/api/incidents")
async def get_incidents():
    hydrated = []
    for inc_id, inc_data in db.incidents.items():
        op_state = inc_data.get("operational_state", {})
        patient_key = op_state.get("patient")
        
        patient_data = db.get_patient(patient_key) if patient_key else None
        profile = patient_data.get("profile", {}) if patient_data else {}
        
        emergency_contacts = list(db.emergency_contacts.values())
        primary_contact = emergency_contacts[0] if emergency_contacts else {"name": "Unknown", "phone": "Unknown"}
        
        events = inc_data.get("events", [])
        created_event = next((e for e in events if "Incident created" in e.get("event", "")), None)
        event_type = created_event["event"].replace("Incident created for event: ", "") if created_event else "Emergency Incident"
        
        hydrated.append({
            "id": inc_id,
            "status": op_state.get("status", "ACTIVE"),
            "severity": op_state.get("triage_priority", "PENDING"),
            "title": f"{profile.get('name', 'Unknown')} - {event_type}",
            "timestamp": events[0]["timestamp"] if events else "",
            "patient": {
                "name": profile.get("name", "Unknown"),
                "age": profile.get("age", "?"),
                "location": op_state.get("location", "Location tracking active"),
                "address": "Coordinates synced securely",
                "phone": profile.get("phone", "Unknown"),
                "relationship": profile.get("relationship", "Unknown"),
                "emergencyContact": primary_contact["name"]
            },
            "situation": {
                "reported": event_type,
                "conscious": op_state.get("conscious", "Unknown"),
                "breathing": op_state.get("breathing", "Unknown"),
                "confidence": "High"
            },
            "pipeline": {
                "created": True,
                "assessed": bool(op_state.get("triage_priority")),
                "patientRetrieved": bool(patient_data),
                "workflowStarted": True,
                "familyNotified": bool(op_state.get("contacts_notified")),
                "resourcesDiscovered": bool(op_state.get("hospital_searched")),
                "transportRequested": bool(op_state.get("transport")),
                "handoffGenerated": bool(inc_data.get("handoff_state", {}).get("generated"))
            },
            "widgets": {
                "contacts": db.emergency_contacts,
                "hospitals": op_state.get("hospitals_found", []),
                "transport": op_state.get("transport", None),
                "handoff": {
                    "generated": inc_data.get("handoff_state", {}).get("generated", False),
                    "document": inc_data.get("handoff_state", {}).get("document", db.handoffs.get(inc_id, None))
                },
                "last_call": op_state.get("last_call", None)
            },
            "agent_logs": inc_data.get("agent_logs", {})
        })
    return sorted(hydrated, key=lambda x: x["timestamp"], reverse=True)

@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    return db.get_incident(incident_id)

from medusa.agent import run_emergency_agent
from medusa.history_db import init_db, get_history, delete_session

# Initialize SQLite history database
init_db()

@app.get("/api/history")
async def fetch_history():
    return get_history()

@app.delete("/api/history/{session_id}")
async def remove_session(session_id: str):
    delete_session(session_id)
    return {"status": "success"}

@app.get("/api/mcp/tools")
async def get_mcp_tools():
    try:
        tools = mcp._tool_manager.list_tools()
    except Exception:
        tools = []
        
    registry = {
        "INCIDENT": [],
        "PATIENT": [],
        "TRIAGE": [],
        "RESOURCE": [],
        "TRANSPORT": [],
        "COMMUNICATION": [],
        "COMMUNITY": [],
        "SMART_HOME": [],
        "HANDOFF": [],
        "OPERATIONS": [],
        "OTHER": []
    }
    
    for t in tools:
        name = t.name
        desc = t.description
        
        # Categorize based on capability groupings
        if name in ["create_incident", "get_incident_status", "update_incident", "get_incident_timeline", "close_incident", "update_clinical_state"]:
            category = "INCIDENT"
        elif name in ["resolve_kinship", "get_patient_context", "get_emergency_contacts", "get_important_location", "analyze_drug_interactions"]:
            category = "PATIENT"
        elif name in ["assign_triage_priority", "calculate_gcs_score", "stream_biometric_vitals", "record_observation"]:
            category = "TRIAGE"
        elif name in ["search_care_resources", "recommend_care_resource", "verify_cath_lab_availability", "query_trauma_blood_inventory", "reserve_emergency_bed"]:
            category = "RESOURCE"
        elif name in ["coordinate_transport", "request_transport", "get_transport_status", "calculate_route_traffic_delta", "request_green_corridor_signal"]:
            category = "TRANSPORT"
        elif name in ["notify_emergency_contacts", "notify_family", "send_incident_update", "trigger_voice_call", "get_notification_status"]:
            category = "COMMUNICATION"
        elif name in ["find_nearby_helpers", "request_helper_assistance", "get_helper_status"]:
            category = "COMMUNITY"
        elif name in ["unlock_smart_door_for_ems", "broadcast_household_intercom", "silence_ambient_appliances"]:
            category = "SMART_HOME"
        elif name in ["generate_handoff", "get_handoff", "share_handoff", "export_handoff", "export_audit_telemetry"]:
            category = "HANDOFF"
        elif name in ["get_incident_activity"]:
            category = "OPERATIONS"
        else:
            category = "OTHER"
            
        registry[category].append({
            "name": name,
            "desc": desc or "No description provided."
        })
        
    # Remove empty categories
    registry = {k: v for k, v in registry.items() if len(v) > 0}
    return registry

@app.post("/api/trigger-emergency")
async def trigger_emergency(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    history = data.get("history", [])
    session_id = data.get("session_id", "default")
    return EventSourceResponse(run_emergency_agent(prompt, history, mcp, session_id))


@app.post("/api/emergency/call")
async def trigger_emergency_call(request: Request):
    data = await request.json()
    incident_id = data.get("incident_id")
    phone_number = data.get("phone_number")
    message = data.get("message")
    from medusa.tools.communication import place_phone_call
    result = place_phone_call(incident_id, target_phone=phone_number, message_override=message)
    return result


@app.get("/api/emergency/call-status")
async def get_emergency_call_status():
    from medusa.database import db
    active = {k: v for k, v in db.incidents.items() if v["operational_state"].get("status") == "ACTIVE"}
    if active:
        inc = list(active.values())[-1]
        return inc.get("operational_state", {}).get("last_call", {"status": "NO_CALL_YET"})
    return {"status": "NO_ACTIVE_INCIDENT"}


# Mount the MCP SSE app onto the FastAPI app
app.mount("/mcp", mcp.sse_app)

# AWS Lambda Adapter (Mangum) - Obsolete after pivot to Render
# from mangum import Mangum
# handler = Mangum(app)

if __name__ == "__main__":
    print("Starting MEDUSA Core with FastAPI + MCP on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
