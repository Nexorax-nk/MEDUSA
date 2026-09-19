from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.mcpserver import MCPServer
import sys
import uvicorn
import json
import asyncio
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

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

# Register all 21 capabilities
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
                }
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
        "COMMUNICATION": [],
        "RESOURCE": [],
        "TRANSPORT": [],
        "HANDOFF": [],
        "TRIAGE": [],
        "OTHER": []
    }
    
    for t in tools:
        name = t.name
        desc = t.description
        
        # Categorize based on known capability groupings
        if name in ["create_incident", "get_incident_status", "update_incident"]:
            category = "INCIDENT"
        elif name in ["resolve_kinship", "get_patient_context", "get_emergency_contacts", "get_important_location"]:
            category = "PATIENT"
        elif name in ["notify_emergency_contacts", "notify_family", "send_incident_update"]:
            category = "COMMUNICATION"
        elif name in ["search_care_resources", "check_facility_status", "get_hospital_capacity"]:
            category = "RESOURCE"
        elif name in ["coordinate_transport", "request_transport", "get_transport_status"]:
            category = "TRANSPORT"
        elif name in ["generate_handoff"]:
            category = "HANDOFF"
        elif name in ["assign_triage_priority", "update_clinical_state", "record_observation"]:
            category = "TRIAGE"
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


# Mount the MCP SSE app onto the FastAPI app
app.mount("/mcp", mcp.sse_app)

# AWS Lambda Adapter (Mangum)
from mangum import Mangum
handler = Mangum(app)

if __name__ == "__main__":
    print("Starting MEDUSA Core with FastAPI + MCP on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
