import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
if len(JWT_SECRET_KEY.encode()) < 32:
    raise RuntimeError("Set JWT_SECRET_KEY to a random secret of at least 32 bytes.")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive.")
