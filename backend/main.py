from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from models.embeddings import EmbeddingModel
from services.vector_db import VectorDB
from services.tenor_api import TenorAPI
from dotenv import load_dotenv
import os

# Load env vars
load_dotenv()

app = FastAPI(title="AI GIF Picker API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    vector_db = VectorDB(memory=False)
    # Initialize Tenor API
    tenor_api = TenorAPI()

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
        all_results = vector_db.search(embedding, limit=request.limit)
        
        # Filter by similarity threshold
        SIMILARITY_THRESHOLD = 0.6
        results = [r for r in all_results if r.score >= SIMILARITY_THRESHOLD]
        print(f"Found {len(results)} relevant results (score >= {SIMILARITY_THRESHOLD})")
        
        # 3. If low confidence or few results, fallback to Tenor
        tenor_results = []
        if len(results) < request.limit:
            print("Fetching from Tenor...")
            tenor_data = tenor_api.search(request.query, limit=request.limit)
            
            # Format Tenor results immediately
            formatted_tenor_results = []
            for item in tenor_data:
                media = item.get("media_formats", {})
                formatted_tenor_results.append({
                    "id": item.get("id"),
                    "title": item.get("content_description", ""),
                    "url": item.get("itemurl", ""),
                    "src": media.get("webm", {}).get("url", ""),
                    "gif_src": media.get("gif", {}).get("url", ""),
                    "width": media.get("gif", {}).get("dims", [498, 373])[0],
                    "height": media.get("gif", {}).get("dims", [498, 373])[1],
                    "preview": media.get("tinygif", {}).get("url", "")
                })
            
            # LAZY INDEXING: Save these results to VectorDB with the query's embedding
            if formatted_tenor_results:
                print(f"Indexing {len(formatted_tenor_results)} new results for query: '{request.query}'")
                # Create a list of the same embedding for all results
                embeddings = [embedding] * len(formatted_tenor_results)
                # Use the formatted results as payloads
                payloads = formatted_tenor_results
                vector_db.upsert(embeddings, payloads)
                
            tenor_results = formatted_tenor_results

        # Format results for Discord
        formatted_results = []
        
        # Process Semantic Results
        for r in results:
            payload = r.payload
            formatted_results.append(payload)

        # Add Tenor Results (already formatted)
        formatted_results.extend(tenor_results)

        # Deduplicate by ID
        seen_ids = set()
        unique_results = []
        for r in formatted_results:
            if r['id'] not in seen_ids:
                unique_results.append(r)
                seen_ids.add(r['id'])

        return {
            "results": unique_results[:request.limit]
        }
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/reset")
async def reset_db():
    print("Resetting Vector DB...")
    global vector_db
    try:
        # Re-initialize with a fresh collection (dropping old one)
        vector_db.client.delete_collection(vector_db.collection_name)
        vector_db._ensure_collection()
        return {"status": "success", "message": "Brain wiped! 🧠✨"}
    except Exception as e:
        print(f"Error resetting DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))
