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

class ContextRequest(BaseModel):
    messages: list[str]

# Pre-defined anchors for context detection
EMOTION_ANCHORS = {
    "anger": ["rage", "furious", "hate this", "broken", "stupid", "error", "bug", "fail"],
    "joy": ["happy", "success", "finally", "works", "great", "awesome", "celebrate", "party"],
    "confusion": ["what", "why", "confused", "weird", "strange", "help", "how", "unknown"],
    "waiting": ["slow", "loading", "taking forever", "waiting", "stuck", "lag"],
    "tired": ["sleepy", "exhausted", "late", "3am", "tired", "bed", "nap"],
    "coding": ["code", "programming", "dev", "git", "commit", "push", "deploy", "python", "typescript"],
    "funny": ["lol", "lmao", "haha", "funny", "hilarious", "laughing", "joke", "rofl"]
}

SUGGESTIONS = {
    "anger": ["coding rage", "computer smash", "dumpster fire", "screaming"],
    "joy": ["coding success", "hackerman", "celebration", "party"],
    "confusion": ["confused math lady", "what is happening", "confused travolta"],
    "waiting": ["waiting skeleton", "still loading", "mr bean waiting"],
    "tired": ["tired coding", "falling asleep", "coffee needs"],
    "coding": ["coding", "developer", "hacker", "programming"],
    "funny": ["laughing", "spit take", "wheeze", "dying laughing"]
}

# Global cache for anchor embeddings
ANCHOR_EMBEDDINGS = {}
EMOTION_DATA = {}
CLASSIFIER = None
CLASSIFIER_LABELS = []

import numpy as np
import json
import joblib

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Mapping GoEmotions labels to our Suggestion Categories
EMOTION_MAPPING = {
    "anger": "anger", "annoyance": "anger", "disapproval": "anger", "disgust": "anger",
    "joy": "joy", "excitement": "joy", "pride": "joy", "optimism": "joy", "relief": "joy", "admiration": "joy", "approval": "joy", "gratitude": "joy",
    "amusement": "funny",
    "confusion": "confusion", "curiosity": "confusion", "realization": "confusion",
    "love": "love", "caring": "love", "desire": "love",
    "sadness": "sadness", "grief": "sadness", "disappointment": "sadness", "remorse": "sadness", "embarrassment": "sadness",
    "surprise": "shock", "fear": "shock", "nervousness": "shock",
    "neutral": "neutral"
}

@app.on_event("startup")
async def startup_event():
    global model, vector_db, tenor_api, ANCHOR_EMBEDDINGS, EMOTION_DATA, EMOTION_ANCHORS, SUGGESTIONS, CLASSIFIER, CLASSIFIER_LABELS
    # Initialize model
    model = EmbeddingModel()
    # Initialize VectorDB
    vector_db = VectorDB(memory=False)
    # Initialize Tenor API
    tenor_api = TenorAPI()
    
    # Load Emotion Data
    try:
        with open("data/emotions.json", "r") as f:
            EMOTION_DATA = json.load(f)
            
        # Populate global dicts from JSON
        EMOTION_ANCHORS = {k: v["anchors"] for k, v in EMOTION_DATA["emotions"].items()}
        SUGGESTIONS = {k: v["suggestions"] for k, v in EMOTION_DATA["emotions"].items()}
        
        print(f"Loaded {len(EMOTION_ANCHORS)} emotion categories from JSON.")
    except Exception as e:
        print(f"Failed to load emotions.json: {e}")
        EMOTION_ANCHORS = {}
        SUGGESTIONS = {}
    
    # Load Classifier
    try:
        clf_path = "models/emotion_classifier.pkl"
        if os.path.exists(clf_path):
            data = joblib.load(clf_path)
            CLASSIFIER = data["model"]
            CLASSIFIER_LABELS = data["labels"]
            print("Loaded Emotion Classifier.")
        else:
            print("Classifier not found. Using keyword fallback.")
    except Exception as e:
        print(f"Failed to load classifier: {e}")

    # Pre-compute anchor embeddings (Fallback)
    print("Pre-computing emotion anchors...")
    for emotion, keywords in EMOTION_ANCHORS.items():
        anchor_text = " ".join(keywords)
        embedding, _ = model.encode(anchor_text)
        ANCHOR_EMBEDDINGS[emotion] = embedding
    print(f"Computed {len(ANCHOR_EMBEDDINGS)} anchor embeddings.")

