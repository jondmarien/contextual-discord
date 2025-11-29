from fastapi import FastAPI

app = FastAPI(title="AI GIF Picker API")

@app.get("/")
async def root():
    return {"message": "Contextual Discord API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
