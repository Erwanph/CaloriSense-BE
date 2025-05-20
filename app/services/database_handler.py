from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client
import json
from typing import Any, Dict, Union, List, Optional
import time
import threading

from app.database.elements.health_record import HealthRecord
from app.database.elements.intake import Intake, IntakeHistory
from app.database.elements.session import Session
from app.database.elements.intent import Intent
from app.database.elements.user import User
from app.services.config import Config

# Load environment variables
load_dotenv()

class DatabaseHandler:
    user: list[User] = []
    intake_history: list[IntakeHistory] = []
    intent: list[Intent] = []
    health_record: list[HealthRecord] = []
    session: list[Session] = []
    
    # Supabase client instance
    _supabase = None
    
    # Caching variables
    _user_cache = {}
    _intake_history_cache = {}
    _intent_cache = {}
    _health_record_cache = {}
    _session_cache = {}
    
    # Flag to control save operations
    _save_pending = False
    _save_lock = threading.Lock()
    _last_saved = 0
    _save_interval = 10  # seconds
    
    @staticmethod
    def get_supabase():
        """Get or initialize the Supabase client"""
        if DatabaseHandler._supabase is None:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_ANON_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
            DatabaseHandler._supabase = create_client(url, key)
        return DatabaseHandler._supabase

    @staticmethod
    def init():
        print("init called")

        try:
            # Load data from Supabase
            DatabaseHandler._load_data_from_supabase()
            print("Database loaded successfully from Supabase.")
            
            # Initialize caches
            DatabaseHandler._init_caches()
        except Exception as e:
            print(f"Error loading from Supabase: {e}")
            DatabaseHandler.user = []
            DatabaseHandler.intake_history = []
            DatabaseHandler.intent = []
            DatabaseHandler.health_record = []
            DatabaseHandler.session = []
            print("Initialized empty database.")
            DatabaseHandler.save()

    @staticmethod
    def _init_caches():
        """Initialize lookup caches for faster access"""
        # Reset caches
        DatabaseHandler._user_cache = {}
        DatabaseHandler._intake_history_cache = {}
        DatabaseHandler._intent_cache = {}
        DatabaseHandler._health_record_cache = {}
        DatabaseHandler._session_cache = {}
        
        # Build caches
        for user in DatabaseHandler.user:
            DatabaseHandler._user_cache[user.email] = user
        
        for history in DatabaseHandler.intake_history:
            DatabaseHandler._intake_history_cache[history.email] = history
        
        for intent in DatabaseHandler.intent:
            DatabaseHandler._intent_cache[intent.email] = intent
        
        for record in DatabaseHandler.health_record:
            DatabaseHandler._health_record_cache[record.email] = record
        
        for session in DatabaseHandler.session:
            key = f"{session.email}_{session.date}"
            DatabaseHandler._session_cache[key] = session

    @staticmethod
    def save():
        """Save database with throttling to prevent too frequent saves"""
        current_time = time.time()
        
        with DatabaseHandler._save_lock:
            # Mark that we need to save
            DatabaseHandler._save_pending = True
            
            # Only save if enough time has passed since the last save
            if current_time - DatabaseHandler._last_saved >= DatabaseHandler._save_interval:
                DatabaseHandler._save_data_to_supabase()
                DatabaseHandler._last_saved = current_time
                DatabaseHandler._save_pending = False
                print("Database saved successfully to Supabase.")
            else:
                # Schedule a save for later if not already scheduled
                if not hasattr(DatabaseHandler, '_save_timer') or not DatabaseHandler._save_timer.is_alive():
                    delay = DatabaseHandler._save_interval - (current_time - DatabaseHandler._last_saved)
                    DatabaseHandler._save_timer = threading.Timer(delay, DatabaseHandler._delayed_save)
                    DatabaseHandler._save_timer.daemon = True
                    DatabaseHandler._save_timer.start()

    @staticmethod
    def _delayed_save():
        """Perform delayed save operation"""
        with DatabaseHandler._save_lock:
            if DatabaseHandler._save_pending:
                DatabaseHandler._save_data_to_supabase()
                DatabaseHandler._last_saved = time.time()
                DatabaseHandler._save_pending = False
                print("Delayed database save completed.")

    @staticmethod
    def _load_data_from_supabase():
        """Load all data from Supabase tables into memory"""
        supabase = DatabaseHandler.get_supabase()
        
        # Load users
        users_result = supabase.table('users').select('*').execute()
        DatabaseHandler.user = [
            User(
                email=user_data['email'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                date_of_birth=user_data.get('date_of_birth', ''),
                gender=user_data.get('gender', ''),
                country=user_data.get('country', '')
            ) for user_data in users_result.data
        ]
        
        # Load health records
        health_records_result = supabase.table('health_records').select('*').execute()
        DatabaseHandler.health_record = [
            HealthRecord(
                email=record['email'],
                weight=float(record.get('weight', 0)),
                height=float(record.get('height', 0)),
                food_allergies=record.get('food_allergies', ''),
                daily_exercises=record.get('daily_exercises', ''),
                daily_activities=record.get('daily_activities', ''),
                medical_record=record.get('medical_record', '')
            ) for record in health_records_result.data
        ]
        
        # Load intents
        intents_result = supabase.table('intents').select('*').execute()
        DatabaseHandler.intent = [
            Intent(
                email=intent['email'],
                weight_goal=float(intent.get('weight_goal', 0)),
                general_goal=intent.get('general_goal', ''),
                rdi=float(intent.get('rdi', 0))
            ) for intent in intents_result.data
        ]
        
        # Load intakes
        intakes_result = supabase.table('intakes').select('*').execute()
        
        # Group intakes by email to build intake history
        email_to_intakes = {}
        for intake_data in intakes_result.data:
            email = intake_data['email']
            if email not in email_to_intakes:
                email_to_intakes[email] = []
                
            # Convert date from string to datetime if needed
            date = intake_data['date']
            if isinstance(date, str):
                date = date
                
            # Create Intake object
            intake = Intake(
                date=date,
                protein=float(intake_data.get('protein', 0)),
                carbohydrate=float(intake_data.get('carbohydrate', 0)),
                fat=float(intake_data.get('fat', 0)),
                foods=intake_data.get('foods', [])
            )
            email_to_intakes[email].append(intake)
        
        # Create IntakeHistory objects
        DatabaseHandler.intake_history = [
            IntakeHistory(email=email, intakes=intakes)
            for email, intakes in email_to_intakes.items()
        ]
        
        # Load sessions
        sessions_result = supabase.table('sessions').select('*').execute()
        DatabaseHandler.session = []
        
        for session_data in sessions_result.data:
            session = Session(email=session_data['email'])
            session.date = datetime.fromisoformat(session_data['date']) if isinstance(session_data['date'], str) else session_data['date']
            session.messages = session_data.get('messages', [])
            DatabaseHandler.session.append(session)

    @staticmethod
    def _save_data_to_supabase():
        """Save all data from memory to Supabase tables"""
        supabase = DatabaseHandler.get_supabase()
        start_time = time.time()
        
        # Save users
        for user in DatabaseHandler.user:
            user_data = {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_of_birth': user.date_of_birth,
                'gender': user.gender,
                'country': user.country,
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if user exists
            result = supabase.table('users').select('email').eq('email', user.email).execute()
            
            if result.data and len(result.data) > 0:
                # Update existing user
                supabase.table('users').update(user_data).eq('email', user.email).execute()
            else:
                # Insert new user
                user_data['created_at'] = datetime.now().isoformat()
                supabase.table('users').insert(user_data).execute()
        
        # Save health records
        for record in DatabaseHandler.health_record:
            record_data = {
                'email': record.email,
                'weight': record.weight,
                'height': record.height,
                'food_allergies': record.food_allergies,
                'daily_exercises': record.daily_exercises,
                'daily_activities': record.daily_activities,
                'medical_record': record.medical_record,
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if record exists
            result = supabase.table('health_records').select('email').eq('email', record.email).execute()
            
            if result.data and len(result.data) > 0:
                # Update existing record
                supabase.table('health_records').update(record_data).eq('email', record.email).execute()
            else:
                # Insert new record
                record_data['created_at'] = datetime.now().isoformat()
                supabase.table('health_records').insert(record_data).execute()
        
        # Save intents
        for intent_obj in DatabaseHandler.intent:
            intent_data = {
                'email': intent_obj.email,
                'weight_goal': intent_obj.weight_goal,
                'general_goal': intent_obj.general_goal,
                'rdi': intent_obj.rdi,
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if intent exists
            result = supabase.table('intents').select('email').eq('email', intent_obj.email).execute()
            
            if result.data and len(result.data) > 0:
                # Update existing intent
                supabase.table('intents').update(intent_data).eq('email', intent_obj.email).execute()
            else:
                # Insert new intent
                intent_data['created_at'] = datetime.now().isoformat()
                supabase.table('intents').insert(intent_data).execute()
        
        # Save intakes
        for history in DatabaseHandler.intake_history:
            for intake in history.intakes:
                # Convert date to string if it's a datetime
                intake_date = intake.date
                if isinstance(intake_date, datetime):
                    intake_date = intake_date.strftime("%Y-%m-%d")
                
                intake_data = {
                    'email': history.email,
                    'date': intake_date,
                    'protein': intake.protein,
                    'carbohydrate': intake.carbohydrate,
                    'fat': intake.fat,
                    'foods': intake.foods,
                    'updated_at': datetime.now().isoformat()
                }
                
                # Check if intake exists
                result = supabase.table('intakes').select('id').eq('email', history.email).eq('date', intake_date).execute()
                
                if result.data and len(result.data) > 0:
                    # Update existing intake
                    intake_id = result.data[0]['id']
                    supabase.table('intakes').update(intake_data).eq('id', intake_id).execute()
                else:
                    # Insert new intake
                    intake_data['created_at'] = datetime.now().isoformat()
                    supabase.table('intakes').insert(intake_data).execute()
        
        # Save sessions
        for session in DatabaseHandler.session:
            session_date = session.date
            if isinstance(session_date, datetime):
                session_date = session_date.isoformat()
                
            session_data = {
                'email': session.email,
                'date': session_date,
                'messages': session.messages,
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if session exists
            result = supabase.table('sessions').select('id').eq('email', session.email).eq('date', session_date).execute()
            
            if result.data and len(result.data) > 0:
                # Update existing session
                session_id = result.data[0]['id']
                supabase.table('sessions').update(session_data).eq('id', session_id).execute()
            else:
                # Insert new session
                session_data['created_at'] = datetime.now().isoformat()
                supabase.table('sessions').insert(session_data).execute()
                
        print(f"Database save took {time.time() - start_time:.2f} seconds")

    @staticmethod
    def find_user(email: str) -> Optional[User]:
        # Check cache first
        if email in DatabaseHandler._user_cache:
            return DatabaseHandler._user_cache[email]
            
        # Fall back to list search
        for user in DatabaseHandler.user:
            if user.email == email:
                DatabaseHandler._user_cache[email] = user
                return user
        return None
    
    @staticmethod
    def find_intake_history(email: str) -> IntakeHistory:
        # Check cache first
        if email in DatabaseHandler._intake_history_cache:
            return DatabaseHandler._intake_history_cache[email]
            
        # Fall back to list search
        for history in DatabaseHandler.intake_history:
            if history.email == email:
                DatabaseHandler._intake_history_cache[email] = history
                return history
                
        # Create new if not found
        new_history = IntakeHistory(email, [])
        DatabaseHandler.intake_history.append(new_history)
        DatabaseHandler._intake_history_cache[email] = new_history
        return new_history
    
    @staticmethod
    def find_intake(email: str) -> Intake:
        today = datetime.now().date()
        intake_history = DatabaseHandler.find_intake_history(email)
        
        # Check for today's intake
        for intake in intake_history.intakes:
            intake_date = intake.date
            if isinstance(intake_date, str):
                intake_date = datetime.strptime(intake_date, "%Y-%m-%d").date()
            elif isinstance(intake_date, datetime):
                intake_date = intake_date.date()
                
            if intake_date == today:
                return intake
                
        # Create new intake for today
        new_intake = Intake(
            today.strftime("%Y-%m-%d"),
            0,  # protein
            0,  # carbohydrate
            0,  # fat
            []  # foods
        )

        intake_history.intakes.append(new_intake)
        return new_intake
    
    @staticmethod
    def find_intent(email: str) -> Optional[Intent]:
        # Check cache first
        if email in DatabaseHandler._intent_cache:
            return DatabaseHandler._intent_cache[email]
            
        # Fall back to list search
        for intent in DatabaseHandler.intent:
            if intent.email == email:
                DatabaseHandler._intent_cache[email] = intent
                return intent
        return None
    
    @staticmethod
    def find_health_record(email: str) -> Optional[HealthRecord]:
        # Check cache first
        if email in DatabaseHandler._health_record_cache:
            return DatabaseHandler._health_record_cache[email]
            
        # Fall back to list search
        for record in DatabaseHandler.health_record:
            if record.email == email:
                DatabaseHandler._health_record_cache[email] = record
                return record
        return None

    @staticmethod
    def find_session(email: str) -> Optional[Session]:
        date = datetime.now()
        cache_key = f"{email}_{date}"

        # Check cache first
        if cache_key in DatabaseHandler._session_cache:
            return DatabaseHandler._session_cache[cache_key]
            
        # Fall back to list search
        for session in DatabaseHandler.session:
            if session.email == email and session.date == date:
                DatabaseHandler._session_cache[cache_key] = session
                return session
        return None

    @staticmethod
    def save_database(filepath: str) -> None:
        """Legacy method for local file saving - redirects to Supabase saving"""
        DatabaseHandler._save_data_to_supabase()

    @staticmethod
    def load_database(filepath: str) -> None:
        """Legacy method for local file loading - redirects to Supabase loading"""
        DatabaseHandler._load_data_from_supabase()


if __name__ == "__main__":
    db_handler = DatabaseHandler()
    db_handler.init()  # This will initialize and load from Supabase