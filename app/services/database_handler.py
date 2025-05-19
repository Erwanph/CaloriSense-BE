from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client
import json
from typing import Any, Dict, Union, List
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
            JSONHelper.load_database_from_supabase()
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
                JSONHelper.save_database_to_supabase()
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
                JSONHelper.save_database_to_supabase()
                DatabaseHandler._last_saved = time.time()
                DatabaseHandler._save_pending = False
                print("Delayed database save completed.")

    @staticmethod
    def find_user(email: str) -> User:
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
            if intake.date == today:
                return intake
                
        # Create new intake for today
        new_intake = Intake(
            today,
            0,
            0,
            0,
            []
        )

        intake_history.intakes.append(new_intake)
        return new_intake
    
    @staticmethod
    def find_intent(email: str) -> Intent:
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
    def find_health_record(email: str) -> HealthRecord:
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
    def find_session(email: str) -> Session:
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


class JSONHelper:
    @staticmethod
    def export_json(data: Dict[str, Any], indent: int = 2) -> str:
        return json.dumps(data, indent=indent, default=JSONHelper._default_serializer)

    @staticmethod
    def import_json(json_input: Union[str, bytes]) -> Dict[str, Any]:
        return json.loads(json_input)

    @staticmethod
    def save_database_to_supabase() -> None:
        """Save the database to Supabase"""
        start_time = time.time()
        
        data = {
            "user": [u.to_dir() for u in DatabaseHandler.user],
            "intake_history": [ih.to_dir() for ih in DatabaseHandler.intake_history],
            "intent": [i.to_dir() for i in DatabaseHandler.intent],
            "health_record": [hr.to_dir() for hr in DatabaseHandler.health_record],
            "session": [s.to_dir() for s in DatabaseHandler.session],
        }
        
        # Convert to JSON object (not string)
        json_data = data
        
        # Store data in Supabase
        supabase = DatabaseHandler.get_supabase()
        
        # Check if there's an existing record and update it, or insert a new one
        result = supabase.table('app_data').select('id').eq('name', 'main_database').execute()
        
        if result.data and len(result.data) > 0:
            # Update existing record
            record_id = result.data[0]['id']
            supabase.table('app_data').update({'data': json_data}).eq('id', record_id).execute()
        else:
            # Create new record
            supabase.table('app_data').insert({'name': 'main_database', 'data': json_data}).execute()
            
        print(f"Database save took {time.time() - start_time:.2f} seconds")

    @staticmethod
    def load_database_from_supabase() -> None:
        """Load the database from Supabase"""
        start_time = time.time()
        
        supabase = DatabaseHandler.get_supabase()
        
        # Fetch data from Supabase
        result = supabase.table('app_data').select('data').eq('name', 'main_database').execute()
        
        if not result.data or len(result.data) == 0:
            # No data found, initialize with empty database
            DatabaseHandler.user = []
            DatabaseHandler.intake_history = []
            DatabaseHandler.intent = []
            DatabaseHandler.health_record = []
            DatabaseHandler.session = []
            return
        
        # Data is already in JSON format
        data = result.data[0]['data']
        
        # Load data into the DatabaseHandler
        DatabaseHandler.user = [User(**u) for u in data.get("user", [])]

        DatabaseHandler.intake_history = [
            IntakeHistory(
                email=ih["email"],
                intakes=[
                    Intake(
                        **{**i, "date": datetime.fromisoformat(i["date"])}
                    ) for i in ih.get("intakes", [])
                ]
            ) for ih in data.get("intake_history", [])
        ]

        DatabaseHandler.intent = [Intent(**i) for i in data.get("intent", [])]
        DatabaseHandler.health_record = [HealthRecord(**hr) for hr in data.get("health_record", [])]
        DatabaseHandler.session = [
            JSONHelper._load_session(s) for s in data.get("session", [])
        ]
        
        print(f"Database load took {time.time() - start_time:.2f} seconds")

    @staticmethod
    def save_database(filepath: str) -> None:
        """Legacy method for local file saving - redirects to Supabase saving"""
        JSONHelper.save_database_to_supabase()

    @staticmethod
    def load_database(filepath: str) -> None:
        """Legacy method for local file loading - redirects to Supabase loading"""
        JSONHelper.load_database_from_supabase()

    @staticmethod
    def _default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    @staticmethod
    def _load_session(data: Dict[str, Any]) -> Session:
        s = Session(email=data["email"])
        s.date = datetime.fromisoformat(data["date"])
        s.messages = data.get("messages", [])
        return s


if __name__ == "__main__":
    db_handler = DatabaseHandler()
    db_handler.init()  # This will initialize and load from Supabase