from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.routes import lessonplan, chatbot, homework, grading, student, admin

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

@app.get("/")
async def root():
    return {"message": "AI School Automation System Backend is running."} 