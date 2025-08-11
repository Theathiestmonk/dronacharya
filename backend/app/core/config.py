import os

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # Add more settings as needed

settings = Settings() 