import requests
import os
from typing import List, Dict, Any

class TenorAPI:
    def __init__(self):
        self.api_key = os.getenv("TENOR_API_KEY")
        self.client_key = "contextual_discord_bot"
        self.base_url = "https://tenor.googleapis.com/v2"
        
        if not self.api_key:
            print("WARNING: TENOR_API_KEY not found in environment variables.")

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
            
        params = {
            "q": query,
            "key": self.api_key,
            "client_key": self.client_key,
            "limit": limit,
            "media_filter": "gif,tinygif"
        }
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Tenor API error: {e}")
            return []

    def get_trending(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
            
        params = {
            "key": self.api_key,
            "client_key": self.client_key,
            "limit": limit,
            "media_filter": "gif,tinygif"
        }
        
        try:
            response = requests.get(f"{self.base_url}/featured", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Tenor API error: {e}")
            return []
