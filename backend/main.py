from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models.embeddings import EmbeddingModel
from services.vector_db import VectorDB
from services.tenor_api import TenorAPI
from dotenv import load_dotenv
import os

# Load env vars
load_dotenv()

app = FastAPI(title="AI GIF Picker API")

# Global instances
model = None
vector_db = None
tenor_api = None

@app.on_event("startup")
async def startup_event():
    global model, vector_db, tenor_api
    # Initialize model
    model = EmbeddingModel()
    # Initialize VectorDB
    vector_db = VectorDB()
    # Initialize Tenor API
    tenor_api = TenorAPI()
    
    # Seed some data for testing if empty
    if model and vector_db:
        print("Seeding test data...")
        test_phrases = [
            "happy coding",
            "bugs everywhere",
            "deployment success",
            "server crash",
            "coffee break"
        ]
        embeddings = [model.encode(p)[0] for p in test_phrases]
        payloads = [{"text": p, "type": "test"} for p in test_phrases]
        vector_db.upsert(embeddings, payloads)
        print("Seeding complete.")

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

@app.get("/")
async def root():
    return {"message": "Contextual Discord API"}

@app.get("/health")
async def health_check():
    status = "ok" if model and vector_db else "loading"
    return {"status": status}

@app.post("/api/search/semantic")
async def semantic_search(request: SearchRequest):
    print(f"Received search request: {request.query}")
    if not model or not vector_db:
        print("Services not loaded")
        raise HTTPException(status_code=503, detail="Services not loaded")
    
    try:
        # 1. Generate embedding
        print("Generating embedding...")
        embedding, duration = model.encode(request.query)
        print(f"Embedding generated in {duration}ms")
        
        # 2. Search vector DB
        print("Searching vector DB...")
        results = vector_db.search(embedding, limit=request.limit)
        print(f"Found {len(results)} results")
        
        # 3. If low confidence or few results, fallback to Tenor
        # For prototype, let's always fetch Tenor if results < limit
        tenor_results = []
        if len(results) < request.limit:
            print("Fetching from Tenor...")
            tenor_data = tenor_api.search(request.query, limit=request.limit)
            tenor_results = [
                {
                    "id": item.get("id"),
                    "url": item.get("media_formats", {}).get("gif", {}).get("url"),
                    "title": item.get("content_description"),
                    "source": "tenor"
                }
                for item in tenor_data
            ]
            
        return {
            "query": request.query,
            "inference_time_ms": duration,
            "results": [
                {
                    "score": r.score,
                    "payload": r.payload,
                    "source": "semantic"
                }
                for r in results
            ] + tenor_results
        }
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
