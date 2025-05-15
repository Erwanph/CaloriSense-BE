from app.services.deepseek_handler import send
from app.services.database_handler import DatabaseHandler

possible_intentions = [
    "asking only (e.g. asking about food nutrition, what food to eat, etc)",
    "change weight",
    "change height",
    "update allergies",
    "update activities",
    "update medical records",
    "update weight goal",
    "update general goal",
    "telling you what food they eat with the intention to log their food. Be aware this occurs rarely and only answer this if you are confident."
]

intent_system_prompt = f'''
Predict the user's intent. If unsure, answer 0.
Choose from:
{chr(10).join(f"{i}. {intent}" for i, intent in enumerate(possible_intentions))}
Respond with a single digit only.
'''

class IntentPredictor:
    @staticmethod
    async def predict(message: str):
        respond = await send([
            {"role": "system", "content": intent_system_prompt},
            {"role": "user", "content": message}
        ], 0)
        return int(respond)
    
    @staticmethod
    def intent_prompt(intentIdx: int, email: str):
        record = DatabaseHandler.find_health_record(email)
        intent = DatabaseHandler.find_intent(email)
        intake = DatabaseHandler.find_intake(email)

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
                    f"My current intake are: carbohydrate {intake.carbohydrate} kcal, protein {intake.protein} kcal, and fat {intake.fat} kcal"
                    "Please answer with the format:"
                    '{"foods":["food1","food2"],"protein":130,"fat":130,"carbohydrate":250'
                    "Do not add any sentence outside of the curly brackets. Please add the new food to the foods array, and sum up the total of calories."
                )
            case _:
                return "Invalid intent index."
