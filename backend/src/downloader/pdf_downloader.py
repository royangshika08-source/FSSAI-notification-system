import json
import os
import re
import requests
from urllib.parse import unquote


# ============================================================
# FSSAI PDF DOWNLOADER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

INPUT_JSON = os.path.join(
    BASE_DIR,
    "data",
    "output",
    "notifications.json"
)

PDF_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "pdfs"
)

DOWNLOAD_LOG = os.path.join(
    BASE_DIR,
    "data",
    "output",
    "pdf_downloads.json"
)


FSSAI_PAGE = (
    "https://www.fssai.gov.in/"
    "food-law/notifications?notification=gazette-notification"
)


# ============================================================
# CREATE OUTPUT FOLDER
# ============================================================

os.makedirs(PDF_FOLDER, exist_ok=True)


# ============================================================
# LOAD NOTIFICATIONS JSON
# ============================================================

print("=" * 70)
print("FSSAI PDF DOWNLOADER")
print("=" * 70)

print("\nLoading notifications JSON...")

if not os.path.exists(INPUT_JSON):
    print(f"ERROR: JSON file not found:")
    print(INPUT_JSON)
    raise SystemExit(1)

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    notifications = json.load(f)


print(f"Notifications found: {len(notifications)}")


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/pdf,"
        "application/octet-stream,"
        "text/html;q=0.9,*/*;q=0.8"
    ),
    "Referer": FSSAI_PAGE,
    "Connection": "keep-alive"
})


# ============================================================
# HELPER: CLEAN FILE NAME
# ============================================================

def clean_filename(text):
    """
    Convert notification title into a safe Windows filename.
    """

    text = unquote(str(text))

    # Remove Windows-invalid filename characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)

    # Replace multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Limit filename length
    text = text.strip()[:100]

    return text


# ============================================================
# DOWNLOAD FUNCTION
# ============================================================

def download_pdf(url, output_path):

    try:

        response = session.get(
            url,
            timeout=60,
            allow_redirects=True
        )

        print(f"    HTTP status: {response.status_code}")
        print(f"    Final URL: {response.url}")

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        # ----------------------------------------------------
        # Check actual PDF signature
        # A real PDF normally starts with %PDF
        # ----------------------------------------------------

        if not response.content.startswith(b"%PDF"):

            print(
                f"    WARNING: Response is not a PDF."
            )
            print(
                f"    Content-Type: {content_type}"
            )

            return False, "Response is not a PDF"

        # ----------------------------------------------------
        # Save PDF
        # ----------------------------------------------------

        with open(output_path, "wb") as f:
            f.write(response.content)

        file_size = os.path.getsize(output_path)

        if file_size == 0:
            return False, "Downloaded file is empty"

        return True, f"{file_size / 1024 / 1024:.2f} MB"

    except requests.RequestException as e:

        return False, str(e)

    except Exception as e:

        return False, str(e)


# ============================================================
# PROCESS NOTIFICATIONS
# ============================================================

download_results = []

successful = 0
failed = 0


for index, notification in enumerate(notifications, start=1):

    title = notification.get("title", "").strip()
    uploaded_date = notification.get("uploaded_date", "").strip()
    pdf_url = notification.get("pdf_url", "").strip()

    print("\n" + "-" * 70)

    print(
        f"[{index}/{len(notifications)}] "
        f"{uploaded_date}"
    )

    print(f"Title: {title}")

    # --------------------------------------------------------
    # Check URL
    # --------------------------------------------------------

    if not pdf_url:

        print("    ERROR: PDF URL is empty")

        download_results.append({
            "title": title,
            "uploaded_date": uploaded_date,
            "pdf_url": pdf_url,
            "status": "failed",
            "error": "Empty PDF URL"
        })

        failed += 1
        continue

    print(f"PDF URL: {pdf_url}")

    # --------------------------------------------------------
    # Create unique filename
    # --------------------------------------------------------

    safe_title = clean_filename(title)

    filename = (
        f"{uploaded_date.replace('-', '')}_"
        f"{safe_title}.pdf"
    )

    output_path = os.path.join(
        PDF_FOLDER,
        filename
    )

    output_path = os.path.join(
        PDF_FOLDER,
        filename
    )

    print(f"Saving as: {filename}")

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------
    if os.path.exists(output_path):

        print("    PDF already exists - reusing existing file")

        download_results.append({
            "title": title,
            "uploaded_date": uploaded_date,
            "Month": notification.get("Month"),
            "Year": notification.get("Year"),
            "pdf_url": pdf_url,
            "file_name": filename,
            "local_path": output_path,
            "status": "already_exists"
})

    successful += 1

    continue

    success, message = download_pdf(
        pdf_url,
        output_path
    )

    if success:

        print(f"    SUCCESS: PDF downloaded")
        print(f"    Size: {message}")

        download_results.append({
            "title": title,
            "uploaded_date": uploaded_date,
            "Month": notification.get("Month"),
            "Year": notification.get("Year"),
            "pdf_url": pdf_url,
            "file_name": filename,
            "local_path": output_path,
            "status": "downloaded"
        })

        successful += 1

    else:

        print(f"    FAILED: {message}")

        download_results.append({
            "title": title,
            "uploaded_date": uploaded_date,
            "Month": notification.get("Month"),
            "Year": notification.get("Year"),
            "pdf_url": pdf_url,
            "file_name": filename,
            "local_path": output_path,
            "status": "failed",
            "error": message
        })

        failed += 1


# ============================================================
# SAVE DOWNLOAD LOG
# ============================================================

with open(
    DOWNLOAD_LOG,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        download_results,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("PDF DOWNLOAD COMPLETE")
print("=" * 70)

print(f"Total notifications : {len(notifications)}")
print(f"Successfully downloaded : {successful}")
print(f"Failed : {failed}")

print("\nPDF folder:")
print(PDF_FOLDER)

print("\nDownload log:")
print(DOWNLOAD_LOG)

print("=" * 70)