from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

app = FastAPI()

# Allow React frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Go from:
# data/backend/main.py
# up to data/
DATA_DIR = Path(__file__).resolve().parent.parent

# Extracted JSON files are here:
# data/extracted/
EXTRACTED_DIR = DATA_DIR / "extracted"


@app.get("/")
def home():
    return {
        "message": "FSSAI Notification Backend is running"
    }


@app.get("/api/notification/{file_name}")
def get_notification(file_name: str):

    file_path = EXTRACTED_DIR / file_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Extracted JSON file not found: {file_name}"
        )

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )