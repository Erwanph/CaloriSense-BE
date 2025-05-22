import asyncio
from datetime import datetime
import httpx
import os
import json
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, AsyncGenerator
import time
import cachetools

from app.database.elements.session import Session
from app.services.config import Config
from app.services.database_handler import DatabaseHandler
from dateutil.relativedelta import relativedelta

# Load environment variables
load_dotenv()

# Add cache to store API responses
API_CACHE = cachetools.TTLCache(maxsize=100, ttl=60*5)  # Cache lasts 5 minutes

class DeepseekAPI:
    """Helper class to interact with the DeepSeek API"""
    API_URL = "https://api.deepseek.com/chat/completions"
    
    # Reuse HTTP client to save connection setup time
    _http_client = None
    
    @classmethod
    async def get_client(cls):
        """Get or create an HTTP client with appropriate timeout"""
        if cls._http_client is None:
            # Increase timeout from 30.0 to 60.0 seconds to prevent timeouts
            timeout = httpx.Timeout(60.0)
            cls._http_client = httpx.AsyncClient(timeout=timeout)
        return cls._http_client
    
    @staticmethod
    def get_cache_key(messages: List[Dict[str, str]], temperature: float) -> str:
        """Generate a cache key for the request"""
        # Simplified key generation - in production you might want something more robust
        msg_str = str(messages)
        return f"{msg_str}_{temperature}"
    
    @classmethod
    async def send(cls, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Send messages to the DeepSeek API and return the response, with caching"""
        # Check cache first
        cache_key = cls.get_cache_key(messages, temperature)
        cached_result = API_CACHE.get(cache_key)
        if cached_result:
            return cached_result
        
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

        client = await cls.get_client()
        start_time = time.time()
        
        # Implement retry logic - try up to 3 times with exponential backoff
        max_retries = 3
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                response = await client.post(cls.API_URL, headers=headers, json=payload)
                
                if response.status_code != 200:
                    raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")
                    
                data = response.json()
                try:
                    result = data["choices"][0]["message"]["content"]
                    # Cache the result
                    API_CACHE[cache_key] = result
                    print(f"API call took {time.time() - start_time:.2f} seconds")
                    return result
                except (KeyError, IndexError):
                    raise Exception(f"Unexpected response format: {data}")
                    
            except httpx.ReadTimeout:
                if attempt < max_retries - 1:
                    # If not the last attempt, wait and retry
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    print(f"DeepSeek API timed out. Retrying attempt {attempt + 2}/{max_retries}")
                else:
                    # On the last attempt, raise the exception
                    raise Exception("DeepSeek API timed out after multiple attempts. Please try again later.")
            except Exception as e:
                # For other exceptions, don't retry
                raise e
    
    @classmethod
    async def send_stream(cls, messages: List[Dict[str, str]], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Send messages to the DeepSeek API and yield responses as they come in"""
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 512,
            "stream": True  # Enable streaming
        }

        client = await cls.get_client()
        start_time = time.time()
        
        # Implement retry logic - try up to 3 times with exponential backoff
        max_retries = 3
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                async with client.stream("POST", cls.API_URL, headers=headers, json=payload, timeout=60.0) as response:
                    if response.status_code != 200:
                        response_text = await response.aread()
                        raise Exception(f"DeepSeek API error: {response.status_code} - {response_text.decode('utf-8')}")
                    
                    # Process the streaming response
                    full_response = ""
                    async for chunk in response.aiter_bytes():
                        chunk_str = chunk.decode('utf-8')
                        
                        # Parse the SSE format - each chunk starts with "data: "
                        for line in chunk_str.split('\n'):
                            if line.startswith('data: '):
                                data_str = line[6:]  # Remove "data: " prefix
                                
                                # Check for [DONE] marker
                                if data_str.strip() == "[DONE]":
                                    break
                                    
                                try:
                                    data = json.loads(data_str)
                                    delta_content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta_content:
                                        full_response += delta_content
                                        yield delta_content
                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    print(f"Error processing chunk: {e}")
                                    continue
                    
                    # Cache the full response for future use
                    cache_key = cls.get_cache_key(messages, temperature)
                    API_CACHE[cache_key] = full_response
                    print(f"Streaming API call took {time.time() - start_time:.2f} seconds")
                    return
                    
            except httpx.ReadTimeout:
                if attempt < max_retries - 1:
                    # If not the last attempt, wait and retry
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    print(f"DeepSeek API streaming timed out. Retrying attempt {attempt + 2}/{max_retries}")
                else:
                    # On the last attempt, raise the exception
                    raise Exception("DeepSeek API streaming timed out after multiple attempts. Please try again later.")
            except Exception as e:
                # For other exceptions, don't retry
                raise e


class Deepseek:
    """Class to handle DeepSeek chat interactions and session management"""
    
    # Cache for RDI results
    _rdi_cache = {}
    
    @classmethod
    async def calculate_rdi(cls,
            weight: float,
            height: float,
            date_of_birth: str,
            gender: str,
            daily_activities: str,
            general_goal: str
        ) -> float:
        """Calculate Recommended Daily Intake based on user information, with caching"""
        # Create cache key
        cache_key = f"{weight}_{height}_{date_of_birth}_{gender}_{daily_activities}_{general_goal}"
        
        # Check cache
        if cache_key in cls._rdi_cache:
            return cls._rdi_cache[cache_key]
            
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
            rdi = float(response.strip())
            # Cache the result
            cls._rdi_cache[cache_key] = rdi
            return rdi
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
        
        # Database saving is delayed until the websocket handler saves it
        # No need to save the database every time a message is sent
        # DatabaseHandler.save()
        
        return response

    @staticmethod
    async def send_stream(message: str, email: str, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Process a user message, stream response from DeepSeek, and update session"""
        # Find or create session
        session = DatabaseHandler.find_session(email)
        if session is None:
            session = Session(email)
            session.add_system_prompt()
            DatabaseHandler.session.append(session)
        
        # Add user message to session
        session.add_user_prompt(message)
        
        # Stream response from API - first get all messages
        messages = session.messages
        if not messages:
            raise ValueError("No messages to send.")
        
        # Initialize full response accumulator
        full_response = ""
        
        # Use streaming API
        async for token in DeepseekAPI.send_stream(messages, temperature):
            full_response += token
            yield token
        
        # After streaming is complete, add the full response to the session
        session.add_assistant_response(full_response)
        
        # No need to return as we're yielding tokens during the stream

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
            print("Assistant: ", end="", flush=True)
            async for token in Deepseek.send_stream(user_input, email):
                print(token, end="", flush=True)
            print()  # New line after response
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())