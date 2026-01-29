from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from .base import Base

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Google integration data
    google_access_token = Column(Text)
    google_refresh_token = Column(Text)
    google_token_expires_at = Column(DateTime(timezone=True))
    google_classroom_enabled = Column(Boolean, default=False)
    google_calendar_enabled = Column(Boolean, default=False)
    
    # Additional admin settings
    school_name = Column(String)
    school_settings = Column(JSON)  # Store school-specific settings
    integration_settings = Column(JSON)  # Store Google integration settings

class GoogleIntegration(Base):
    __tablename__ = "google_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    service_type = Column(String, nullable=False)  # 'classroom' or 'calendar'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    scope = Column(Text, nullable=False)  # OAuth scopes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ClassroomData(Base):
    __tablename__ = "classroom_data"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    course_id = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    course_description = Column(Text)
    course_room = Column(String)
    course_section = Column(String)
    course_state = Column(String)  # ACTIVE, ARCHIVED, etc.
    teacher_email = Column(String)
    student_count = Column(Integer, default=0)
    raw_data = Column(JSON)  # Store complete course data
    last_synced = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CalendarData(Base):
    __tablename__ = "calendar_data"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    event_id = Column(String, nullable=False)
    event_title = Column(String, nullable=False)
    event_description = Column(Text)
    event_start = Column(DateTime(timezone=True), nullable=False)
    event_end = Column(DateTime(timezone=True), nullable=False)
    event_location = Column(String)
    event_attendees = Column(JSON)  # List of attendee emails
    event_status = Column(String)  # confirmed, tentative, cancelled
    calendar_id = Column(String)  # Google Calendar ID
    raw_data = Column(JSON)  # Store complete event data
    last_synced = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GoogleCloudDriveRead(Base):
    """Table for storing Google OAuth access tokens for Drive read operations (GCDR)"""
    __tablename__ = "gcdr"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String, nullable=False, index=True)  # UUID from user_profiles
    user_email = Column(String, nullable=False, index=True)  # Email of the authenticated user
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    scope = Column(Text, nullable=False)  # OAuth scopes (should include drive.readonly)
    token_type = Column(String, default="Bearer")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Additional metadata
    client_id = Column(String)  # OAuth client ID used
    project_name = Column(String, default="Prakriti Drive Test")  # Project identifier
    notes = Column(Text)  # Optional notes about this token





































