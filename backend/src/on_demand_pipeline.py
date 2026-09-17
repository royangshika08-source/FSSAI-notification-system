"""Download and extract a single FSSAI notification PDF on demand.

Used when a user selects a notification that has not already been
downloaded/extracted by the batch pipeline (backend/src/downloader and
backend/src/extraction), so that AI analysis works for any notification
returned by the scraper, not only the pre-processed sample set.
"""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from src.extraction.pdf_text_extractor import extract_text_from_pdf


BASE_DIR = Path(__file__).resolve().parent.parent.parent

PDF_DIR = BASE_DIR / "data" / "pdfs"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted"

PDF_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

# PDFs are only ever fetched from the official FSSAI domain, even though the
# URL is supplied by the client, to avoid the backend being used to fetch
# arbitrary attacker-supplied URLs (SSRF).
ALLOWED_PDF_HOST_SUFFIX = "fssai.gov.in"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,text/html;q=0.9,*/*;q=0.8",
    "Referer": "https://www.fssai.gov.in/",
}


def clean_filename(text):
    text = unquote(str(text or ""))
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:100]


def build_file_stem(title, uploaded_date):
    safe_title = clean_filename(title)
    safe_date = re.sub(r"[^0-9]", "", uploaded_date or "")
    return f"{safe_date}_{safe_title}".strip("_") or "notification"


def is_allowed_pdf_url(pdf_url):
    try:
        host = (urlparse(pdf_url).hostname or "").lower()
    except ValueError:
        return False

    return bool(host) and host.endswith(ALLOWED_PDF_HOST_SUFFIX)


def download_pdf(pdf_url, destination):
    if not is_allowed_pdf_url(pdf_url):
        raise ValueError("Refusing to download a PDF from an untrusted host")

    response = requests.get(
        pdf_url,
        timeout=60,
        allow_redirects=True,
        headers=REQUEST_HEADERS,
    )
    response.raise_for_status()

    if not response.content.startswith(b"%PDF"):
        raise ValueError("The FSSAI source did not return a PDF file")

    destination.write_bytes(response.content)


def ensure_extracted_notification(title, uploaded_date, pdf_url):
    """Return extracted text for a notification, downloading/extracting first if needed.

    Returns a dict shaped like the batch pipeline's extracted JSON:
    {"file_name", "page_count", "text", "pages"}.
    """
    file_stem = build_file_stem(title, uploaded_date)
    extracted_path = EXTRACTED_DIR / f"{file_stem}.json"

    if extracted_path.exists():
        return json.loads(extracted_path.read_text(encoding="utf-8"))

    if not pdf_url:
        raise ValueError("No PDF URL was supplied for this notification")

    pdf_path = PDF_DIR / f"{file_stem}.pdf"

    if not pdf_path.exists():
        download_pdf(pdf_url, pdf_path)

    pages = extract_text_from_pdf(pdf_path)
    full_text = "\n\n".join(page["text"] for page in pages)

    result = {
        "file_name": pdf_path.name,
        "page_count": len(pages),
        "text": full_text,
        "pages": pages,
    }

    extracted_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return result
