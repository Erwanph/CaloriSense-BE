import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from datetime import datetime
import json
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

                # Send the beginning of streaming message
                await manager.send_message(email, {
                    "status": "streaming_start",
                    "intent": intentionIdx
                })
                
                response_data = {}
                final_response = ""
                
                # Use user data from cache instead of database queries
                match intentionIdx:
                    case 0:
                        # Regular chat - use streaming
                        stream_generator = Deepseek.send_stream(message, email)
                        async for token in stream_generator:
                            # Send each token as it arrives
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": token
                            })
                            final_response += token
                        
                        DatabaseHandler.save()
                        response_data = {
                            "response": final_response, 
                            "info_updated": False
                        }

                    case 1:
                        old_value = user_record.weight
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        user_record.weight = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your weight has been updated from {old_value} kg to {new_value} kg.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "weight"
                        }
                        # Send streaming response for better user experience
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)  # Small delay between words

                    case 2:
                        old_value = user_record.height
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        user_record.height = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your height has been updated from {old_value} cm to {new_value} cm.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "height"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 3:
                        old_value = user_record.food_allergies
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_record.food_allergies = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your food allergies information has been updated from '{old_value}' to '{new_value}'.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "food_allergies"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 4:
                        old_value = user_record.daily_activities
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_record.daily_activities = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your daily activities have been updated from '{old_value}' to '{new_value}'.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "daily_activities"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 5:
                        old_value = user_record.medical_record
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_record.medical_record = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your medical record has been updated from '{old_value}' to '{new_value}'.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "medical_record"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 6:
                        old_value = user_intent.weight_goal
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = float(response)
                        user_intent.weight_goal = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your weight goal has been updated from {old_value} kg to {new_value} kg.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "weight_goal"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 7:
                        old_value = user_intent.general_goal
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
                        new_value = response
                        user_intent.general_goal = new_value
                        DatabaseHandler.save()
                        final_response = with_followup(f"Your general goal has been updated from '{old_value}' to '{new_value}'.")
                        response_data = {
                            "response": final_response,
                            "info_updated": True,
                            "intent": "general_goal"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 8:
                        # Dapatkan prompt yang sudah ada, ini akan memberitahu LLM
                        # makanan dan nutrisi yang sudah ada untuk hari ini.
                        # LLM diharapkan mengembalikan nutrisi untuk makanan BARU SAJA.
                        response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)

                        # Strip markdown block if exists
                        if response.startswith("```"):
                            response = response.strip("`")  # removes all backticks
                            response = response.strip("json\n")  # removes 'json' label and newline
                            response = response.strip()

                        try:
                            response_dict = json.loads(response)
                        except json.JSONDecodeError:
                            try:
                                response_dict = eval(response) # Hati-hati dengan eval, tapi Anda sudah punya ini
                            except Exception as e:
                                response_dict = {"error": "Invalid response format", "raw": response}

                        if "error" in response_dict or not all(k in response_dict for k in ["foods", "carbohydrate", "fat", "protein"]):
                            # Jika LLM tidak mengembalikan format yang benar atau ada error,
                            # kirim pesan error ke user dan jangan update intake.
                            error_message = response_dict.get("error", "LLM returned an invalid format.")
                            raw_resp_info = f" Raw response: {response_dict.get('raw', 'N/A')}" if 'raw' in response_dict else ""
                            final_response = f"Sorry, I couldn't process that food input. {error_message}{raw_resp_info}"
                            response_data = {
                                "response": final_response,
                                "info_updated": False, # Karena tidak ada update
                                "intent": "food_intake_error" # intent bisa diubah untuk error handling di client
                            }
                            # Kirim pesan error sebagai 'streaming_token' jika ingin konsisten, atau langsung streaming_end
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": final_response
                            })
                        else:
                            # --- PERUBAHAN DIMULAI DI SINI ---
                            # Pastikan user_intake.foods adalah list
                            if not isinstance(user_intake.foods, list):
                                user_intake.foods = []

                            # Tambahkan makanan baru ke list yang sudah ada
                            new_foods = response_dict.get('foods', [])
                            if isinstance(new_foods, list):
                                user_intake.foods.extend(new_foods)
                            elif isinstance(new_foods, str): # Jika LLM mengembalikan string, coba split atau tambahkan apa adanya
                                user_intake.foods.append(new_foods)


                            # Akumulasikan nilai nutrisi
                            # Pastikan tipe data user_intake.carbohydrate, dll. adalah float/int
                            try:
                                user_intake.carbohydrate = float(user_intake.carbohydrate) + float(response_dict.get('carbohydrate', 0))
                                user_intake.fat = float(user_intake.fat) + float(response_dict.get('fat', 0))
                                user_intake.protein = float(user_intake.protein) + float(response_dict.get('protein', 0))
                            except ValueError:
                                # Handle kasus jika nilai awal bukan angka atau response_dict tidak valid
                                # Anda mungkin ingin log error ini atau mengirim pesan ke user
                                print(f"Error: Could not convert nutrient values to float for accumulation. Email: {email}")
                                # Untuk sekarang, kita biarkan nilai lama jika konversi gagal,
                                # tapi idealnya ini harus ditangani lebih baik.
                                pass # Atau kirim pesan error

                            DatabaseHandler.save()

                            # Format food items untuk display (sekarang akan berisi semua makanan hari ini)
                            food_list = ", ".join(user_intake.foods) if isinstance(user_intake.foods, list) else user_intake.foods

                            final_response = with_followup(
                                f"Your calorie tracker has been updated! Today you've eaten: {food_list}. "
                                f"Total for today: {user_intake.carbohydrate:.2f}g carbohydrate, "
                                f"{user_intake.fat:.2f}g fat, {user_intake.protein:.2f}g protein."
                            )
                            response_data = {
                                "response": final_response,
                                "info_updated": True,
                                "intent": "food_intake"
                            }
                            # --- PERUBAHAN SELESAI DI SINI ---

                        # Send streaming response (baik untuk sukses maupun error parsing LLM)
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)
                    
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
                        final_response = with_followup(record_info)
                        response_data = {
                            "response": final_response,
                            "info_updated": False,
                            "intent": "health_record_info"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case 10:
                        # User is asking for personal information
                        name = getattr(user_record, "name", None)
                        personal_info = f"Here is your personal information:\n- Email: {email}"
                        if name:
                            personal_info += f"\n- Name: {name}"
                        final_response = with_followup(personal_info)
                        response_data = {
                            "response": final_response,
                            "info_updated": False,
                            "intent": "personal_info"
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)

                    case _:
                        DatabaseHandler.save()
                        final_response = "Sorry, your intention couldn't be determined."
                        response_data = {
                            "response": final_response,
                            "info_updated": False
                        }
                        # Send streaming response
                        for word in final_response.split():
                            await manager.send_message(email, {
                                "status": "streaming_token",
                                "token": word + " "
                            })
                            await asyncio.sleep(0.05)
                
                # Send the end of streaming message
                await manager.send_message(email, {
                    "status": "streaming_end",
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