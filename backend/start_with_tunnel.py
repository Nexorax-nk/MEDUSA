import subprocess
import time
import sys
from pyngrok import ngrok
from dotenv import load_dotenv
import os

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

def start_tunnel():
    print("🌍 Starting Public ngrok Tunnel for Alexa+...")
    
    # Check for NGROK_AUTHTOKEN in environment if needed, but it works without it for simple HTTP
    auth_token = os.getenv("NGROK_AUTHTOKEN")
    if auth_token:
        ngrok.set_auth_token(auth_token)
        
    try:
        # Open a HTTP tunnel on port 8000
        http_tunnel = ngrok.connect(8000)
        public_url = http_tunnel.public_url
        
        print("\n========================================================")
        print(f"✅ TUNNEL SUCCESSFUL!")
        print(f"🔗 YOUR PUBLIC MCP URL: {public_url}/sse")
        print("========================================================\n")
        print("Copy this URL and paste it into the Alexa Developer Console.\n")
        
    except Exception as e:
        print(f"❌ Failed to start ngrok tunnel: {e}")
        print("You may need to sign up for ngrok and add NGROK_AUTHTOKEN to your .env file.")
        sys.exit(1)

    # Start the actual MCP Server
    print("🚀 Starting MEDUSA MCP Server on localhost:8000...")
    try:
        subprocess.run([sys.executable, "server.py"], check=True)
    except KeyboardInterrupt:
        print("\nStopping server and tunnel...")
        ngrok.disconnect(public_url)
        ngrok.kill()
        
if __name__ == "__main__":
    start_tunnel()
