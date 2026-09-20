import boto3
import os
import time
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# We initialize the clients in a safe way so it doesn't crash if AWS credentials are not set
region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
try:
    logs_client = boto3.client('logs', region_name=region_name)
    metrics_client = boto3.client('cloudwatch', region_name=region_name)
    CLOUDWATCH_ENABLED = True
except Exception as e:
    print(f"Warning: CloudWatch integration disabled due to init error: {e}")
    CLOUDWATCH_ENABLED = False

LOG_GROUP_NAME = "/medusa/emergency-logs"
LOG_STREAM_NAME = "agent-activity-stream"

def _ensure_log_stream():
    """Ensure that the Log Group and Log Stream exist."""
    if not CLOUDWATCH_ENABLED: return
    
    try:
        # Check and create Log Group
        try:
            logs_client.create_log_group(logGroupName=LOG_GROUP_NAME)
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass
            
        # Check and create Log Stream
        try:
            logs_client.create_log_stream(logGroupName=LOG_GROUP_NAME, logStreamName=LOG_STREAM_NAME)
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass
    except Exception as e:
        print(f"Error initializing CloudWatch Log Stream: {e}")

# Try to initialize the log stream once when the module loads
if CLOUDWATCH_ENABLED:
    threading.Thread(target=_ensure_log_stream, daemon=True).start()

def log_agent_activity(incident_id: str, agent_type: str, action_text: str):
    """Streams a log message to CloudWatch Logs."""
    if not CLOUDWATCH_ENABLED: return
    
    def _send_log():
        try:
            timestamp = int(round(time.time() * 1000))
            message = f"[{incident_id}] [{agent_type.upper()}] {action_text}"
            
            logs_client.put_log_events(
                logGroupName=LOG_GROUP_NAME,
                logStreamName=LOG_STREAM_NAME,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': message
                    }
                ]
            )
        except Exception as e:
            # Note: put_log_events occasionally requires sequence tokens, but boto3 handles simple streams well.
            # If it fails, it prints to local console safely.
            print(f"Failed to send CloudWatch Log: {e}")
            
    # Run in background to avoid blocking the main thread
    threading.Thread(target=_send_log, daemon=True).start()

def push_metric(metric_name: str, value: int = 1):
    """Pushes a custom metric to CloudWatch Metrics."""
    if not CLOUDWATCH_ENABLED: return
    
    def _send_metric():
        try:
            metrics_client.put_metric_data(
                Namespace='Medusa/Emergency',
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': 'Count'
                    }
                ]
            )
        except Exception as e:
            print(f"Failed to send CloudWatch Metric: {e}")
            
    # Run in background to avoid blocking
    threading.Thread(target=_send_metric, daemon=True).start()
