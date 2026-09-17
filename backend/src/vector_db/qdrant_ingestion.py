from pathlib import Path
import json
import re
import os
import uuid

from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

EMBEDDINGS_DIR = (
    BASE_DIR
    / "data"
    / "instructor_embeddings"
)

NOTIFICATIONS_FILE = (
    BASE_DIR
    / "data"
    / "output"
    / "notifications.json"
)


# ============================================================
# QDRANT CLOUD ENVIRONMENT
# ============================================================

# Use the .env file that we confirmed is working
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


# ============================================================
# QDRANT CONFIGURATION
# ============================================================

COLLECTION_NAME = "fssai_notifications_instructor"

VECTOR_SIZE = 768

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    check_compatibility=False,
    timeout=120
)


# ============================================================
# HELPER
# ============================================================

def normalize_filename(filename):

    filename = str(filename).lower()

    filename = filename.replace(
        ".pdf",
        ""
    )

    filename = filename.replace(
        ".json",
        ""
    )

    filename = filename.replace(
        "_chunks_embeddings",
        ""
    )

    filename = filename.replace(
        "_instructor_embeddings",
        ""
    )

    filename = re.sub(
        r"[^a-z0-9]+",
        "",
        filename
    )

    return filename


# ============================================================
# LOAD NOTIFICATIONS
# ============================================================

def load_notifications():

    if not NOTIFICATIONS_FILE.exists():

        raise FileNotFoundError(
            f"Notifications file not found:\n"
            f"{NOTIFICATIONS_FILE}"
        )

    data = json.loads(
        NOTIFICATIONS_FILE.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, list):

        raise ValueError(
            "notifications.json must contain a JSON array."
        )

    return data


# ============================================================
# BUILD NOTIFICATION LOOKUP
# ============================================================

def build_notification_lookup(
    notifications
):

    lookup = {}

    for notification in notifications:

        title = (
            notification.get(
                "title",
                ""
            )
            .strip()
        )

        key = normalize_filename(
            title
        )

        lookup.setdefault(
            key,
            []
        ).append(
            notification
        )

    return lookup


# ============================================================
# FIND NOTIFICATION
# ============================================================

def find_notification(
    source_file,
    lookup,
    notifications
):

    normalized_source = normalize_filename(
        source_file
    )

    # --------------------------------------------------------
    # Match title against source filename
    # --------------------------------------------------------

    for key, matches in lookup.items():

        if key and key in normalized_source:

            if len(matches) == 1:

                return matches[0]

            # If multiple titles are similar,
            # use date from filename.

            date_match = re.search(
                r"(\d{2})(\d{2})(\d{4})",
                source_file
            )

            if date_match:

                date = (
                    f"{date_match.group(1)}-"
                    f"{date_match.group(2)}-"
                    f"{date_match.group(3)}"
                )

                for notification in matches:

                    if (
                        notification.get(
                            "uploaded_date"
                        )
                        == date
                    ):

                        return notification

    # --------------------------------------------------------
    # Fallback: match by date
    # --------------------------------------------------------

    date_match = re.search(
        r"(\d{2})(\d{2})(\d{4})",
        source_file
    )

    if date_match:

        date = (
            f"{date_match.group(1)}-"
            f"{date_match.group(2)}-"
            f"{date_match.group(3)}"
        )

        for notification in notifications:

            if (
                notification.get(
                    "uploaded_date"
                )
                == date
            ):

                return notification

    return None


# ============================================================
# MAIN
# ============================================================

