from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
from typing import List, Dict, Any

class VectorDB:
    def __init__(self, collection_name="gifs", memory=True):
        print(f"Initializing VectorDB (Memory: {memory})...")
        if memory:
            self.client = QdrantClient(":memory:")
        else:
            # TODO: Add persistent storage path or URL
            self.client = QdrantClient(path="./qdrant_data")
            
        self.collection_name = collection_name
        self._ensure_collection()
        print("VectorDB initialized.")

    def _ensure_collection(self):
        # In development, we can just recreate to ensure schema is correct
        # or use recreate_collection which handles existence check
        self.client.recreate_collection(
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
