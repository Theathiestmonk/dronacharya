# AI School Automation System - Backend Server
import sys
import os

# Ensure the backend directory is in Python path for proper imports
backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")
print(f"Backend directory: {backend_dir}")

try:
    # Import the FastAPI app from app.main for production deployment
    from app.main import app
    print("✅ Successfully imported FastAPI app")

    # This allows uvicorn to find the app when running: uvicorn main:app
    print(f"✅ App imported: {app}")
    print(f"✅ App title: {getattr(app, 'title', 'No title')}")

except Exception as e:
    print(f"❌ Failed to import app: {e}")
    import traceback
    traceback.print_exc()
    # Exit with error code to fail deployment
    sys.exit(1)

# For local development - run the server when executed directly
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting local development server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
