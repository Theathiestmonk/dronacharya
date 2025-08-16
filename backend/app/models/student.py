from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

class StudentBase(BaseModel):
    student_id: str = Field(..., description="Unique student ID")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    date_of_birth: date
    grade: str = Field(..., description="Current grade level")
    parent_name: str = Field(..., description="Parent/Guardian name")
    parent_phone: str = Field(..., description="Parent/Guardian phone number")
    address: str = Field(..., description="Student's address")
    emergency_contact: str = Field(..., description="Emergency contact number")

class StudentCreate(StudentBase):
    password: str = Field(..., min_length=6, description="Password for login")

class StudentLogin(BaseModel):
    student_id: str
    password: str

class StudentResponse(StudentBase):
    id: int
    is_active: bool = True
    created_at: Optional[date] = None
    
    class Config:
        from_attributes = True

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    grade: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
