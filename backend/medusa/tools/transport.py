import json
import random
from datetime import datetime
from ..database import db

def register_transport_tools(mcp):
    @mcp.tool()
    def coordinate_transport(incident_id: str, destination: str, pickup_location: str = None) -> str:
        """Coordinate ambulance or emergency transport to a destination."""
        print(f"[TOOL CALLED] TRANSPORT: coordinate_transport(incident_id={incident_id}, destination={destination}, pickup_location={pickup_location})")
        incident = db.get_incident(incident_id)
        if not incident:
            return "Incident not found."
        
        # Generate structured transport receipt
        request_id = f"AMB-{random.randint(1000, 9999)}"
        eta_minutes = random.randint(8, 18)
        
        if not pickup_location:
            user_location = db.get_important_location("home")
            pickup_address = user_location["address"] if user_location else "User's current location"
        else:
            pickup_address = pickup_location
        
        receipt = {
            "request_id": request_id,
            "pickup": pickup_address,
            "destination": destination,
            "eta_minutes": eta_minutes,
            "status": "CONFIRMED",
            "dispatched_at": datetime.now().isoformat(),
            "contact": "+91 108"
        }
        
        # Record in incident
        db.record_observation(incident_id, f"Transport {request_id} dispatched to {destination}. ETA: {eta_minutes} mins.")
        incident["operational_state"]["transport"] = receipt
        
        try:
            from ..history_db import save_incident
            save_incident(incident_id, incident)
        except Exception as e:
            print(f"Error saving transport: {e}")
        
        return json.dumps(receipt, indent=2)
