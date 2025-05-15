class HealthRecord:
    def __init__(
        self,
        email: str,
        weight: float,
        height: float,
        food_allergies: str,
        daily_exercises: str,
        daily_activities: str,
        medical_record: str
    ):
        self.email = email
        self.weight = weight
        self.height = height
        self.food_allergies = food_allergies
        self.daily_exercises = daily_exercises
        self.daily_activities = daily_activities
        self.medical_record = medical_record

    def to_dir(self) -> dict:
        return {
            "email": self.email,
            "weight": self.weight,
            "height": self.height,
            "food_allergies": self.food_allergies,
            "daily_exercises": self.daily_exercises,
            "daily_activities": self.daily_activities,
            "medical_record": self.medical_record,
        }
    
    def to_natural_language(self) -> str:
        return (
            f"\nThe user with email {self.email} has a weight of {self.weight} kilograms and "
            f"a height of {self.height} centimeters. "
            f"They have the following food allergies: {self.food_allergies}. "
            f"Their daily exercises include: {self.daily_exercises}, and their daily activities are: "
            f"{self.daily_activities}. "
            f"Their medical record contains the following notes: {self.medical_record}.\n"
        )

