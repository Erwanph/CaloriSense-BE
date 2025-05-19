import asyncio
from datetime import datetime
import httpx
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

from app.database.elements.session import Session
from app.services.config import Config
from app.services.database_handler import DatabaseHandler
from dateutil.relativedelta import relativedelta

# Module name should be deepseek_handler.py to match import in auth.py

# Load environment variables
load_dotenv()

class DeepseekAPI:
    """Helper class to interact with the DeepSeek API"""
    API_URL = "https://api.deepseek.com/chat/completions"
    
    @staticmethod
    async def send(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Send messages to the DeepSeek API and return the response"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 512,
            "stream": False
        }

        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(DeepseekAPI.API_URL, headers=headers, json=payload)
            except httpx.ReadTimeout:
                raise Exception("DeepSeek API timed out. Please try again later.")

        if response.status_code != 200:
            raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise Exception(f"Unexpected response format: {data}")


class Deepseek:
    """Class to handle DeepSeek chat interactions and session management"""
    
    @staticmethod
    async def calculate_rdi(
            weight: float,
            height: float,
            date_of_birth: str,
            gender: str,
            daily_activities: str,
            general_goal: str
        ) -> float:
        """Calculate Recommended Daily Intake based on user information"""

        message = (
            f"The user was born on {date_of_birth}, a {gender} weighing {weight} kilograms and "
            f"{height} centimeters tall. Their daily activity level is '{daily_activities}', "
            f"and their goal is to '{general_goal}'. Please calculate the RDI (Recommended Daily Intake) "
            f"in kilocalories for this person based on this information."
        )

        messages = [
            {"role": "system", "content": "Please calculate the RDI based on the following condition. Answers only in numbers. Do not show me the calculation, answer only in one word."},
            {"role": "user", "content": message}
        ]

        response = await DeepseekAPI.send(messages, 0)

        try:
            return float(response.strip())
        except ValueError:
            raise ValueError(f"Invalid response for RDI: {response}")

    @staticmethod
    async def send(message: str, email: str, temperature: float = 0.7) -> str:
        """Process a user message, get response from DeepSeek, and update session"""
        # Find or create session
        session = DatabaseHandler.find_session(email)
        if session is None:
            session = Session(email)
            session.add_system_prompt()
            DatabaseHandler.session.append(session)
        
        # Add user message to session
        session.add_user_prompt(message)
        
        # Get response from API
        response = await Deepseek._send_messages(session, temperature)
        
        # Add assistant response to session
        session.add_assistant_response(response)
        
        # Save updated database
        DatabaseHandler.save()
        
        return response

    @staticmethod
    async def _send_messages(session: Session, temperature: float) -> str:
        """Send all messages in session to DeepSeek API"""
        messages = session.messages
        if not messages:
            raise ValueError("No messages to send.")

        response = await DeepseekAPI.send(messages, temperature)
        return response


async def main():
    """CLI for testing the Deepseek chat functionality"""
    # Initialize database
    DatabaseHandler.init()
    
    print("Deepseek Chat CLI")
    email = input("Enter email for session: ")
    
    while True:
        user_input = input("> ")
        if user_input.lower() in {"exit", "quit"}:
            break
            
        try:
            response = await Deepseek.send(user_input, email)
            print(f"Assistant: {response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())