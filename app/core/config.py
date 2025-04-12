import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY","accesskey")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "supersecret")
    AWS_REGION = os.getenv("AWS_REGION","ap-northeast-2")
    AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

settings = Settings()