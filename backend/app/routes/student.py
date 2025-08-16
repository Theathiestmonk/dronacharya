from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import hashlib
import os
from datetime import datetime, date
import json

from ..models.student import StudentCreate, StudentLogin, StudentResponse, StudentUpdate, StudentBase

router = APIRouter(prefix="/students", tags=["students"])

# Simple in-memory storage for demo (in production, use a proper database)
STUDENTS_FILE = "students.json"
students_db = {}

# Load existing students from file
def load_students():
    global students_db
    if os.path.exists(STUDENTS_FILE):
        try:
            with open(STUDENTS_FILE, 'r') as f:
                data = json.load(f)
                # Convert string dates back to date objects
                for student_id, student_data in data.items():
                    if 'date_of_birth' in student_data:
                        student_data['date_of_birth'] = date.fromisoformat(student_data['date_of_birth'])
                    if 'created_at' in student_data and student_data['created_at']:
                        student_data['created_at'] = date.fromisoformat(student_data['created_at'])
                students_db = data
        except Exception as e:
            print(f"Error loading students: {e}")
            students_db = {}

# Save students to file
def save_students():
    try:
        # Convert date objects to strings for JSON serialization
        data_to_save = {}
        for student_id, student_data in students_db.items():
            data_to_save[student_id] = student_data.copy()
            if 'date_of_birth' in data_to_save[student_id]:
                data_to_save[student_id]['date_of_birth'] = data_to_save[student_id]['date_of_birth'].isoformat()
            if 'created_at' in data_to_save[student_id] and data_to_save[student_id]['created_at']:
                data_to_save[student_id]['created_at'] = data_to_save[student_id]['created_at'].isoformat()
        
        with open(STUDENTS_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        print(f"Error saving students: {e}")

# Hash password
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Verify password
def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# Load students on startup
load_students()

@router.post("/register", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def register_student(student: StudentCreate):
    """Register a new student"""
    if student.student_id in students_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID already exists"
        )
    
    # Check if email already exists
    for existing_student in students_db.values():
        if existing_student['email'] == student.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create student record
    student_data = student.dict()
    student_data['password'] = hash_password(student.password)
    student_data['id'] = len(students_db) + 1
    student_data['is_active'] = True
    student_data['created_at'] = date.today()
    
    students_db[student.student_id] = student_data
    save_students()
    
    # Return student data without password
    response_data = student_data.copy()
    del response_data['password']
    return StudentResponse(**response_data)

@router.post("/login")
async def login_student(credentials: StudentLogin):
    """Login student with student ID and password"""
    if credentials.student_id not in students_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password"
        )
    
    student = students_db[credentials.student_id]
    
    if not verify_password(credentials.password, student['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password"
        )
    
    if not student['is_active']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Return student data without password
    response_data = student.copy()
    del response_data['password']
    
    return {
        "message": "Login successful",
        "student": StudentResponse(**response_data),
        "access_token": f"student_{credentials.student_id}_{datetime.now().timestamp()}"
    }

@router.get("/profile/{student_id}", response_model=StudentResponse)
async def get_student_profile(student_id: str):
    """Get student profile by student ID"""
    if student_id not in students_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    student = students_db[student_id]
    response_data = student.copy()
    del response_data['password']
    
    return StudentResponse(**response_data)

@router.put("/profile/{student_id}", response_model=StudentResponse)
async def update_student_profile(student_id: str, updates: StudentUpdate):
    """Update student profile"""
    if student_id not in students_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    student = students_db[student_id]
    
    # Update only provided fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        student[field] = value
    
    students_db[student_id] = student
    save_students()
    
    # Return updated student data without password
    response_data = student.copy()
    del response_data['password']
    
    return StudentResponse(**response_data)

@router.get("/", response_model=List[StudentResponse])
async def list_students():
    """List all students (for admin purposes)"""
    students = []
    for student in students_db.values():
        response_data = student.copy()
        del response_data['password']
        students.append(StudentResponse(**response_data))
    
    return students

@router.delete("/{student_id}")
async def delete_student(student_id: str):
    """Delete a student (for admin purposes)"""
    if student_id not in students_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    del students_db[student_id]
    save_students()
    
    return {"message": "Student deleted successfully"}
