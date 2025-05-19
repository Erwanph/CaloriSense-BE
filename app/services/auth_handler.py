import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any

# Load environment variables
load_dotenv()

class AuthHandler:
    def __init__(self) -> None:
        self._supabase = self._initialize_supabase()
    
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
        """Authenticate user using Supabase"""
        try:
            response = self._supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
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
        """Logout user session"""
        try:
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