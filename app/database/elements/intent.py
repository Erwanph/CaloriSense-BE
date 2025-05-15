class Intent:
    def __init__(
        self,
        email: str,
        weight_goal: float,
        general_goal: str,
        rdi: float
    ):
        self.email = email
        self.weight_goal = weight_goal
        self.general_goal = general_goal
        self.rdi = rdi

    def to_dir(self) -> dict:
        return {
            "email": self.email,
            "weight_goal": self.weight_goal,
            "general_goal": self.general_goal,
            "rdi": self.rdi
        }
    
    def to_natural_language(self) -> str:
        return (
            f"\nThe user with email {self.email} has a goal to reach a weight of {self.weight_goal} kilograms. "
            f"Their general goal is: {self.general_goal}. "
            f"Their recommended daily intake (RDI) is {self.rdi} kilocalories.\n"
        )

