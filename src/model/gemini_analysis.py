import os
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from google import genai
from google.genai import types


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]


# ============================================================
# ENVIRONMENT
# ============================================================

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


# ============================================================
# CONFIGURATION
# ============================================================

EMBEDDING_MODEL = "hkunlp/instructor-large"

COLLECTION_NAME = "fssai_notifications_instructor"

TOP_K = 5

QUERY_INSTRUCTION = (
    "Represent the question for retrieving "
    "relevant FSSAI regulatory documents:"
)

GEMINI_MODEL = "gemini-3.5-flash"


# ============================================================
# VALIDATE CREDENTIALS
# ============================================================

print("=" * 70)
print("FSSAI GEMINI REGULATORY ANALYSIS")
print("=" * 70)

print("\nLoading credentials...")

print(
    "GEMINI API key loaded:",
    bool(GEMINI_API_KEY)
)

print(
    "QDRANT URL loaded:",
    bool(QDRANT_URL)
)

print(
    "QDRANT API key loaded:",
    bool(QDRANT_API_KEY)
)

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found in .env"
    )

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError(
        "QDRANT_URL or QDRANT_API_KEY not found in .env"
    )


# ============================================================
# INITIALIZE CLIENTS
# ============================================================

print("\nLoading embedding model...")

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

print("INSTRUCTOR-large loaded.")


print("\nConnecting to Qdrant Cloud...")

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

print("Qdrant Cloud connection established.")


print("\nConnecting to Gemini...")

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)

print("Gemini client initialized.")


# ============================================================
# QDRANT RETRIEVAL
# ============================================================

def retrieve_chunks(query):

    query_pair = [
        QUERY_INSTRUCTION,
        query
    ]

    print("\nGenerating query embedding...")

    query_vector = embedding_model.encode(
        [query_pair],
        normalize_embeddings=True
    )[0].tolist()

    print(
        "Query vector dimension:",
        len(query_vector)
    )

    print(
        f"Searching Qdrant for top {TOP_K} results..."
    )

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=TOP_K,
        with_payload=True
    ).points

    print(
        f"Retrieved {len(results)} chunks."
    )

    return results


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_with_gemini(
    user_query,
    retrieved_results
):

    context_parts = []

    for index, result in enumerate(
        retrieved_results,
        start=1
    ):

        payload = result.payload or {}

        context_parts.append(
            f"""
--- RETRIEVED CHUNK {index} ---

Similarity score:
{result.score}

Notification title:
{payload.get("title", "")}

Uploaded date:
{payload.get("uploaded_date", "")}

Month:
{payload.get("Month", "")}

Year:
{payload.get("Year", "")}

PDF URL:
{payload.get("pdf_url", "")}

Chunk ID:
{payload.get("chunk_id", "")}

Chunk text:
{payload.get("text", "")}
"""
        )

    retrieved_context = "\n".join(
        context_parts
    )

    prompt = f"""
You are analyzing official FSSAI notification documents
retrieved from a vector database.

USER QUESTION:
{user_query}

RETRIEVED DOCUMENT CHUNKS:
{retrieved_context}

Your task is to analyze ONLY the information contained
in the retrieved FSSAI notification chunks.

Perform ALL of the following tasks in ONE model call:

1. Identify all notification(s) that are relevant to
   the user's question.

2. Summarize the relevant notification content accurately.

3. Identify ALL distinct areas that are affected by the
   relevant notification(s).

4. Do NOT use a predefined or fixed list of affected
   areas. Identify the affected areas dynamically from
   the actual notification content.

5. Include every meaningful affected area that can be
   supported by the retrieved document chunks.

6. If one notification affects multiple areas, include
   all of those areas.

7. Do not limit the number of affected areas.

8. Do not invent an affected area that is not supported
   by the retrieved document text.

9. Also identify the actual change or changes described
   in the notification, when the retrieved text provides
   enough information to do so.

10. If the retrieved chunks do not contain enough
    information to identify a notification, affected
    area, or change, clearly state that instead of
    guessing.

Return the result as structured JSON.
"""

    response_schema = {
        "type": "object",
        "properties": {

            "relevant_notifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "title": {
                            "type": "string"
                        },

                        "uploaded_date": {
                            "type": "string"
                        },

                        "pdf_url": {
                            "type": "string"
                        }
                    },

                    "required": [
                        "title",
                        "uploaded_date",
                        "pdf_url"
                    ]
                }
            },

            "summary": {
                "type": "string"
            },

            "affected_areas": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "detected_changes": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },

        "required": [
            "relevant_notifications",
            "summary",
            "affected_areas",
            "detected_changes"
        ]
    }

    print("\nCalling Gemini...")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        )
    )

    return response.text


# ============================================================
# MAIN
# ============================================================

def main():

    query = input(
        "\nEnter your question:\n> "
    ).strip()

    if not query:

        print("No query entered.")
        return

    # --------------------------------------------------------
    # Retrieve relevant chunks
    # --------------------------------------------------------

    results = retrieve_chunks(
        query
    )

    if not results:

        print(
            "\nNo relevant chunks found."
        )

        return

    # --------------------------------------------------------
    # Gemini analysis
    # --------------------------------------------------------

    analysis = analyze_with_gemini(
        query,
        results
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("GEMINI ANALYSIS")
    print("=" * 70)

    print(analysis)

    print("\n")
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()