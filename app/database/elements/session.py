from datetime import datetime
from app.services.config import Config

class Session:
    def __init__(self, email: str):
        self.email = email
        self.date = datetime.now()
        self.messages: list[dict] = []
    
    def add_system_prompt(self):
        from app.services.database_handler import DatabaseHandler

        system_prompt = (
            Config.SYSTEM_PROMPT +
            (DatabaseHandler.find_user(self.email).to_natural_language() if DatabaseHandler.find_user(self.email) else "") +
            (DatabaseHandler.find_health_record(self.email).to_natural_language() if DatabaseHandler.find_health_record(self.email) else "") +
            (DatabaseHandler.find_intent(self.email).to_natural_language() if DatabaseHandler.find_intent(self.email) else "") +
            (DatabaseHandler.find_intake_history(self.email).to_natural_language() if DatabaseHandler.find_intake_history(self.email) else "")
        )
        
        self.messages.append(
            {
                "role": "system", 
                "content": system_prompt
            }
        )
    
    def add_user_prompt(self, message):
        self.messages.append(
            {
                "role": "user",
                "content": message
            }
        )
    
    def add_assistant_response(self, message):
        self.messages.append(
            {
                "role": "assistant",
                "content": message
            }
        )

    def to_dir(self) -> dict:
        return {
            "email": self.email,
            "date": self.date.isoformat(),
            "messages": self.messages
        }
