# AI School Automation System - Backend Server
# Ensure the backend directory is in Python path for proper imports
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import the FastAPI app from app.main for production deployment
from app.main import app

# This allows uvicorn to find the app when running: uvicorn main:app

# For local development - run the server when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
