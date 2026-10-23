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

    @mcp.tool()
    def calculate_route_traffic_delta(origin: str, destination: str) -> str:
        """Calculate differential travel time comparing civilian rush-hour traffic vs. emergency priority sirens-active transit."""
        print(f"[TOOL CALLED] TRANSPORT: calculate_route_traffic_delta(origin='{origin}', dest='{destination}')")
        standard_traffic_min = random.randint(28, 42)
        emergency_priority_min = max(9, int(standard_traffic_min * 0.45))
        delta_saved = standard_traffic_min - emergency_priority_min
        
        receipt = {
            "origin": origin,
            "destination": destination,
            "standard_civilian_traffic_duration_min": standard_traffic_min,
            "emergency_priority_transit_min": emergency_priority_min,
            "critical_minutes_saved": delta_saved,
            "golden_hour_window_preserved": True,
            "calculated_at": datetime.now().isoformat()
        }
        return json.dumps(receipt, indent=2)

    @mcp.tool()
    def request_green_corridor_signal(incident_id: str, route_corridor: str) -> str:
        """Issue an intelligent traffic signal preemption request (Emergency Green Wave) along the ambulance route."""
        print(f"[TOOL CALLED] TRANSPORT: request_green_corridor_signal(incident_id='{incident_id}', corridor='{route_corridor}')")
        incident = db.get_incident(incident_id)
        receipt = {
            "incident_id": incident_id,
            "route_corridor": route_corridor,
            "signal_preemption": "ACTIVE",
            "intersections_synchronized": 7,
            "estimated_junction_delay_reduction_percent": 68,
            "status": "GREEN_CORRIDOR_ESTABLISHED"
        }
        if incident:
            db.record_observation(incident_id, f"Smart city green corridor synchronized along {route_corridor} for ambulance transit.")
        return json.dumps(receipt, indent=2)

