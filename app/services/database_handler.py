from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client
import json
from typing import Any, Dict, Union, List

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
    def save():
        JSONHelper.save_database_to_supabase()
        print("Database saved successfully to Supabase.")

    @staticmethod
    def find_user(email: str) -> User:
        for user in DatabaseHandler.user:
            if user.email == email:
                return user
        return None
    
    @staticmethod
    def find_intake_history(email: str) -> IntakeHistory:
        for history in DatabaseHandler.intake_history:
            if history.email == email:
                return history
        new_history = IntakeHistory(email, [])
        DatabaseHandler.intake_history.append(new_history)
        return new_history
    
    @staticmethod
    def find_intake(email: str) -> Intake:
        intake_history = DatabaseHandler.find_intake_history(email)
        for intake in intake_history.intakes:
            if intake.date == datetime.now().date():
                return intake
        new_intake = Intake(
            datetime.now().date(),
            0,
            0,
            0,
            []
        )

        intake_history.intakes.append(new_intake)
        return new_intake
    
    @staticmethod
    def find_intent(email: str) -> Intent:
        for intent in DatabaseHandler.intent:
            if intent.email == email:
                return intent
        return None
    
    @staticmethod
    def find_health_record(email: str) -> HealthRecord:
        for record in DatabaseHandler.health_record:
            if record.email == email:
                return record
        return None

    @staticmethod
    def find_session(email: str) -> Session:
        date = datetime.now()
        for session in DatabaseHandler.session:
            if session.email == email and session.date == date:
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

    @staticmethod
    def load_database_from_supabase() -> None:
        """Load the database from Supabase"""
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