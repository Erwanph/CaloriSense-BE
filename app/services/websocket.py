import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

from app.services.intent_predictor import IntentPredictor
from app.services.deepseek_handler import Deepseek
from app.services.database_handler import DatabaseHandler

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
            
            # Process the message
            try:
                # Predict user intent
                intentionIdx = await IntentPredictor.predict(message)
                intentPrompt = IntentPredictor.intent_prompt(intentionIdx, email)

                def with_followup(text: str):
                    return f"✅ Done! Would you like to do anything else?\n\n{text}"

                response_data = {}
                
                # Send processing notification
                await manager.send_message(email, {
                    "status": "processing",
                    "message": "Processing your request..."
                })
                
                match intentionIdx:
                    case 0:
                        response = await Deepseek.send(message, email)
                        DatabaseHandler.save()
                        response_data = {
                            "response": response, 
                            "info_updated": False
                        }

                    case 1:
                        record = DatabaseHandler.find_health_record(email)
                        old_value = record.weight
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        record.weight = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your weight has been updated from {old_value} kg to {new_value} kg."),
                            "info_updated": True,
                            "intent": "weight"
                        }

                    case 2:
                        record = DatabaseHandler.find_health_record(email)
                        old_value = record.height
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        record.height = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your height has been updated from {old_value} cm to {new_value} cm."),
                            "info_updated": True,
                            "intent": "height"
                        }

                    case 3:
                        record = DatabaseHandler.find_health_record(email)
                        old_value = record.food_allergies
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        record.food_allergies = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your food allergies information has been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "food_allergies"
                        }

                    case 4:
                        record = DatabaseHandler.find_health_record(email)
                        old_value = record.daily_activities
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        record.daily_activities = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your daily activities have been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "daily_activities"
                        }

                    case 5:
                        record = DatabaseHandler.find_health_record(email)
                        old_value = record.medical_record
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        record.medical_record = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your medical record has been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "medical_record"
                        }

                    case 6:
                        intent = DatabaseHandler.find_intent(email)
                        old_value = intent.weight_goal
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        intent.weight_goal = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your weight goal has been updated from {old_value} kg to {new_value} kg."),
                            "info_updated": True,
                            "intent": "weight_goal"
                        }

                    case 7:
                        intent = DatabaseHandler.find_intent(email)
                        old_value = intent.general_goal
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        intent.general_goal = new_value
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your general goal has been updated from '{old_value}' to '{new_value}'."),
                            "info_updated": True,
                            "intent": "general_goal"
                        }
                    case 8:
                        intake = DatabaseHandler.find_intake(email)
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)

                        try:
                            response_dict = json.loads(response)
                        except json.JSONDecodeError:
                            try:
                                response_dict = eval(response)
                            except Exception as e:
                                response_dict = {"error": "Invalid response format", "raw": response}

                        intake.foods = response_dict['foods']
                        intake.carbohydrate = response_dict['carbohydrate']
                        intake.fat = response_dict['fat']
                        intake.protein = response_dict['protein']
                        DatabaseHandler.save()
                        response_data = {
                            "response": with_followup(f"Your calorie tracker has been updated!"),
                            "info_updated": True,
                            "intent": "food_intake"
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