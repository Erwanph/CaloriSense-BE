from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.database.elements.health_record import HealthRecord
from app.database.elements.intake import Intake, IntakeHistory
from app.database.elements.intent import Intent
from app.database.elements.user import User
from app.services.auth_handler import AuthHandler
from typing import List, Optional
from datetime import datetime

from app.services.database_handler import DatabaseHandler
from app.services.deepseek_handler import calculate_rdi


router = APIRouter()
auth_handler = AuthHandler()

class AuthRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register_user(auth: AuthRequest):
    success = auth_handler.register(auth.email, auth.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")
    
    return {"message": "User registered successfully."}


@router.post("/login")
def login_user(auth: AuthRequest):
    success = auth_handler.login(auth.email, auth.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return {"message": "Login successful."}

class InitializationRequest(BaseModel):
    # User
    email: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    country: str

    # Health Record
    weight: float
    height: float
    food_allergies: str
    daily_exercises: str
    daily_activities: str
    medical_record: str

    # Intent
    weight_goal: float
    general_goal: str

@router.post("/initialize")
async def initialize_user(data: InitializationRequest):
    # --- User ---
    new_user = User(
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        country=data.country
    )
    DatabaseHandler.user.append(new_user)

    # --- Health Record ---
    new_health = HealthRecord(
        email=data.email,
        weight=data.weight,
        height=data.height,
        food_allergies=data.food_allergies,
        daily_exercises=data.daily_exercises,
        daily_activities=data.daily_activities,
        medical_record=data.medical_record
    )
    DatabaseHandler.health_record.append(new_health)

    rdi = await calculate_rdi(
        data.weight,
        data.height,
        data.date_of_birth,
        data.gender,
        data.daily_activities,
        data.general_goal
    )

    # --- Intent ---
    new_intent = Intent(
        email=data.email,
        weight_goal=data.weight_goal,
        general_goal=data.general_goal,
        rdi=rdi
    )
    DatabaseHandler.intent.append(new_intent)
    DatabaseHandler.save()

    return {"message": "User, health record, intent, and intake initialized successfully."}