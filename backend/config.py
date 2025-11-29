# Configuration settings
import os
from dotenv import load_dotenv

load_dotenv()

API_PORT = int(os.getenv("API_PORT", "8000"))
