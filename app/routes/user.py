from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.database_handler import DatabaseHandler
from app.database.elements.user import User
from app.database.elements.health_record import HealthRecord
from app.database.elements.intent import Intent
from app.database.elements.intake import Intake, IntakeHistory

router = APIRouter()

class UserRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    country: str

@router.get("/user/{email}")
def get_user(email: str) -> dict:
    user: User | None = DatabaseHandler.find_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dir()

@router.post("/user")
def create_or_update_user(user_data: UserRequest) -> dict:
    existing_user: User | None = DatabaseHandler.find_user(user_data.email)
    if existing_user:
        existing_user.first_name = user_data.first_name
        existing_user.last_name = user_data.last_name
        existing_user.date_of_birth = user_data.date_of_birth
        existing_user.gender = user_data.gender
        existing_user.country = user_data.country
        return {"message": "User updated."}
    new_user: User = User(**user_data.dict())
    DatabaseHandler.user.append(new_user)
    DatabaseHandler.save()
    return {"message": "User created."}

class HealthRecordRequest(BaseModel):
    email: str
    weight: float
    height: float
    food_allergies: str
    daily_exercises: str
    daily_activities: str
    medical_record: str

@router.get("/health_record/{email}")
def get_health_record(email: str) -> dict:
    record: HealthRecord | None = DatabaseHandler.find_health_record(email)
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")
    return record.to_dir()

@router.post("/health_record")
def create_or_update_health_record(data: HealthRecordRequest) -> dict:
    existing: HealthRecord | None = DatabaseHandler.find_health_record(data.email)
    if existing:
        for k, v in data.dict().items():
            setattr(existing, k, v)
        return {"message": "Health record updated."}
    new_record: HealthRecord = HealthRecord(**data.dict())
    DatabaseHandler.health_record.append(new_record)
    DatabaseHandler.save()
    return {"message": "Health record created."}

class IntentRequest(BaseModel):
    email: str
    weight_goal: float
    general_goal: str
    rdi: float

@router.get("/intent/{email}")
def get_intent(email: str) -> dict:
    intent: Intent | None = DatabaseHandler.find_intent(email)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    return intent.to_dir()

@router.post("/intent")
def create_or_update_intent(data: IntentRequest) -> dict:
    existing: Intent | None = DatabaseHandler.find_intent(data.email)
    if existing:
        for k, v in data.dict().items():
            setattr(existing, k, v)
        return {"message": "Intent updated."}
    new_intent: Intent = Intent(**data.dict())
    DatabaseHandler.intent.append(new_intent)
    DatabaseHandler.save()
    return {"message": "Intent created."}

class IntakeRequest(BaseModel):
    date: str
    protein: float
    carbohydrate: float
    fat: float
    foods: List[str]

class IntakeHistoryRequest(BaseModel):
    email: str
    intakes: List[IntakeRequest]

@router.get("/intake/{email}")
def get_intake_history(email: str) -> dict:
    history: IntakeHistory | None = DatabaseHandler.find_intake_history(email)
    if not history:
        raise HTTPException(status_code=404, detail="Intake history not found")
    return history.to_dir()

@router.post("/intake")
def create_or_update_intake(data: IntakeHistoryRequest) -> dict:
    existing: IntakeHistory | None = DatabaseHandler.find_intake_history(data.email)
    intake_objs: List[Intake] = [Intake(**i.dict()) for i in data.intakes]
    if existing:
        existing.intakes = intake_objs
        return {"message": "Intake history updated."}
    new_history: IntakeHistory = IntakeHistory(email=data.email, intakes=intake_objs)
    DatabaseHandler.intake_history.append(new_history)
    DatabaseHandler.save()
    return {"message": "Intake history created."}