def main():
    
        # --------------------------------------------------------
    # Create collection only if it does not exist
    # --------------------------------------------------------

    if client.collection_exists(COLLECTION_NAME):

        print(
            f"\nCollection '{COLLECTION_NAME}' already exists."
        )

        print(
            "Keeping existing collection and vectors."
        )

    else:

        print(
            f"\nCreating collection: {COLLECTION_NAME}"
        )

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense_vec": VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            }
        )

        print(
            "Collection created successfully."
        )

    print("=" * 70)
    print("FSSAI INSTRUCTOR-LARGE QDRANT CLOUD INGESTION")
    print("=" * 70)

    # --------------------------------------------------------
    # Verify Qdrant Cloud credentials
    # --------------------------------------------------------

    print("\nLoading Qdrant Cloud credentials...")

    print(
        f"Environment file: {ENV_FILE}"
    )

    print(
        f"QDRANT URL loaded: "
        f"{bool(QDRANT_URL)}"
    )

    print(
        f"QDRANT API key loaded: "
        f"{bool(QDRANT_API_KEY)}"
    )

    if not QDRANT_URL or not QDRANT_API_KEY:

        raise ValueError(
            "QDRANT_URL or QDRANT_API_KEY not found in "
            "src/tests/.env"
        )

    # --------------------------------------------------------
    # Load notification metadata
    # --------------------------------------------------------

    print(
        "\nLoading notification metadata..."
    )

    notifications = load_notifications()

    print(
        f"Notifications loaded: "
        f"{len(notifications)}"
    )

    notification_lookup = (
        build_notification_lookup(
            notifications
        )
    )

    # --------------------------------------------------------
    # Find INSTRUCTOR embedding files
    # --------------------------------------------------------

    embedding_files = sorted(
        EMBEDDINGS_DIR.rglob(
            "*_instructor_embeddings.json"
        )
    )

    print(
        f"\nINSTRUCTOR embedding files found: "
        f"{len(embedding_files)}"
    )

    if not embedding_files:

        print(
            "ERROR: No INSTRUCTOR embedding files found."
        )

        return

    # --------------------------------------------------------
    # Prepare Qdrant points
    # --------------------------------------------------------

    points = []

    unmatched = 0

    total_chunks = 0

    # --------------------------------------------------------
    # Process embedding files
    # --------------------------------------------------------

    for file_index, embedding_file in enumerate(
        embedding_files,
        start=1
    ):

        print(
            "\n" + "-" * 70
        )

        print(
            f"[{file_index}/{len(embedding_files)}] "
            f"{embedding_file.name}"
        )

        try:

            data = json.loads(
                embedding_file.read_text(
                    encoding="utf-8"
                )
            )

            chunks = data.get(
                "chunks",
                []
            )

            print(
                f"Chunks found: "
                f"{len(chunks)}"
            )

            # ------------------------------------------------
            # Find notification metadata
            # ------------------------------------------------

            source_file = data.get(
                "source_file",
                ""
            )

            notification = (
                find_notification(
                    source_file,
                    notification_lookup,
                    notifications
                )
            )

            if notification:

                print(
                    "Metadata match: YES"
                )

            else:

                print(
                    "Metadata match: NO"
                )

                unmatched += 1

            # ------------------------------------------------
            # Process chunks
            # ------------------------------------------------

            for chunk in chunks:

                vector = chunk.get(
                    "embedding"
                )

                if not vector:

                    continue

                # ------------------------------------------------
                # Verify vector dimension
                # ------------------------------------------------

                if len(vector) != VECTOR_SIZE:

                    raise ValueError(
                        f"Expected vector dimension "
                        f"{VECTOR_SIZE}, got "
                        f"{len(vector)}"
                    )

                # ------------------------------------------------
                # Create payload
                # ------------------------------------------------

                payload = {

                    "chunk_id": chunk.get(
                        "chunk_id"
                    ),

                    "chunk_index": chunk.get(
                        "chunk_index"
                    ),

                    "text": chunk.get(
                        "text"
                    ),

                    "source_file": source_file,

                    "page_count": chunk.get(
                        "page_count"
                    ),

                    "embedding_model": data.get(
                        "embedding_model"
                    ),

                    "embedding_dimension": data.get(
                        "embedding_dimension"
                    ),

                    "embedding_instruction": data.get(
                        "embedding_instruction"
                    ),

                    # Notification metadata
                    "title": (
                        notification.get(
                            "title"
                        )
                        if notification
                        else ""
                    ),

                    "uploaded_date": (
                        notification.get(
                            "uploaded_date"
                        )
                        if notification
                        else ""
                    ),

                    "Month": (
                        notification.get(
                            "Month"
                        )
                        if notification
                        else ""
                    ),

                    "Year": (
                        notification.get(
                            "Year"
                        )
                        if notification
                        else None
                    ),

                    "pdf_url": (
                        notification.get(
                            "pdf_url"
                        )
                        if notification
                        else ""
                    )
                }

                point_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{payload['uploaded_date']}|{payload['title']}|{payload['chunk_index']}"
                    )
                )
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector={"dense_vec": vector},
                        payload=payload
                    )
                )


                total_chunks += 1

        except Exception as exc:

            print(
                f"FAILED: {exc}"
            )

    # --------------------------------------------------------
    # Upload points to Qdrant Cloud
    # --------------------------------------------------------

    print("\n")

    print(
        f"Total points prepared: "
        f"{len(points)}"
    )

    BATCH_SIZE = 50

    for start in range(
        0,
        len(points),
        BATCH_SIZE
    ):

        batch = points[
            start:start + BATCH_SIZE
        ]

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch
        )

        print(
            f"Uploaded points "
            f"{start + 1}-"
            f"{start + len(batch)}"
        )

    # --------------------------------------------------------
    # Verify collection
    # --------------------------------------------------------

    collection_info = (
        client.get_collection(
            COLLECTION_NAME
        )
    )

    print("\n")

    print("=" * 70)
    print("INSTRUCTOR QDRANT CLOUD INGESTION COMPLETE")
    print("=" * 70)

    print(
        f"Collection: "
        f"{COLLECTION_NAME}"
    )

    print(
        f"Vector size: "
        f"{VECTOR_SIZE}"
    )

    print(
        "Distance: Cosine"
    )

    print(
        f"Points prepared: "
        f"{len(points)}"
    )

    print(
        f"Points stored: "
        f"{collection_info.points_count}"
    )

    print(
        f"Unmatched metadata files: "
        f"{unmatched}"
    )

    print("=" * 70)

    client.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()