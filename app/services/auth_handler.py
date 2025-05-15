import json
import os

from app.services.config import Config

class AuthHandler:
    def __init__(self) -> None:
        self.filepath = Config.USER_INFO_PATH
        self.users: list[dict] = []
        self.load_users()
    
    def register(self, email: str, password: str) -> bool:
        if any(user["email"] == email for user in self.users):
            return False
        self.users.append({"email": email, "password": password})
        self.save_users()
        return True

    def login(self, email: str, password: str) -> bool:
        return any(user["email"] == email and user["password"] == password for user in self.users)
    
    def load_users(self) -> None:
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.users = json.load(f)
        else:
            self.users = []

    def save_users(self) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2)
