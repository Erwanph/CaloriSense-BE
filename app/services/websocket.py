import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from datetime import datetime

from app.services.intent_predictor import IntentPredictor
from app.services.deepseek_handler import Deepseek
from app.services.database_handler import DatabaseHandler
from app.services.auth_handler import UserDataCache

router = APIRouter()

# Create a ConnectionManager to handle WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/{email}")
async def websocket_endpoint(websocket: WebSocket, email: str):
    await manager.connect(websocket, email)
    
    # Get reference to the global user data cache
    user_cache = UserDataCache.get_instance()
    
    # Load user data from cache immediately at connection time
    cached_data = user_cache.get_user_data(email)
    
    # If cache is empty, initialize it (fallback mechanism)
    if not cached_data:
        # Initialize database
        DatabaseHandler.init()
        
        # Load user data
        user_record = DatabaseHandler.find_health_record(email)
        user_intent = DatabaseHandler.find_intent(email)
        user_intake = DatabaseHandler.find_intake(email)
        
        # Store for direct access
        cached_data = {
            "health_record": user_record,
            "intent": user_intent,
            "intake": user_intake
        }
        
        # Update cache
        user_cache.set_user_data(email, cached_data)
    else:
        # Extract data from cache
        user_record = cached_data["health_record"]
        user_intent = cached_data["intent"]
        user_intake = cached_data["intake"]
        
        # Make sure we have today's intake (it could be from a previous day in cache)
        today = datetime.now().date()
        if not user_intake or user_intake.date != today:
            user_intake = DatabaseHandler.find_intake(email)
            cached_data["intake"] = user_intake
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if "message" not in message_data:
                await manager.send_message(email, {
                    "error": "Message field is required"
                })
                continue
                
            message = message_data["message"]
            
            # Send processing notification immediately
            await manager.send_message(email, {
                "status": "processing",
                "message": "Processing your request..."
            })
            
            # Process the message
            try:
                # Predict intent
                intentionIdx = await IntentPredictor.predict(message)
                intentPrompt = IntentPredictor.intent_prompt(intentionIdx, email) 

                def with_followup(text: str):
                    return f"✅ Done! Would you like to do anything else?\n\n{text}"

                response_data = {}
                
                # Use user data from cache instead of database queries
                match intentionIdx:
                    case 0:
                        response = await Deepseek.send(message, email)
                        DatabaseHandler.save()
                        response_data = {
                            "response": response, 
                            "info_updated": False
                        }

                    case 1:
                        old_value = user_record.weight
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        user_record.weight = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your weight has been updated from {old_value} kg to {new_value} kg."),
                            "info_updated": True,
                            "intent": "weight"
                        }

                    case 2:
                        old_value = user_record.height
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        user_record.height = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your height has been updated from {old_value} cm to {new_value} cm."),
                            "info_updated": True,
                            "intent": "height"
                        }

                    case 3:
                        old_value = user_record.food_allergies
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_record.food_allergies = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your food allergies information has been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "food_allergies"
                        }

                    case 4:
                        old_value = user_record.daily_activities
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_record.daily_activities = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your daily activities have been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "daily_activities"
                        }

                    case 5:
                        old_value = user_record.medical_record
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_record.medical_record = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your medical record has been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "medical_record"
                        }

                    case 6:
                        old_value = user_intent.weight_goal
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        user_intent.weight_goal = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your weight goal has been updated from {old_value} kg to {new_value} kg."),
                            "info_updated": True,
                            "intent": "weight_goal"
                        }

                    case 7:
                        old_value = user_intent.general_goal
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_intent.general_goal = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your general goal has been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "general_goal"
                        }
                    case 8:
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)

                        try:
                            response_dict = json.loads(response)
                        except json.JSONDecodeError:
                            try:
                                response_dict = eval(response)
                            except Exception as e:
                                response_dict = {"error": "Invalid response format", "raw": response}

                        # Properly handle the food items (avoid duplicates)
                        user_intake.foods = response_dict['foods']
                        user_intake.carbohydrate = response_dict['carbohydrate']
                        user_intake.fat = response_dict['fat']
                        user_intake.protein = response_dict['protein']
                        DatabaseHandler.save()
                        
                        # Format food items for display
                        food_list = ", ".join(user_intake.foods) if isinstance(user_intake.foods, list) else user_intake.foods
                        
                        response_data = {
                            "response": with_followup(f"Your calorie tracker has been updated! You ate {food_list} with {user_intake.carbohydrate}g carbohydrate, {user_intake.fat}g fat, {user_intake.protein}g protein."),
                            "info_updated": True,
                            "intent": "food_intake"
                        }
                    
                    case 9:
                        # User is asking for health record information
                        record_info = (
                            f"Here is your health record:\n"
                            f"- Weight: {user_record.weight} kg\n"
                            f"- Height: {user_record.height} cm\n"
                            f"- Allergies: {user_record.food_allergies}\n"
                            f"- Daily Activities: {user_record.daily_activities}\n"
                            f"- Daily Exercises: {user_record.daily_exercises}\n"
                            f"- Medical Record: {user_record.medical_record}"
                        )
                        response_data = {
                            "response": with_followup(record_info),
                            "info_updated": False,
                            "intent": "health_record_info"
                        }

                    case 10:
                        # User is asking for personal information
                        name = getattr(user_record, "name", None)
                        personal_info = f"Here is your personal information:\n- Email: {email}"
                        if name:
                            personal_info += f"\n- Name: {name}"
                        response_data = {
                            "response": with_followup(personal_info),
                            "info_updated": False,
                            "intent": "personal_info"
                        }

                    case _:
                        DatabaseHandler.save()
                        response_data = {
                            "response": "Sorry, your intention couldn't be determined.",
                            "info_updated": False
                        }
                
                # Send the final response back to the client
                await manager.send_message(email, {
                    "status": "completed",
                    **response_data
                })
                
            except Exception as e:
                # Send error message if something goes wrong
                await manager.send_message(email, {
                    "status": "error",
                    "message": f"Error processing request: {str(e)}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(email)
    except Exception as e:
        manager.disconnect(email)
        print(f"WebSocket error: {str(e)}")