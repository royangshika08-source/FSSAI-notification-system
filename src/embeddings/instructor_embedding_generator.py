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

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "instructor_embeddings"
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "hkunlp/instructor-large"

DOCUMENT_INSTRUCTION = (
    "Represent the FSSAI regulatory document "
    "for retrieval:"
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("FSSAI INSTRUCTOR-LARGE EMBEDDING GENERATOR")
    print("=" * 70)

    # --------------------------------------------------------
    # Load model
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
    vector_dimension = None

    # --------------------------------------------------------
    # Process each document
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

            print(
                f"Generating embeddings for "
                f"{len(chunks)} chunks..."
            )

            if not chunks:

                print(
                    "WARNING: No chunks found."
                )

                continue

            # ------------------------------------------------
            # INSTRUCTOR format
            #
            # Each item is:
            # [instruction, document text]
            # ------------------------------------------------

            instruction_pairs = [
                [
                    DOCUMENT_INSTRUCTION,
                    chunk.get(
                        "text",
                        ""
                    )
                ]
                for chunk in chunks
            ]

            # ------------------------------------------------
            # Generate embeddings
            # ------------------------------------------------

            vectors = model.encode(
                instruction_pairs,
                batch_size=4,
                show_progress_bar=True,
                normalize_embeddings=True
            )

            # ------------------------------------------------
            # Determine dimension
            # ------------------------------------------------

            current_dimension = len(
                vectors[0]
            )

            if vector_dimension is None:

                vector_dimension = (
                    current_dimension
                )

            # ------------------------------------------------
            # Add embeddings to chunks
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
            # Create output
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

                "embedding_instruction": (
                    DOCUMENT_INSTRUCTION
                ),

                "embedding_dimension": (
                    vector_dimension
                ),

                "chunk_count": len(
                    embedded_chunks
                ),

                "chunks": embedded_chunks
            }

            # ------------------------------------------------
            # Save
            # ------------------------------------------------

            output_file = (
                OUTPUT_DIR
                / f"{chunk_file.stem}"
                f"_instructor_embeddings.json"
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
                f"Chunks embedded: "
                f"{len(embedded_chunks)}"
            )

            print(
                f"Vector dimension: "
                f"{current_dimension}"
            )

            print(
                f"Saved to: "
                f"{output_file}"
            )

            total_chunks += len(
                embedded_chunks
            )

            successful += 1

        except Exception as exc:

            print(
                f"FAILED: {exc}"
            )

            failed += 1

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")

    print("=" * 70)
    print(
        "INSTRUCTOR EMBEDDING GENERATION COMPLETE"
    )
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
        f"Vector dimension: "
        f"{vector_dimension}"
    )

    print(
        "\nEmbeddings saved to:"
    )

    print(
        OUTPUT_DIR
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()