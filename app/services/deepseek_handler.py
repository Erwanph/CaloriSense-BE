import asyncio
from datetime import datetime
import httpx
from app.database.elements.session import Session
from app.services.config import Config
from app.services.database_handler import DatabaseHandler
from dateutil.relativedelta import relativedelta

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

async def send(messages: list[dir], temperature: float = 0.7) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.DEEPSEEK_KEY}"
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
            response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        except httpx.ReadTimeout:
            raise Exception("DeepSeek API timed out. Please try again later.")

    if response.status_code != 200:
        raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise Exception(f"Unexpected response format: {data}")

async def calculate_rdi(
        weight: float,
        height: float,
        date_of_birth: str,
        gender: str,
        daily_activities: str,
        general_goal: str
    ) -> float:

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

    response = await send(messages, 0)

    try:
        return float(response.strip())
    except ValueError:
        raise ValueError(f"Invalid response for RDI: {response}")

class Deepseek:
    async def send(message: str, email: str, temperature: float = 0.7):
        session = DatabaseHandler.find_session(email)
        if (session is None):
            session = Session(email)
            session.add_system_prompt()
            DatabaseHandler.session.append(session)
        
        session.add_user_prompt(message)
        response = await Deepseek._send_messages(session, temperature)
        session.add_assisant_response(response)
        DatabaseHandler.save()
        return response

    async def _send_messages(session: Session, temperature: float) -> None:
        messages = session.messages
        if not messages:
            raise ValueError("No messages to send.")

        response = await send(messages, temperature)
        messages.append({"role": "assistant", "content": response})
        return response
    


async def main():
    joniBot = Deepseek(Config.SYSTEM_PROMPT)
    while True:
        prompt = input("> ")
        if prompt.lower() in {"exit", "quit"}:
            break
        joniBot.add_user_message(prompt)
        response = await joniBot.send()
        print(response)

if __name__ == "__main__":
    asyncio.run(main())