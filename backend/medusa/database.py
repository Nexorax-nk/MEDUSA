import json
from typing import Dict, Any
from datetime import datetime

class MedusaMemorySystem:
    def __init__(self):
        # MEDUSA MEMORY ROOT
        self.memory = {
            "USER_MEMORY": {
                "profile": {
                    "name": "Naveen Kumar G",
                    "age": 20,
                    "phone": "+91 XXXXX XXXXX",
                    "email": "naveen@example.com",
                    "home_address": "Chennai, Tamil Nadu",
                    "city": "Chennai"
                },
                "emergency_contacts": {
                    "1": {"name": "Priya Kumar", "phone": "+91 ZZZZZ", "type": "Mother", "priority": "Primary"},
                    "2": {"name": "Ramesh Kumar", "phone": "+91 UUUUU", "type": "Uncle", "priority": "Secondary"},
                    "3": {"name": "Dr. Sharma", "phone": "+91 AAAAA", "type": "Family Doctor", "priority": "Backup"},
                    "4": {"name": "Suresh", "phone": "+91 BBBBB", "type": "Trusted Contact", "priority": "Backup"}
                },
                "important_locations": {
                    "home": {"address": "Chennai, Tamil Nadu", "lat": 13.0827, "lng": 80.2707},
                    "college": {"address": "SRM Institute", "lat": 12.8236, "lng": 80.0435},
                    "parents_home": {"address": "Madurai", "lat": 9.9252, "lng": 78.1198}
                },
                "nearby_contacts": {
                    "1": {"name": "Suresh", "phone": "+91 BBBBB", "type": "Uncle", "distance_km": 0.35},
                    "2": {"name": "Ravi", "phone": "+91 CCCCC", "type": "Neighbor", "distance_km": 1.2},
                    "3": {"name": "Karthik", "phone": "+91 DDDDD", "type": "Family Friend", "distance_km": 2.8}
                },
                "emergency_protocol": {
                    "default_protocol": "CRITICAL-FIRST",
                    "emergency_mode": "ENABLED",
                    "auto_escalation": "ENABLED",
                    "escalation_rules": {
                        "critical_incident": "Immediate escalation",
                        "unresponsive_patient": "Immediate escalation",
                        "breathing_difficulty": "Immediate escalation",
                        "severe_injury": "Immediate escalation"
                    },
                    "communication": {
                        "primary_contact": "Father",
                        "secondary_contact": "Mother",
                        "emergency_contact": "+91 XXXXX XXXXX"
                    },
                    "location_preferences": {
                        "share_location": "On Emergency Only",
                        "location_precision": "High",
                        "keep_user_updated": "Yes",
                        "family_notification": "Critical incidents only",
                        "status_updates": "Every major state change"
                    }
                },
                "core_preferences": {
                    "response_style": "Concise / Action First",
                    "notification_level": "Strict / Critical Only",
                    "family_updates": "Enabled",
                    "location_sharing": "Emergency Only",
                    "voice_confirmation": "Required for non-critical actions",
                    "language": "English",
                    "emergency_language": "English",
                    "status_updates": "Major Events Only",
                    "ui_theme": "Cyberpunk Dark",
                    "status": "LOCKED"
                },
                "care_network": {
                    "primary_physician": {
                        "name": "Dr. S. Venkat",
                        "specialty": "General Medicine",
                        "phone": "+91 XXXXX XXXXX"
                    },
                    "preferred_facility": {
                        "facility": "Apollo Hospital, Greams Road",
                        "reason": "Previous Care / Cardiology Dept"
                    },
                    "local_support": {
                        "name": "Mr. Sharma",
                        "relation": "Neighbour",
                        "phone": "+91 XXXXX XXXXX"
                    },
                    "emergency_services": {
                        "local_emergency": "112"
                    }
                }
            },
            "PATIENT_MEMORY": {
                "father": {
                    "profile": {
                        "name": "Rajesh Kumar",
                        "relationship": "Father",
                        "age": 54,
                        "phone": "+91 YYYYY YYYYY",
                        "blood_group": "O+"
                    },
                    "health_info": {
                        "known_conditions": ["Hypertension"],
                        "allergies": ["Penicillin"],
                        "medications": ["Amlodipine"],
                        "emergency_notes": "Avoid known allergens."
                    }
                },
                "mother": {
                    "profile": {
                        "name": "Priya Kumar",
                        "relationship": "Mother",
                        "age": 49,
                        "phone": "+91 ZZZZZ",
                        "blood_group": "B+"
                    },
                    "health_info": {}
                },
                "sister": {
                    "profile": {
                        "name": "Ananya Kumar",
                        "relationship": "Sister",
                        "age": 21,
                        "phone": "+91 WWWWW"
                    },
                    "health_info": {}
                }
            },
            "INCIDENT_MEMORY": {}
        }
        
        # Operational transient states
        self.helpers: Dict[str, Any] = {
            "HELP-101": {"id": "HELP-101", "name": "Dr. Sharma", "distance_km": 1.2, "status": "AVAILABLE", "type": "MEDICAL"},
            "HELP-102": {"id": "HELP-102", "name": "Community Responder Anil", "distance_km": 0.5, "status": "AVAILABLE", "type": "FIRST_AID"}
        }
        self.handoffs: Dict[str, Any] = {}
        
        self._sync_with_db()

    def _sync_with_db(self):
        try:
            from .history_db import load_user_data, save_user_data, get_history
            
            # Load or initialize USER_MEMORY
            user_data = load_user_data("USER_MEMORY")
            if user_data:
                # Merge loaded data over the default schema to preserve new keys
                for k, v in user_data.items():
                    self.memory["USER_MEMORY"][k] = v
                save_user_data("USER_MEMORY", self.memory["USER_MEMORY"])
            else:
                save_user_data("USER_MEMORY", self.memory["USER_MEMORY"])
                
            # Load or initialize PATIENT_MEMORY
            patient_data = load_user_data("PATIENT_MEMORY")
            if patient_data:
                # Merge loaded data over the default schema
                for k, v in patient_data.items():
                    self.memory["PATIENT_MEMORY"][k] = v
                save_user_data("PATIENT_MEMORY", self.memory["PATIENT_MEMORY"])
            else:
                save_user_data("PATIENT_MEMORY", self.memory["PATIENT_MEMORY"])
                
            # Load INCIDENT_MEMORY
            history = get_history()
            if "incidents" in history:
                for inc in history["incidents"]:
                    self.memory["INCIDENT_MEMORY"][inc["incident_id"]] = inc["data"]
                
        except Exception as e:
            print(f"Error syncing with SQLite DB: {e}")

    def save_user_memory(self):
        try:
            from .history_db import save_user_data
            save_user_data("USER_MEMORY", self.memory["USER_MEMORY"])
        except Exception as e:
            print(f"Error saving USER_MEMORY: {e}")
            
    def save_patient_memory(self):
        try:
            from .history_db import save_user_data
            save_user_data("PATIENT_MEMORY", self.memory["PATIENT_MEMORY"])
        except Exception as e:
            print(f"Error saving PATIENT_MEMORY: {e}")

    # -- Convenience properties for server.py API --
    @property
    def user_profile(self):
        return self.memory["USER_MEMORY"]["profile"]
    
    @property
    def emergency_contacts(self):
        return self.memory["USER_MEMORY"]["emergency_contacts"]
    
    @property
    def important_locations(self):
        return self.memory["USER_MEMORY"]["important_locations"]
    
    @property
    def patients(self):
        return self.memory["PATIENT_MEMORY"]
    
    @property
    def incidents(self):
        return self.memory["INCIDENT_MEMORY"]

    # -- User Memory Access --
    def get_user_profile(self) -> dict:
        return self.memory["USER_MEMORY"]["profile"]

    def get_emergency_contacts(self) -> dict:
        return self.memory["USER_MEMORY"]["emergency_contacts"]

    def get_important_location(self, location_name: str) -> dict | None:
        key = location_name.lower().replace(" ", "_").replace("'", "")
        return self.memory["USER_MEMORY"]["important_locations"].get(key)

    def get_nearby_contacts(self) -> dict:
        return self.memory["USER_MEMORY"].get("nearby_contacts", {})

    # -- Patient Memory Access --
    def resolve_kinship(self, relation: str) -> str | None:
        """Returns the dictionary key in PATIENT_MEMORY if it exists"""
        clean_relation = relation.lower().replace("my ", "").strip()
        if clean_relation in self.memory["PATIENT_MEMORY"]:
            return clean_relation
        return None

    def get_patient(self, relation_key: str) -> dict | None:
        """Returns the full patient block (profile + health_info)"""
        return self.memory["PATIENT_MEMORY"].get(relation_key)

    # -- Incident Memory Access (Dynamic scaffolding) --
    def create_incident(self, relation_key: str, event_type: str) -> str:
        incident_id = f"MED-{1000 + len(self.memory['INCIDENT_MEMORY']) + 42}"
        incident_data = {
            "conversation": [],
            "events": [
                {"timestamp": datetime.now().isoformat(), "event": f"Incident created for event: {event_type}"}
            ],
            "agent_logs": {
                "situation": [f"[{datetime.now().strftime('%H:%M:%S')}] > Initializing Situation Agent for incident {incident_id}..."],
                "patient": [f"[{datetime.now().strftime('%H:%M:%S')}] > Standby mode active."],
                "response": [f"[{datetime.now().strftime('%H:%M:%S')}] > Connected to MCP event bus. Waiting for escalation."],
                "communication": [f"[{datetime.now().strftime('%H:%M:%S')}] > Comm channels linked."],
                "resource": [f"[{datetime.now().strftime('%H:%M:%S')}] > SerpAPI initialized."],
                "transport": [f"[{datetime.now().strftime('%H:%M:%S')}] > Mock dispatch module loaded."]
            },
            "operational_state": {
                "patient": relation_key,
                "status": "ACTIVE",
                "observations": [],
                "assigned_helpers": [],
                "triage_priority": None
            },
            "handoff_state": {
                "generated": False,
                "shared_with": []
            }
        }
        self.memory["INCIDENT_MEMORY"][incident_id] = incident_data
        
        try:
            from .history_db import save_incident
            save_incident(incident_id, incident_data)
        except Exception as e:
            print(f"Error saving incident to DB: {e}")
            
        try:
            import boto3
            import json
            import os
            eb_client = boto3.client('events', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
            eb_client.put_events(
                Entries=[
                    {
                        'Source': 'medusa.emergency',
                        'DetailType': 'Emergency.Escalated',
                        'Detail': json.dumps({'incident_id': incident_id, 'event_type': event_type})
                    }
                ]
            )
        except Exception as e:
            print(f"Error emitting EventBridge event: {e}")
            
        try:
            from .cloudwatch import push_metric
            push_metric('EmergencyIncidentsCreated', 1)
        except Exception as e:
            print(f"Error emitting CloudWatch metric: {e}")
            
        return incident_id

    def get_incident(self, incident_id: str) -> dict | None:
        return self.memory["INCIDENT_MEMORY"].get(incident_id)

    def update_incident_status(self, incident_id: str, status: str) -> bool:
        incident = self.get_incident(incident_id)
        if incident:
            incident["operational_state"]["status"] = status
            incident["events"].append(
                {"timestamp": datetime.now().isoformat(), "event": f"Status changed to {status}"}
            )
            try:
                from .history_db import save_incident
                save_incident(incident_id, incident)
            except Exception:
                pass
            return True
        return False

    def record_observation(self, incident_id: str, observation: str) -> bool:
        incident = self.get_incident(incident_id)
        if incident:
            incident["operational_state"]["observations"].append(observation)
            incident["events"].append(
                {"timestamp": datetime.now().isoformat(), "event": f"Observation recorded: {observation}"}
            )
            try:
                from .history_db import save_incident
                save_incident(incident_id, incident)
            except Exception:
                pass
            return True
        return False

    def log_agent_action(self, incident_id: str, agent_type: str, action_text: str) -> bool:
        incident = self.get_incident(incident_id)
        if incident:
            if "agent_logs" not in incident:
                incident["agent_logs"] = {
                    "situation": [], "patient": [], "response": [],
                    "communication": [], "resource": [], "transport": []
                }
            if agent_type not in incident["agent_logs"]:
                incident["agent_logs"][agent_type] = []
                
            timestamp = datetime.now().strftime('%H:%M:%S')
            incident["agent_logs"][agent_type].append(f"[{timestamp}] {action_text}")
            
            try:
                from .history_db import save_incident
                save_incident(incident_id, incident)
            except Exception:
                pass
                
            try:
                from .cloudwatch import log_agent_activity
                log_agent_activity(incident_id, agent_type, action_text)
            except Exception:
                pass
                
            return True
        return False

# Global singleton
db = MedusaMemorySystem()
