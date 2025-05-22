import asyncio
from app.services.deepseek_handler import DeepseekAPI
from app.services.auth_handler import UserDataCache
from app.database.elements.health_record import HealthRecord
from app.database.elements.intent import Intent
from app.database.elements.intake import Intake

possible_intentions = [
    "asking only (e.g. asking about food nutrition, what food to eat, etc)",
    "change weight",
    "change height",
    "update allergies",
    "update activities", 
    "update medical records",
    "update weight goal",
    "update general goal",
    "telling you what food they eat with the intention to log their food. Be aware this occurs rarely and only answer this if you are confident.",
    # "ask current weight"
]

intent_system_prompt = f"""
You are an intent classifier.

Your task is to determine the user's intent based on their message. 
If the user's intent is unclear, ambiguous, too short, or only contains a topic keyword without any clear action, return 0.

Do not guess or assume. Only choose another number if the message **clearly expresses a user intention**.

Choose only from:
{chr(10).join(f"{i}. {intent}" for i, intent in enumerate(possible_intentions))}

Return a single digit only (e.g. 0, 1, 2, ...). No explanation.
"""

class IntentPredictor:
    # Cache intent prediction results to avoid redundant API calls
    _intent_prediction_cache = {}
    
    @staticmethod
    async def predict(message: str):
        # Check cache first
        if message in IntentPredictor._intent_prediction_cache:
            return IntentPredictor._intent_prediction_cache[message]
            
        messages = [
            {"role": "system", "content": intent_system_prompt},
            {"role": "user", "content": message}
        ]
        try:
            response = await DeepseekAPI.send(messages, temperature=0)
            intent_idx = int(response.strip())
            # Cache the result
            IntentPredictor._intent_prediction_cache[message] = intent_idx
            return intent_idx
        except ValueError:
            return 0 
        except Exception as e:
            print(f"Error predicting intent: {e}")
            return 0  # Default to asking mode on any error
    
    @staticmethod
    def intent_prompt(intentIdx: int, email: str):
        # Get user data from cache
        user_cache = UserDataCache.get_instance()
        cached_data = user_cache.get_user_data(email)
        
        # Initialize default objects in case data is not found
        record = None
        intent = None
        intake = None
        
        if cached_data:
            record = cached_data.get("health_record")
            intent = cached_data.get("intent")
            intake = cached_data.get("intake")
        else:
            # Fallback to database if cache is empty
            from app.services.database_handler import DatabaseHandler
            record = DatabaseHandler.find_health_record(email)
            intent = DatabaseHandler.find_intent(email)
            intake = DatabaseHandler.find_intake(email)
        
        # Create default objects if still None
        if record is None:
            record = HealthRecord(email=email, weight=70, height=170, food_allergies="None", 
                                 daily_activities="Sedentary",daily_exercises="Active", medical_record="None")
        
        if intent is None:
            intent = Intent(email=email, weight_goal=70, general_goal="Maintain weight", rdi=1800)
            
        if intake is None:
            intake = Intake(email=email, foods=[], carbohydrate=0, protein=0, fat=0)

        match intentIdx:
            case 0:
                return ""
            case 1:
                return (
                    f"For the following message, I want to change my weight. "
                    f"My previous weight is {record.weight} kg. "
                    f"Please answer with the new weight only, as a float in kg."
                )
            case 2:
                return (
                    f"For the following message, I want to change my height. "
                    f"My previous height is {record.height} cm. "
                    f"Please answer with the new height only, as a float in cm."
                )
            case 3:
                return (
                    f"For the following message, I want to update my food allergies information. "
                    f"My previous data was: {record.food_allergies}. "
                    f"Please answer with the updated allergies only as a string."
                )
            case 4:
                return (
                    f"For the following message, I want to update my daily activities. "
                    f"My current daily activities are: {record.daily_activities}. "
                    f"Please answer with the updated daily activities only as a string."
                )
            case 5:
                return (
                    f"For the following message, I want to update my medical records. "
                    f"My previous medical records are: {record.medical_record}. "
                    f"Please answer with the updated medical records only as a string."
                )
            case 6:
                return (
                    f"For the following message, I want to change my weight goal. "
                    f"My current weight goal is {intent.weight_goal} kg. "
                    f"Please answer with the new weight goal only as a float in kg."
                )
            case 7:
                return (
                    f"For the following message, I want to change my general goal. "
                    f"My current goal is: {intent.general_goal}. "
                    f"Please answer with the new goal only as a string."
                )
            case 8:
                return (
                    f"For the following message, I want to update my food and calorie intake. "
                    f"The foods that I have eaten today are: {intake.foods}. "
                    f"My current intake are: carbohydrate {intake.carbohydrate}g, protein {intake.protein}g, and fat {intake.fat}g. "
                    f"Please parse the user's message to identify new food items and their quantities. "
                    f"If the user mentions a food with a quantity (e.g., 'nasi goreng 1'), keep the quantity with the food name. "
                    f"Please use these realistic nutrition values for common foods:\n"
                    f"- Nasi goreng (1 plate): 45g carbohydrate, 8g protein, 15g fat\n"
                    f"- White rice (1 cup): 45g carbohydrate, 4g protein, 0.5g fat\n"
                    f"- Chicken breast (100g): 0g carbohydrate, 31g protein, 3.6g fat\n"
                    f"- Egg (1 large): 0.6g carbohydrate, 6g protein, 5g fat\n"
                    f"Please answer with the format: "
                    '{"foods":["food1","food2 quantity"],"protein":X,"fat":Y,"carbohydrate":Z}'
                    f" where X, Y, and Z are calculated values based on the actual foods identified, not these example values."
                    f" Do not add any sentence outside of the curly brackets."
                    f" If you don't know the exact nutrition values for a specific food, use your knowledge to provide realistic estimates."
                )
            case 9:
                return (
                    f"The user's current weight is {record.weight} kg. "
                    f"Just respond with: 'Your current weight is {record.weight} kg.' Do not say anything else."
                )
            case _:
                return "Invalid intent index."