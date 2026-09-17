import os
import json

EXTRACTED_DIR = "data/extracted"
CHUNKS_DIR = "data/chunks"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []

    start = 0
    chunk_index = 1

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]

        if chunk.strip():
            chunks.append({
                "chunk_id": f"chunk_{chunk_index:04d}",
                "chunk_index": chunk_index,
                "text": chunk
            })

        if end >= len(text):
            break

        start = end - overlap
        chunk_index += 1

    return chunks


def process_file(filename):
    input_path = os.path.join(EXTRACTED_DIR, filename)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("text", "")
    page_count = data.get("page_count", 0)
    source_file = data.get("file_name", filename)

    chunks = chunk_text(text)

    output = {
        "source_file": source_file,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "chunk_count": len(chunks),
        "chunks": []
    }

    for chunk in chunks:
        output["chunks"].append({
            "chunk_id": f"{source_file}_chunk_{chunk['chunk_index']:04d}",
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
            "source_file": source_file,
            "page_count": page_count
        })

    output_filename = os.path.splitext(filename)[0] + "_chunks.json"
    output_path = os.path.join(CHUNKS_DIR, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(
        f"Created: {output_filename} | "
        f"Chunks: {len(chunks)}"
    )


def main():
    os.makedirs(CHUNKS_DIR, exist_ok=True)

    files = [
        f for f in os.listdir(EXTRACTED_DIR)
        if f.endswith(".json")
    ]

    print(f"Extracted JSON files found: {len(files)}")

    for filename in files:
        process_file(filename)

    print("\nChunking completed.")


if __name__ == "__main__":
    main()