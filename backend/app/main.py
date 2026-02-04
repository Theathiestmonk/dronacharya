from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.routes import lessonplan, chatbot, homework, grading, student, admin
from app.services.auto_sync_scheduler import get_auto_sync_scheduler

load_dotenv()

# Environment variables loaded (not printed for security)
# Removed debug prints to prevent exposing sensitive information in logs

app = FastAPI(title="AI School Automation System", version="1.0.0")

# CORS configuration (allow all origins for now, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(lessonplan.router, prefix="/lessonplan", tags=["Lesson Plan"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
app.include_router(homework.router, prefix="/homework", tags=["Homework"])
app.include_router(grading.router, prefix="/grading", tags=["Grading"])
app.include_router(student.router, prefix="/students", tags=["Students"])
app.include_router(admin.router, tags=["Admin"])

@app.on_event("startup")
async def startup_event():
    """Start the auto-sync scheduler on app startup"""
    try:
        scheduler = get_auto_sync_scheduler()
        scheduler.start()
        print("[App] Auto-sync scheduler started")
    except Exception as e:
        print(f"[App] Warning: Failed to start auto-sync scheduler: {e}")
        import traceback
        traceback.print_exc()
    
    # Log DWD status for production debugging
    try:
        from app.services.google_dwd_service import get_dwd_service
        dwd_service = get_dwd_service()
        if dwd_service and dwd_service.is_available():
            client_id = dwd_service._get_client_id()
            workspace_domain = dwd_service.workspace_domain
            print(f"[DWD] ✅ Service available")
            print(f"[DWD] Client ID: {client_id}")
            print(f"[DWD] Workspace Domain: {workspace_domain}")
            print(f"[DWD] ⚠️  Verify Client ID is authorized in Google Admin Console:")
            print(f"[DWD]    https://admin.google.com → Security → API Controls → Domain-wide Delegation")
        else:
            print(f"[DWD] ❌ Service not available - check GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_JSON")
    except Exception as e:
        print(f"[DWD] ⚠️  Could not check DWD status: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the auto-sync scheduler on app shutdown"""
    try:
        scheduler = get_auto_sync_scheduler()
        scheduler.stop()
        print("[App] Auto-sync scheduler stopped")
    except Exception as e:
        print(f"[App] Warning: Error stopping auto-sync scheduler: {e}")

@app.get("/")
async def root():
    return {"message": "AI School Automation System Backend is running."}

@app.get("/health")
async def health_check():
    """Health check endpoint that also shows scheduler status"""
    scheduler = get_auto_sync_scheduler()
    scheduler_status = "running" if scheduler.is_running else "stopped"
    next_run = None
    if scheduler.is_running and scheduler.scheduler.get_job('auto_sync_job'):
        next_run = scheduler.scheduler.get_job('auto_sync_job').next_run_time.isoformat() if scheduler.scheduler.get_job('auto_sync_job').next_run_time else None
    
    return {
        "status": "healthy",
        "scheduler": scheduler_status,
        "next_sync": next_run
    } 