@app.post("/api/context/analyze")
async def analyze_context(request: ContextRequest):
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        if not request.messages:
             return {"emotion": "neutral", "score": 0.0, "suggestions": []}

        last_message = request.messages[-1]
        context_text = " ".join(request.messages)
        
        best_emotion = "neutral"
        best_score = 0.0
        
        # 1. Try Classifier (Primary)
        if CLASSIFIER:
            # Encode last message (Recency Bias)
            embedding, _ = model.encode(last_message)
            embedding = np.array(embedding).reshape(1, -1)
            
            # Predict
            probs = CLASSIFIER.predict_proba(embedding)[0]
            max_idx = np.argmax(probs)
            pred_label = CLASSIFIER_LABELS[max_idx]
            confidence = probs[max_idx]
            
            print(f"Classifier Prediction: {pred_label} ({confidence:.2f})")
            
            if confidence > 0.3:
                # Map to our categories
                mapped_emotion = EMOTION_MAPPING.get(pred_label, "neutral")
                if mapped_emotion != "neutral":
                    best_emotion = mapped_emotion
                    best_score = float(confidence)
        
        # 2. Check Specific Keywords (Coding, Gaming, Waiting, Tired)
        # These are often not covered well by general emotion datasets
        # We check these if the classifier is unsure or predicts "neutral"
        
        special_categories = ["coding", "gaming", "waiting", "tired"]
        
        # If classifier found nothing or neutral, OR if we want to override with specific context
        if best_emotion == "neutral" or best_score < 0.6:
            # Check anchors for special categories
            last_msg_embedding, _ = model.encode(last_message)
            
            for cat in special_categories:
                if cat in ANCHOR_EMBEDDINGS:
                    score = cosine_similarity(last_msg_embedding, ANCHOR_EMBEDDINGS[cat])
                    if score > 0.25 and score > best_score:
                        best_score = score
                        best_emotion = cat
                        print(f"Keyword Override: {cat} ({score:.2f})")

        suggestions = SUGGESTIONS.get(best_emotion, [])
        
        return {
            "emotion": best_emotion,
            "score": float(best_score),
            "suggestions": suggestions
        }
        
    except Exception as e:
        print(f"Error analyzing context: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trending")
async def get_trending(emotion: str = None):
    # If emotion is provided and valid, return suggestions for that emotion as "trending"
    if emotion and emotion in SUGGESTIONS:
        print(f"Returning contextual trending for: {emotion}")
        return {"trending": SUGGESTIONS[emotion]}
    
    # Otherwise return global trending
    return {
        "trending": EMOTION_DATA.get("trending_global", [
            "coding", "cat", "dog", "funny", "reaction", "anime", "gaming", "meme"
        ])
    }

# --- Favorites API ---

class FavoriteGIF(BaseModel):
    id: str
    url: str
    title: str
    preview: str
    width: int = 0
    height: int = 0

FAVORITES_FILE = "data/favorites.json"
FAVORITES_DB = {}

def save_favorites():
    try:
        with open(FAVORITES_FILE, "w") as f:
            json.dump(FAVORITES_DB, f, indent=2)
    except Exception as e:
        print(f"Failed to save favorites: {e}")

@app.on_event("startup")
async def load_favorites():
    global FAVORITES_DB
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, "r") as f:
                FAVORITES_DB = json.load(f)
        else:
            FAVORITES_DB = {}
            # Ensure directory exists
            os.makedirs("data", exist_ok=True)
            save_favorites()
        print(f"Loaded {len(FAVORITES_DB)} favorites.")
    except Exception as e:
        print(f"Failed to load favorites: {e}")
        FAVORITES_DB = {}

@app.get("/api/favorites")
async def get_favorites():
    # Return list of favorites (values of the dict)
    return {"favorites": list(FAVORITES_DB.values())}

@app.post("/api/favorites")
async def add_favorite(gif: FavoriteGIF):
    if gif.id in FAVORITES_DB:
        return {"message": "Already favorited", "favorite": gif}
    
    FAVORITES_DB[gif.id] = gif.dict()
    save_favorites()
    return {"message": "Added to favorites", "favorite": gif}

@app.delete("/api/favorites/{gif_id}")
async def remove_favorite(gif_id: str):
    if gif_id in FAVORITES_DB:
        del FAVORITES_DB[gif_id]
        save_favorites()
        return {"message": "Removed from favorites", "id": gif_id}
    raise HTTPException(status_code=404, detail="Favorite not found")
