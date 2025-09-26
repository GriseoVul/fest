import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    #db settings
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = os.getenv("DB_PORT")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASS: str = os.getenv("DB_PASS")
    DB_NAME: str = os.getenv("DB_NAME")



    class Config:
        env_file = ".env"

settings = Settings()