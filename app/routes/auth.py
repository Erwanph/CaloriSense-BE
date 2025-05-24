from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
from app.database.elements.health_record import HealthRecord
from app.database.elements.intake import Intake, IntakeHistory
from app.database.elements.intent import Intent
from app.database.elements.user import User
from app.services.auth_handler import AuthHandler
from typing import List, Optional
from datetime import datetime
from fastapi.security import HTTPBearer

from app.services.database_handler import DatabaseHandler
from app.services.deepseek_handler import Deepseek

router = APIRouter()
auth_handler = AuthHandler()
security = HTTPBearer()

# Helper function untuk mendapatkan current user
async def get_current_user(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.split("Bearer ")[-1]
        user_response = auth_handler.get_user(token)
        if user_response["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return user_response["data"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

class AuthRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register_user(auth: AuthRequest):
    response = auth_handler.register(auth.email, auth.password)
    if response["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response["message"]
        )
    return {
        "message": "User registered successfully",
        "data": {
            "user_id": response["data"]["user_id"],
            "email": response["data"]["email"]
        }
    }

@router.post("/login")
async def login_user(auth: AuthRequest):
    response = auth_handler.login(auth.email, auth.password)
    if response["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=response["message"]
        )
    return {
        "message": "Login successful",
        "data": {
            "access_token": response["data"]["access_token"],
            "refresh_token": response["data"]["refresh_token"],
            "user_id": response["data"]["user_id"]
        }
    }

class InitializationRequest(BaseModel):
    # User
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
async def initialize_user(
    data: InitializationRequest,
    current_user: dict = Depends(get_current_user)
):
    email = current_user["email"]
    
    # Initialize database
    DatabaseHandler.init()
    
    # --- User: Update existing or create new ---
    existing_user = DatabaseHandler.find_user(email)
    if existing_user:
        # Update existing user
        existing_user.first_name = data.first_name
        existing_user.last_name = data.last_name
        existing_user.date_of_birth = data.date_of_birth
        existing_user.gender = data.gender
        existing_user.country = data.country
    else:
        # Create new user (shouldn't happen if auth works correctly)
        new_user = User(
            email=email,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            country=data.country
        )
        DatabaseHandler.user.append(new_user)

    # --- Health Record: Update existing or create new ---
    existing_health = DatabaseHandler.find_health_record(email)
    if existing_health:
        # Update existing health record
        existing_health.weight = data.weight
        existing_health.height = data.height
        existing_health.food_allergies = data.food_allergies
        existing_health.daily_exercises = data.daily_exercises
        existing_health.daily_activities = data.daily_activities
        existing_health.medical_record = data.medical_record
    else:
        # Create new health record
        new_health = HealthRecord(
            email=email,
            weight=data.weight,
            height=data.height,
            food_allergies=data.food_allergies,
            daily_exercises=data.daily_exercises,
            daily_activities=data.daily_activities,
            medical_record=data.medical_record
        )
        DatabaseHandler.health_record.append(new_health)

    # Calculate RDI
    rdi = await Deepseek.calculate_rdi(
        data.weight,
        data.height,
        data.date_of_birth,
        data.gender,
        data.daily_activities,
        data.general_goal
    )

    # --- Intent: Update existing or create new ---
    existing_intent = DatabaseHandler.find_intent(email)
    if existing_intent:
        # Update existing intent
        existing_intent.weight_goal = data.weight_goal
        existing_intent.general_goal = data.general_goal
        existing_intent.rdi = rdi
    else:
        # Create new intent
        new_intent = Intent(
            email=email,
            weight_goal=data.weight_goal,
            general_goal=data.general_goal,
            rdi=rdi
        )
        DatabaseHandler.intent.append(new_intent)
    
    # Save changes
    DatabaseHandler.save()

    return {"message": "User data initialized successfully"}

@router.post("/logout")
async def logout_user(current_user: dict = Depends(get_current_user)):
    response = auth_handler.logout(current_user["access_token"])
    if response["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response["message"]
        )
    return {"message": "Successfully logged out"}