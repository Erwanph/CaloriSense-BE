class User:
    def __init__(
            self, 
            email: str, 
            first_name: str, 
            last_name: str, 
            date_of_birth: str, 
            gender: str, 
            country: str) -> None:
        
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.country = country

    def to_dir(self) -> dict:
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "country": self.country
        }
    
    def to_natural_language(self) -> str:
        return (
            f"\nThe user's name is {self.first_name} {self.last_name}. "
            f"They were born on {self.date_of_birth}, identify as {self.gender}, "
            f"and are from {self.country}. Their registered email is {self.email}.\n"
        )

