import os
import sys
from dotenv import load_dotenv

# Ensure backend directory and project root are in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)

for path in [backend_dir, project_root]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Explicitly load .env from backend/.env
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)
load_dotenv()

# Import the FastAPI ASGI app from server
from server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
