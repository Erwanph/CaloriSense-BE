import asyncio
from typing import Dict, List, Any

# Import the Deepseek class from the refactored module
from app.services.deepseek_impl import Deepseek, DeepseekAPI

# Export the calculate_rdi function directly to maintain backward compatibility
async def calculate_rdi(
        weight: float,
        height: float,
        date_of_birth: str,
        gender: str,
        daily_activities: str,
        general_goal: str
    ) -> float:
    """
    Calculate Recommended Daily Intake based on user information.
    This function is a wrapper around Deepseek.calculate_rdi to maintain
    backward compatibility with existing code.
    """
    return await Deepseek.calculate_rdi(
        weight=weight,
        height=height,
        date_of_birth=date_of_birth,
        gender=gender,
        daily_activities=daily_activities,
        general_goal=general_goal
    )

# Re-export the send function for backward compatibility
async def send(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    """
    Send messages to the DeepSeek API and return the response.
    Wrapper for backward compatibility.
    """
    return await DeepseekAPI.send(messages, temperature)