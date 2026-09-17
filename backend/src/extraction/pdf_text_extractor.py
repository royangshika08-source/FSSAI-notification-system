from pathlib import Path
import fitz
import json


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PDF_DIR = BASE_DIR / "data" / "pdfs"

OUTPUT_DIR = BASE_DIR / "data" / "extracted"

DOWNLOAD_LOG = (
    BASE_DIR
    / "data"
    / "output"
    / "pdf_downloads.json"
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# TEXT EXTRACTION FUNCTION
# ============================================================

def extract_text_from_pdf(pdf_path):

    document = fitz.open(pdf_path)

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        text = page.get_text(
            "text"
        )

        pages.append(
            {
                "page_number": page_number,
                "text": text.strip()
            }
        )

    document.close()

    return pages


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("FSSAI PDF TEXT EXTRACTOR")
    print("=" * 70)

    # --------------------------------------------------------
    # Check PDF folder
    # --------------------------------------------------------

    if not PDF_DIR.exists():

        print(
            "ERROR: PDF folder not found:"
        )

        print(PDF_DIR)

        return

    # --------------------------------------------------------
    # Find PDFs
    # --------------------------------------------------------

    pdf_files = sorted(
        PDF_DIR.glob("*.pdf")
    )

    print(
        f"\nPDF files found: {len(pdf_files)}"
    )

    if not pdf_files:

        print(
            "No PDF files found."
        )

        return

    successful = 0
    failed = 0

    # --------------------------------------------------------
    # Process each PDF
    # --------------------------------------------------------

    for index, pdf_path in enumerate(
        pdf_files,
        start=1
    ):

        print("\n" + "-" * 70)

        print(
            f"[{index}/{len(pdf_files)}] "
            f"{pdf_path.name}"
        )

        try:

            pages = extract_text_from_pdf(
                pdf_path
            )

            # ------------------------------------------------
            # Combine page text
            # ------------------------------------------------

            full_text = "\n\n".join(
                page["text"]
                for page in pages
            )

            # ------------------------------------------------
            # Output JSON filename
            # ------------------------------------------------

            output_file = (
                OUTPUT_DIR
                / f"{pdf_path.stem}.json"
            )

            result = {
                "file_name": pdf_path.name,
                "page_count": len(pages),
                "text": full_text,
                "pages": pages
            }

            output_file.write_text(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            print(
                f"    Pages extracted: {len(pages)}"
            )

            print(
                f"    Characters extracted: "
                f"{len(full_text)}"
            )

            print(
                f"    Saved to: {output_file}"
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
    print("TEXT EXTRACTION COMPLETE")
    print("=" * 70)

    print(
        f"Total PDFs: {len(pdf_files)}"
    )

    print(
        f"Successfully extracted: {successful}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"\nExtracted files:"
    )

    print(
        OUTPUT_DIR
    )

    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()