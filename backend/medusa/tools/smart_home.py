import json
from datetime import datetime
from ..database import db

def register_smart_home_tools(mcp):
    @mcp.tool()
    def unlock_smart_door_for_ems(incident_id: str) -> str:
        """Unlock smart deadbolts (e.g. Ring / Zigbee locks) and illuminate porch entry lights to grant arriving first responders instant, non-destructive access."""
        print(f"[TOOL CALLED] SMART_HOME: unlock_smart_door_for_ems(incident_id={incident_id})")
        incident = db.get_incident(incident_id)
        action_receipt = {
            "action": "EMS_ACCESS_OVERRIDE",
            "front_door_lock": "UNLOCKED",
            "porch_floodlights": "ILLUMINATED_100_PERCENT",
            "access_code_beacon": "EMERGENCY_DISPATCH_BEACON_ACTIVE",
            "timestamp": datetime.now().isoformat(),
            "status": "CONFIRMED"
        }
        if incident:
            db.record_observation(incident_id, "Smart home perimeter unlocked and exterior entry illumination activated for EMS access.")
        return json.dumps(action_receipt, indent=2)

    @mcp.tool()
    def broadcast_household_intercom(message: str) -> str:
        """Broadcast an urgent voice and audio chime notification across all Amazon Echo devices in the household (Multi-Room Audio)."""
        print(f"[TOOL CALLED] SMART_HOME: broadcast_household_intercom(message='{message}')")
        receipt = {
            "broadcast_target": "ALL_ECHO_DEVICES_MULTI_ROOM",
            "audio_chime": "HIGH_PRIORITY_EMERGENCY_ALARM",
            "message_spoken": message,
            "devices_reached": ["Echo Show (Kitchen)", "Echo Dot (Master Bedroom)", "Echo Studio (Living Room)", "Echo Pop (Study)"],
            "timestamp": datetime.now().isoformat(),
            "status": "BROADCAST_DELIVERED"
        }
        return json.dumps(receipt, indent=2)

    @mcp.tool()
    def silence_ambient_appliances() -> str:
        """Automatically mute televisions, pause streaming audio, and halt robot vacuums to establish total acoustic clarity for emergency triage dialogue."""
        print("[TOOL CALLED] SMART_HOME: silence_ambient_appliances()")
        receipt = {
            "fire_tv_state": "MUTED_AND_PAUSED",
            "echo_music_stream": "PAUSED",
            "robot_vacuum": "RETURN_TO_DOCK_AND_MUTE",
            "ambient_acoustic_floor": "-18dB_OPTIMIZED_FOR_VOICE",
            "timestamp": datetime.now().isoformat(),
            "status": "ACOUSTIC_CLARITY_ESTABLISHED"
        }
        return json.dumps(receipt, indent=2)
