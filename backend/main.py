from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models.embeddings import EmbeddingModel
import os

app = FastAPI(title="AI GIF Picker API")

# Global model instance
model = None

@app.on_event("startup")
async def startup_event():
    global model
    # Initialize model on startup
    # This might take a moment on first run to download weights
    model = EmbeddingModel()

class SearchRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    return {"message": "Contextual Discord API"}

@app.get("/health")
async def health_check():
    status = "ok" if model else "loading"
    return {"status": status}

@app.post("/api/search/semantic")
async def semantic_search(request: SearchRequest):
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    embedding, duration = model.encode(request.query)
    
    return {
        "query": request.query,
        "embedding_length": len(embedding),
        "inference_time_ms": duration,
        "message": "Embedding generated successfully"
    }
