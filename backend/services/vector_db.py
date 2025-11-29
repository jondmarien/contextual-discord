from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
from typing import List, Dict, Any

class VectorDB:
    def __init__(self, collection_name="gifs", memory=False):
        print(f"Initializing VectorDB (Memory: {memory})...")
        if memory:
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(path="./qdrant_data")
            
        self.collection_name = collection_name
        self._ensure_collection()
        print("VectorDB initialized.")

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection_name)
            print(f"Collection '{self.collection_name}' exists.")
        except Exception:
            print(f"Creating collection '{self.collection_name}'...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,  # MiniLM-L6-v2 dimension
                    distance=models.Distance.COSINE
                )
            )

    def upsert(self, vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=v,
                payload=p
            )
            for v, p in zip(vectors, payloads)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(self, vector: List[float], limit: int = 10):
        return self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit
        ).points
