import asyncio
import sys
from mcp import ClientSession
from mcp.client.sse import sse_client

sys.stdout.reconfigure(encoding='utf-8')

async def run_advanced_simulation():
    print("🎙️ Starting Advanced Alexa End-to-End Simulation...")
    
    async with sse_client("http://localhost:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            print("\n[Phase 1] 🚨 Incident Creation")
            print("⚙️ AI -> Calling resolve_kinship('father')")
            res = await session.call_tool("resolve_kinship", {"relation": "father"})
            print(f"✅ {res.content[0].text}")
            
            print("⚙️ AI -> Calling create_incident('MED-PAT-002', 'heart attack')")
            res = await session.call_tool("create_incident", {"patient_id": "MED-PAT-002", "event_type": "heart attack"})
            incident_id = res.content[0].text.split("Created: ")[1].split(".")[0]
            print(f"✅ Created Incident: {incident_id}")
            
            print("\n[Phase 2] 🏘️ Community & Care Response")
            print("⚙️ AI -> Calling find_nearby_helpers('Home', 2.0)")
            res = await session.call_tool("find_nearby_helpers", {"location": "Home", "radius_km": 2.0})
            print(f"✅ Found helpers: {res.content[0].text}")
            
            print(f"⚙️ AI -> Calling request_helper_assistance('{incident_id}', 'HELP-102')")
            res = await session.call_tool("request_helper_assistance", {"incident_id": incident_id, "helper_id": "HELP-102"})
            print(f"✅ {res.content[0].text}")
            
            print(f"⚙️ AI -> Calling recommend_care_resource('{incident_id}')")
            res = await session.call_tool("recommend_care_resource", {"incident_id": incident_id})
            print(f"✅ {res.content[0].text}")
            
            print("\n[Phase 3] 🚑 Transport & Handoff")
            print(f"⚙️ AI -> Calling coordinate_transport('{incident_id}', 'Apollo Cardiac Center')")
            res = await session.call_tool("coordinate_transport", {"incident_id": incident_id, "destination": "Apollo Cardiac Center"})
            print(f"✅ {res.content[0].text}")
            
            print(f"⚙️ AI -> Calling generate_handoff('{incident_id}')")
            res = await session.call_tool("generate_handoff", {"incident_id": incident_id})
            print(f"✅ {res.content[0].text}")
            
            print("\n[Phase 4] 📊 Command Center Observability")
            print(f"⚙️ AI -> Calling get_incident_activity('{incident_id}')")
            res = await session.call_tool("get_incident_activity", {"incident_id": incident_id})
            print(f"✅ Activity Data:\n{res.content[0].text}")
            
            print(f"⚙️ AI -> Calling get_incident_timeline('{incident_id}')")
            res = await session.call_tool("get_incident_timeline", {"incident_id": incident_id})
            print(f"✅ Timeline History:\n{res.content[0].text}")

if __name__ == "__main__":
    asyncio.run(run_advanced_simulation())
