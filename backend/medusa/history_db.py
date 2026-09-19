import json
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables (AWS credentials)
load_dotenv()

# Initialize DynamoDB Resource
region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
dynamodb = boto3.resource('dynamodb', region_name=region_name)
client = boto3.client('dynamodb', region_name=region_name)

# Table Names
CONVERSATIONS_TABLE = "MedusaConversations"
INCIDENTS_TABLE = "MedusaIncidents"
USER_DATA_TABLE = "MedusaUserData"

def _create_table_if_not_exists(table_name, key_schema, attribute_definitions):
    try:
        client.describe_table(TableName=table_name)
    except client.exceptions.ResourceNotFoundException:
        print(f"Creating DynamoDB Table: {table_name}...")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'
        )
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"Table {table_name} created successfully.")

def init_db():
    """Create DynamoDB tables if they do not exist."""
    print("Initializing DynamoDB tables...")
    
    # Conversations table
    _create_table_if_not_exists(
        CONVERSATIONS_TABLE,
        key_schema=[
            {'AttributeName': 'session_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'}
        ]
    )
    
    # Incidents table
    _create_table_if_not_exists(
        INCIDENTS_TABLE,
        key_schema=[
            {'AttributeName': 'incident_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'incident_id', 'AttributeType': 'S'}
        ]
    )

    # User Data table
    _create_table_if_not_exists(
        USER_DATA_TABLE,
        key_schema=[
            {'AttributeName': 'domain_key', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'domain_key', 'AttributeType': 'S'}
        ]
    )
    print("DynamoDB initialization complete.")

def save_message(session_id: str, role: str, content: str):
    table = dynamodb.Table(CONVERSATIONS_TABLE)
    try:
        table.put_item(
            Item={
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'role': role,
                'content': content
            }
        )
    except Exception as e:
        print(f"DynamoDB Error saving message: {e}")

def save_incident(incident_id: str, data: dict):
    table = dynamodb.Table(INCIDENTS_TABLE)
    try:
        table.put_item(
            Item={
                'incident_id': incident_id,
                'data_json': json.dumps(data),
                'timestamp': datetime.now().isoformat()
            }
        )
    except Exception as e:
        print(f"DynamoDB Error saving incident: {e}")

def get_history():
    conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
    incidents_table = dynamodb.Table(INCIDENTS_TABLE)
    
    # Scan conversations (in production, we'd query active sessions. For demo, scan all).
    try:
        response = conversations_table.scan()
        rows = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = conversations_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            rows.extend(response.get('Items', []))
    except Exception as e:
        print(f"Error scanning conversations: {e}")
        rows = []
        
    sessions = {}
    for item in rows:
        session_id = item['session_id']
        role = item['role']
        content = item['content']
        ts = item['timestamp']
        
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "created_at": ts
            }
        sessions[session_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": ts
        })
        
    # Sort messages within sessions by timestamp
    for session_id in sessions:
        sessions[session_id]["messages"].sort(key=lambda x: x["timestamp"])
        if sessions[session_id]["messages"]:
            sessions[session_id]["created_at"] = sessions[session_id]["messages"][0]["timestamp"]
        
    # Scan incidents
    try:
        response = incidents_table.scan()
        incident_rows = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = incidents_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            incident_rows.extend(response.get('Items', []))
    except Exception as e:
        print(f"Error scanning incidents: {e}")
        incident_rows = []
        
    incidents_list = []
    for item in incident_rows:
        incidents_list.append({
            "incident_id": item['incident_id'],
            "data": json.loads(item['data_json']),
            "timestamp": item.get('timestamp', '')
        })
        
    # Sort incidents newest first
    incidents_list.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Sort sessions newest first
    session_list = sorted(list(sessions.values()), key=lambda x: x["created_at"], reverse=True)
    
    return {
        "conversations": session_list,
        "incidents": incidents_list
    }

def delete_session(session_id: str):
    conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
    incidents_table = dynamodb.Table(INCIDENTS_TABLE)
    
    # 1. Delete conversation history for this session_id
    try:
        from boto3.dynamodb.conditions import Key
        response = conversations_table.query(
            KeyConditionExpression=Key('session_id').eq(session_id)
        )
        items = response.get('Items', [])
        
        if items:
            with conversations_table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'session_id': session_id,
                            'timestamp': item['timestamp']
                        }
                    )
    except Exception as e:
        print(f"Error deleting session messages: {e}")
    
    # 2. Find and delete associated incidents
    keys_to_delete = []
    try:
        response = incidents_table.scan()
        for item in response.get('Items', []):
            try:
                data = json.loads(item['data_json'])
                if data.get("session_id") == session_id:
                    inc_id = item['incident_id']
                    keys_to_delete.append(inc_id)
                    incidents_table.delete_item(Key={'incident_id': inc_id})
            except Exception:
                pass
    except Exception as e:
        print(f"Error deleting associated incidents: {e}")
    
    # 3. Remove from in-memory DB as well to prevent ghost incidents
    try:
        from medusa.database import db
        for k in keys_to_delete:
            if k in db.incidents:
                del db.incidents[k]
    except Exception as e:
        print(f"Error removing incident from memory: {e}")

def save_user_data(domain_key: str, data: dict):
    table = dynamodb.Table(USER_DATA_TABLE)
    try:
        table.put_item(
            Item={
                'domain_key': domain_key,
                'data_json': json.dumps(data),
                'timestamp': datetime.now().isoformat()
            }
        )
    except Exception as e:
        print(f"DynamoDB Error saving user data: {e}")

def load_user_data(domain_key: str):
    table = dynamodb.Table(USER_DATA_TABLE)
    try:
        response = table.get_item(Key={'domain_key': domain_key})
        item = response.get('Item')
        if item:
            return json.loads(item['data_json'])
    except Exception as e:
        print(f"DynamoDB Error loading user data: {e}")
    return None

