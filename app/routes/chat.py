import json
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.intent_predictor import IntentPredictor
from app.services.deepseek_handler import Deepseek
from app.services.database_handler import DatabaseHandler

router = APIRouter()

@router.get("/")
async def answer(email: str, message: str):
    intentionIdx = await IntentPredictor.predict(message)
    intentPrompt = IntentPredictor.intent_prompt(intentionIdx, email)

    def with_followup(text: str):
        return f"✅ Selesai! Apakah kamu ingin melakukan hal lain?\n\n{text}"


    match intentionIdx:
        case 0:
            response = await Deepseek.send(message, email)
            DatabaseHandler.save()
            return {"response": response, "info_updated": False}

        case 1:
            record = DatabaseHandler.find_health_record(email)
            old_value = record.weight
            response = await Deepseek.send(f"{intentPrompt}\n\n{message}", email, 0)
            new_value = float(response)
            record.weight = new_value
            DatabaseHandler.save()
            return {
                "response": with_followup(f"Berat badanmu telah diperbarui dari {old_value} kg menjadi {new_value} kg."),
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
            return {
                "response": with_followup(f"Tinggi badanmu telah diperbarui dari {old_value} cm menjadi {new_value} cm."),
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
            return {
                "response": with_followup(f"Informasi alergi makananmu telah diperbarui dari '{old_value}' menjadi '{new_value}'."),
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
            return {
                "response": with_followup(f"Aktivitas harianmu telah diperbarui dari '{old_value}' menjadi '{new_value}'."),
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
            return {
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
            return {
                "response": with_followup(f"Catatan medis kamu telah diperbarui dari '{old_value}' menjadi '{new_value}'."),
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
            return {
                "response": with_followup(f"Tujuan umummu telah diperbarui dari '{old_value}' menjadi '{new_value}'."),
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
                    print("Failed to parse response:", e)
                    response_dict = {"error": "Invalid response format", "raw": response}
            print(response_dict.keys())
            print(response_dict)

            intake.foods = response_dict['foods']
            intake.carbohydrate = response_dict['carbohydrate']
            intake.fat = response_dict['fat']
            intake.protein = response_dict['protein']
            DatabaseHandler.save()
            return {
                "response": with_followup(f"Kalori harianmu telah diperbarui! Kamu makan {intake.foods} dengan {intake.carbohydrate}g karbohidrat, "f"{intake.fat}g lemak, dan {intake.protein}g protein."),
                "info_updated": True,
                "intent": "food_intake"
            }
        
        case 9:
            record = DatabaseHandler.find_health_record(email)
            return {
                "response": f"Your current weight is {record.weight} kg.",
                "info_updated": False,
                "intent": "get_weight"
            }                   


        case _:
            DatabaseHandler.save()
            return {
                "response": "Sorry, your intention couldn't be determined.",
                "info_updated": False
            }
