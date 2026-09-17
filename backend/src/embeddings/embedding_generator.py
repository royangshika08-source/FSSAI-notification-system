from pathlib import Path
import json

from sentence_transformers import SentenceTransformer


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CHUNKS_DIR = (
    BASE_DIR
    / "data"
    / "chunks"
)

EMBEDDINGS_DIR = (
    BASE_DIR
    / "data"
    / "embeddings"
)


# ============================================================
# EMBEDDING MODEL
# ============================================================

MODEL_NAME = "all-MiniLM-L6-v2"


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

EMBEDDINGS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("FSSAI EMBEDDING GENERATOR")
    print("=" * 70)

    print(
        f"\nLoading embedding model: "
        f"{MODEL_NAME}"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    print("Embedding model loaded.")

    # --------------------------------------------------------
    # Find chunk files
    # --------------------------------------------------------

    chunk_files = sorted(
        CHUNKS_DIR.rglob(
            "*_chunks.json"
        )
    )

    print(
        f"\nChunk files found: "
        f"{len(chunk_files)}"
    )

    if not chunk_files:

        print(
            "ERROR: No chunk files found."
        )

        return

    total_chunks = 0
    successful = 0
    failed = 0

    # --------------------------------------------------------
    # Process every chunk file
    # --------------------------------------------------------

    for index, chunk_file in enumerate(
        chunk_files,
        start=1
    ):

        print("\n" + "-" * 70)

        print(
            f"[{index}/{len(chunk_files)}] "
            f"{chunk_file.name}"
        )

        try:

            data = json.loads(
                chunk_file.read_text(
                    encoding="utf-8"
                )
            )

            chunks = data.get(
                "chunks",
                []
            )

            if not chunks:

                print(
                    "    WARNING: No chunks found."
                )

                continue

            # ------------------------------------------------
            # Extract chunk text
            # ------------------------------------------------

            texts = [
                chunk["text"]
                for chunk in chunks
            ]

            # ------------------------------------------------
            # Generate embeddings
            # ------------------------------------------------

            vectors = model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # ------------------------------------------------
            # Attach vector to each chunk
            # ------------------------------------------------

            embedded_chunks = []

            for chunk, vector in zip(
                chunks,
                vectors
            ):

                embedded_chunks.append(
                    {
                        **chunk,
                        "embedding": vector.tolist()
                    }
                )

            # ------------------------------------------------
            # Final output
            # ------------------------------------------------

            output = {
                "source_file": data.get(
                    "source_file",
                    ""
                ),
                "chunk_size": data.get(
                    "chunk_size",
                    1000
                ),
                "chunk_overlap": data.get(
                    "chunk_overlap",
                    200
                ),
                "embedding_model": MODEL_NAME,
                "embedding_dimension": int(
                    vectors.shape[1]
                ),
                "chunk_count": len(
                    embedded_chunks
                ),
                "chunks": embedded_chunks
            }

            output_file = (
                EMBEDDINGS_DIR
                / f"{chunk_file.stem}_embeddings.json"
            )

            output_file.write_text(
                json.dumps(
                    output,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            print(
                f"    Chunks embedded: "
                f"{len(embedded_chunks)}"
            )

            print(
                f"    Vector dimension: "
                f"{vectors.shape[1]}"
            )

            print(
                f"    Saved to: "
                f"{output_file}"
            )

            total_chunks += len(
                embedded_chunks
            )

            successful += 1

        except Exception as exc:

            print(
                f"    FAILED: {exc}"
            )

            failed += 1

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")

    print("=" * 70)
    print("EMBEDDING GENERATION COMPLETE")
    print("=" * 70)

    print(
        f"Chunk files processed: "
        f"{len(chunk_files)}"
    )

    print(
        f"Successfully processed: "
        f"{successful}"
    )

    print(
        f"Failed: "
        f"{failed}"
    )

    print(
        f"Total chunks embedded: "
        f"{total_chunks}"
    )

    print(
        f"Embedding model: "
        f"{MODEL_NAME}"
    )

    print(
        f"Embeddings saved to:"
    )

    print(
        EMBEDDINGS_DIR
    )

    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()