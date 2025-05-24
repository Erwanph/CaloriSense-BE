import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any, Optional

from app.database.elements.health_record import HealthRecord
from app.database.elements.intake import IntakeHistory, Intake
from app.database.elements.intent import Intent
from app.database.elements.user import User
from app.services.database_handler import DatabaseHandler

# Load environment variables
load_dotenv()

class UserDataCache:
    """A class to store user data in memory to avoid repeated database calls"""
    _instance = None
    _cache = {}  # Using email as key
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = UserDataCache()
        return cls._instance
    
    def set_user_data(self, email: str, data: Dict[str, Any]):
        """Store user data in cache"""
        self._cache[email] = data
    
    def get_user_data(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user data from cache"""
        return self._cache.get(email)
    
    def update_user_data(self, email: str, field: str, value: Any):
        """Update a specific field in cached user data"""
        if email in self._cache:
            self._cache[email][field] = value
    
    def clear_cache(self, email: str = None):
        """Clear cache for specific user or all users"""
        if email:
            if email in self._cache:
                del self._cache[email]
        else:
            self._cache = {}

class AuthHandler:
    def __init__(self) -> None:
        self._supabase = self._initialize_supabase()
        self._cache = UserDataCache.get_instance()
    
    def _initialize_supabase(self) -> Client:
        """Initialize and return Supabase client"""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
            
        return create_client(url, key)

    def register(self, email: str, password: str) -> Dict[str, Any]:
        """Register new user using Supabase authentication"""
        try:
            response = self._supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            # Initialize database records for new user
            self._initialize_user_data(email)
            
            return {
                "status": "success",
                "data": {
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "session": response.session.access_token if response.session else None
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user using Supabase and preload user data"""
        try:
            response = self._supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # Preload user data into cache (without creating duplicates)
            self._preload_user_data(email)
            
            return {
                "status": "success",
                "data": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "user_id": response.user.id
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def _initialize_user_data(self, email: str):
        """Initialize and save user data records for new users - only creates if doesn't exist"""
        # Initialize Database
        DatabaseHandler.init()
        
        records_created = False
        
        # Create new user record if it doesn't exist
        user = DatabaseHandler.find_user(email)
        if not user:
            user = User(email=email, name="New User")
            DatabaseHandler.user.append(user)
            records_created = True
        
        # Create health record if it doesn't exist
        health_record = DatabaseHandler.find_health_record(email)
        if not health_record:
            health_record = HealthRecord(
                email=email,
                weight=0.0,
                height=0.0,
                date_of_birth="",
                gender="",
                food_allergies="",
                daily_activities="",
                medical_record=""
            )
            DatabaseHandler.health_record.append(health_record)
            records_created = True
        
        # Create intent if it doesn't exist
        intent = DatabaseHandler.find_intent(email)
        if not intent:
            intent = Intent(
                email=email,
                weight_goal=0.0,
                general_goal=""
            )
            DatabaseHandler.intent.append(intent)
            records_created = True
        
        # Create intake history if it doesn't exist
        intake_history = DatabaseHandler.find_intake_history(email)
        if not intake_history:
            intake_history = IntakeHistory(email=email, intakes=[])
            DatabaseHandler.intake_history.append(intake_history)
            records_created = True
        
        # Only save if we actually created new records
        if records_created:
            DatabaseHandler.save()
        
        # Cache data
        self._preload_user_data(email)

    def _preload_user_data(self, email: str):
        """Load user data from database into cache - doesn't create records"""
        # Initialize Database
        DatabaseHandler.init()
        
        # Load user data (without creating new records)
        user = DatabaseHandler.find_user(email)
        health_record = DatabaseHandler.find_health_record(email)
        intent = DatabaseHandler.find_intent(email)
        intake_history = DatabaseHandler.find_intake_history(email)
        intake = DatabaseHandler.find_intake(email)  # Today's intake
        
        # Store in cache
        self._cache.set_user_data(email, {
            "user": user,
            "health_record": health_record,
            "intent": intent,
            "intake_history": intake_history,
            "intake": intake
        })

    def get_user(self, access_token: str) -> Dict[str, Any]:
        """Get user data from Supabase using access token"""
        try:
            user = self._supabase.auth.get_user(access_token)
            return {
                "status": "success",
                "data": user.user.dict()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def logout(self, access_token: str) -> Dict[str, Any]:
        """Logout user session and clear cache"""
        try:
            user = self._supabase.auth.get_user(access_token)
            email = user.user.email
            
            # Clear user data from cache
            self._cache.clear_cache(email)
            
            # Sign out
            self._supabase.auth.sign_out(access_token)
            
            return {
                "status": "success",
                "message": "Logged out successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_cached_user_data(self, email: str) -> Dict[str, Any]:
        """Get cached user data for a specific user"""
        return self._cache.get_user_data(email)
    
    def update_cache_and_save(self, email: str, field: str, value: Any):
        """Update cache and save to database"""
        # Update cache
        data = self._cache.get_user_data(email)
        if data:
            # Determine which object to update based on field
            if field in ["weight", "height", "date_of_birth", "gender", "food_allergies", "daily_activities", "medical_record"]:
                data["health_record"].__setattr__(field, value)
            elif field in ["weight_goal", "general_goal"]:
                data["intent"].__setattr__(field, value)
            elif field in ["foods", "carbohydrate", "protein", "fat"]:
                data["intake"].__setattr__(field, value)
                
            # Save to database
            DatabaseHandler.save()