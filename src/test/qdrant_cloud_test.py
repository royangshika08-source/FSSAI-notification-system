import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


print("QDRANT URL loaded:", bool(QDRANT_URL))
print("QDRANT API key loaded:", bool(QDRANT_API_KEY))


if not QDRANT_URL or not QDRANT_API_KEY:
    print("\nERROR: Qdrant credentials not found in .env")
    raise SystemExit(1)


# Connect to Qdrant Cloud
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)


# Test connection
collections = client.get_collections()


print("\nQDRANT CLOUD CONNECTION SUCCESSFUL!")
print("Existing collections:")

for collection in collections.collections:
    print("-", collection.name)



client.close()