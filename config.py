from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_hostname: str
    database_port: int
    database_password: str
    database_username: str
    database_name: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    email_sender: str
    email_password: str
    database_url: str
    apikey: str                

    class Config:
        env_file = ".env"  # Load environment variables from the .env file

settings = Settings()