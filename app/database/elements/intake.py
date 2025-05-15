from datetime import datetime

from datetime import datetime

class Intake:
    def __init__(
        self,
        date: str | datetime,
        protein: float,
        carbohydrate: float,
        fat: float,
        foods: list[str]
    ):
        if isinstance(date, str):
            self.date = datetime.strptime(date, "%Y-%m-%d")
        else:
            self.date = date
        self.protein = protein
        self.carbohydrate = carbohydrate
        self.fat = fat
        self.foods = foods

    def to_dir(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "protein": self.protein,
            "carbohydrate": self.carbohydrate,
            "fat": self.fat,
            "foods": self.foods,
        }



class IntakeHistory:
    def __init__(
        self,
        email: str,
        intakes: list[Intake]
    ):
        self.email = email
        self.intakes = intakes

    def to_dir(self) -> dict:
        return {
            "email": self.email,
            "intakes": [intake.to_dir() for intake in self.intakes]
        }
    
    def to_natural_language(self) -> str:
        if not self.intakes:
            return (
                f"\nThere are currently no food intake records available for the user with email {self.email}. "
                "This means the user has not logged any meals, calories, or food data yet.\n"
            )
        if len(self.intakes) == 1:
            latest = self.intakes[0]
        else:
            latest = max(
                self.intakes,
                key=lambda i: i.date if isinstance(i.date, datetime) else datetime.combine(i.date, datetime.min.time())
            )

        foods = ', '.join(latest.foods)
        total_kcal = latest.protein + latest.carbohydrate + latest.fat

        return (
            f"\nOn {latest.date.strftime('%Y-%m-%d')}, the user consumed a total of {total_kcal} kcal, "
            f"consisting of {latest.protein} kcal from protein, {latest.carbohydrate} kcal from carbohydrates, "
            f"and {latest.fat} kcal from fat. The foods they ate included: {foods}.\n"
        )

