import os
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]


# ============================================================
# QDRANT CLOUD ENVIRONMENT
# ============================================================

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "hkunlp/instructor-large"

COLLECTION_NAME = (
    "fssai_notifications_instructor"
)

TOP_K = 5

QUERY_INSTRUCTION = (
    "Represent the question for retrieving "
    "relevant FSSAI regulatory documents:"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("FSSAI INSTRUCTOR-LARGE QDRANT CLOUD SEMANTIC SEARCH")
    print("=" * 70)

    # --------------------------------------------------------
    # Check Qdrant credentials
    # --------------------------------------------------------

    print("\nLoading Qdrant Cloud credentials...")

    print(
        f"QDRANT URL loaded: "
        f"{bool(QDRANT_URL)}"
    )

    print(
        f"QDRANT API key loaded: "
        f"{bool(QDRANT_API_KEY)}"
    )

    if not QDRANT_URL or not QDRANT_API_KEY:

        print(
            "\nERROR: Qdrant Cloud credentials "
            "not found in .env"
        )

        return

    # --------------------------------------------------------
    # Load INSTRUCTOR-large
    # --------------------------------------------------------

    print(
        f"\nLoading model: {MODEL_NAME}"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    print(
        "INSTRUCTOR-large loaded."
    )

    # --------------------------------------------------------
    # Connect to Qdrant Cloud
    # --------------------------------------------------------

    print(
        "\nConnecting to Qdrant Cloud..."
    )

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        check_compatibility=False,
        timeout=120
    )

    print(
        "Qdrant Cloud connection established."
    )

    # --------------------------------------------------------
    # Check collection
    # --------------------------------------------------------

    if not client.collection_exists(
        COLLECTION_NAME
    ):

        print(
            f"ERROR: Collection "
            f"'{COLLECTION_NAME}' not found."
        )

        client.close()
        return

    collection_info = (
        client.get_collection(
            COLLECTION_NAME
        )
    )

    print(
        f"\nCollection: "
        f"{COLLECTION_NAME}"
    )

    print(
        f"Points available: "
        f"{collection_info.points_count}"
    )

    # --------------------------------------------------------
    # Get user query
    # --------------------------------------------------------

    query = input(
        "\nEnter your search question:\n> "
    ).strip()

    if not query:

        print(
            "No query entered."
        )

        client.close()
        return

    # --------------------------------------------------------
    # INSTRUCTOR query format
    # --------------------------------------------------------

    query_pair = [
        QUERY_INSTRUCTION,
        query
    ]

    print(
        "\nGenerating query embedding..."
    )

    query_vector = model.encode(
        [query_pair],
        normalize_embeddings=True
    )[0].tolist()

    print(
        f"Query vector dimension: "
        f"{len(query_vector)}"
    )

    # --------------------------------------------------------
    # Search Qdrant Cloud
    # --------------------------------------------------------

    print(
        "Searching Qdrant Cloud..."
    )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        using= "dense_vec",
        limit=TOP_K,
        with_payload=True
    ).points

    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    print("\n")

    print("=" * 70)
    print("SEARCH RESULTS")
    print("=" * 70)

    if not results:

        print(
            "No results found."
        )

        client.close()
        return

    for index, result in enumerate(
        results,
        start=1
    ):

        payload = (
            result.payload
            or {}
        )

        print(
            f"\nRESULT {index}"
        )

        print(
            "-" * 70
        )

        print(
            f"Score: "
            f"{result.score:.4f}"
        )

        print(
            f"Title: "
            f"{payload.get('title', '')}"
        )

        print(
            f"Uploaded date: "
            f"{payload.get('uploaded_date', '')}"
        )

        print(
            f"Month: "
            f"{payload.get('Month', '')}"
        )

        print(
            f"Year: "
            f"{payload.get('Year', '')}"
        )

        print(
            f"Chunk ID: "
            f"{payload.get('chunk_id', '')}"
        )

        print(
            f"PDF URL: "
            f"{payload.get('pdf_url', '')}"
        )

        print(
            "\nChunk text:"
        )

        print(
            payload.get(
                "text",
                ""
            )
        )

    print("\n")

    print("=" * 70)
    print("SEMANTIC SEARCH COMPLETE")
    print("=" * 70)

    client.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()