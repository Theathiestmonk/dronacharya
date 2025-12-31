#!/usr/bin/env python3
"""
Main entry point for the AI School Automation System
This file allows Render to run the FastAPI app from the root directory
"""

# Import the FastAPI app from backend
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
