from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
import json
import time
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
)


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

SOURCE_URL = (
    "https://www.fssai.gov.in/"
    "food-law/notifications?notification=gazette-notification"
)

BASE_URL = "https://www.fssai.gov.in/"


DEFAULT_START_DATE = datetime.strptime(
    "01-12-2025",
    "%d-%m-%Y"
).date()

DEFAULT_END_DATE = datetime.strptime(
    "31-05-2026",
    "%d-%m-%Y"
).date()


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

OUTPUT_FILE = OUTPUT_DIR / "notifications.json"


# ============================================================
# BROWSER SETUP
# ============================================================

def create_driver():

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    return webdriver.Chrome(
        options=options
    )


# ============================================================
# WAIT FOR FSSAI PAGE
# ============================================================

def wait_for_table(driver):

    WebDriverWait(
        driver,
        30
    ).until(
        lambda d: (
            "S.NO." in
            d.find_element(
                By.TAG_NAME,
                "body"
            ).text
            and
            "DOWNLOAD" in
            d.find_element(
                By.TAG_NAME,
                "body"
            ).text
        )
    )


# ============================================================
# EXTRACT CURRENT PAGE
# ============================================================

def extract_current_page(
    driver,
    page_number,
    start_date,
    end_date,
    save_raw=True,
):

    wait_for_table(driver)

    # --------------------------------------------------------
    # Save rendered HTML for debugging/audit
    # --------------------------------------------------------

    if save_raw:
        html = driver.page_source

        RAW_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        raw_file = (
            RAW_DIR
            / f"gazette_page_{page_number}.html"
        )

        raw_file.write_text(
            html,
            encoding="utf-8"
        )

    # --------------------------------------------------------
    # Get PDF links directly from the browser DOM.
    #
    # We use JavaScript here instead of assuming a fixed
    # parent/child structure for the FSSAI page.
    # --------------------------------------------------------

    link_data = driver.execute_script(
        """
        const anchors = Array.from(
            document.querySelectorAll("a[href]")
        );

        function findNotificationContainer(anchor) {

            let current = anchor;

            for (let i = 0; i < 8 && current; i++) {

                const text =
                    (current.innerText || "").trim();

                if (
                    /\\b\\d{2}-\\d{2}-\\d{4}\\b/.test(text)
                ) {
                    return text;
                }

                current = current.parentElement;
            }

            return "";
        }

        return anchors.map(anchor => {

            return {
                href: anchor.href || "",
                text: (anchor.innerText || "").trim(),
                row_text: findNotificationContainer(anchor)
            };

        });
        """
    )

    print(
        f"  Total links on page: {len(link_data)}"
    )

    records = []

    # --------------------------------------------------------
    # PROCESS EACH LINK
    # --------------------------------------------------------

    for item in link_data:

        href = (
            item.get("href") or ""
        ).strip()

        link_text = (
            item.get("text") or ""
        ).strip()

        row_text = (
            item.get("row_text") or ""
        ).strip()

        # ----------------------------------------------------
        # Only PDF/download links
        # ----------------------------------------------------

        if not href:
            continue

        if (
            ".pdf" not in href.lower()
            and "pdf" not in link_text.lower()
        ):
            continue

        # ----------------------------------------------------
        # If no notification container was found,
        # skip it rather than inventing a record.
        # ----------------------------------------------------

        if not row_text:
            continue

        # ----------------------------------------------------
        # Extract date
        # ----------------------------------------------------

        date_match = re.search(
            r"\b\d{2}-\d{2}-\d{4}\b",
            row_text
        )

        if not date_match:
            continue

        uploaded_date = date_match.group(0)

        try:

            parsed_date = datetime.strptime(
                uploaded_date,
                "%d-%m-%Y"
            ).date()

        except ValueError:

            continue

        # ----------------------------------------------------
        # Required date range
        # ----------------------------------------------------
        if not (
            start_date
            <= parsed_date
            <= end_date
        ):
            continue

        # ----------------------------------------------------
        # Extract title
        # ----------------------------------------------------

        title_text = row_text

        # Remove serial number
        title_text = re.sub(
            r"^\s*\d+\s*",
            "",
            title_text
        )

        # Remove date
        title_text = re.sub(
            r"\b\d{2}-\d{2}-\d{4}\b",
            "",
            title_text,
            count=1
        )

        # Remove PDF size
        title_text = re.sub(
            r"PDF\s*\[[^\]]*\]",
            "",
            title_text,
            flags=re.IGNORECASE
        )

        # Remove standalone PDF
        title_text = re.sub(
            r"\bPDF\b",
            "",
            title_text,
            flags=re.IGNORECASE
        )

        # Normalize whitespace
        title_text = re.sub(
            r"\s+",
            " ",
            title_text
        ).strip()

        # EXACT PDF URL FROM FSSAI
        # Keep the complete href exactly as Selenium received it.

        if href.startswith("http://") or href.startswith("https://"):
            pdf_url = href
        else:
            pdf_url = urljoin(BASE_URL, href)

        print()
        print("MATCH FOUND")
        print(
            "DATE:",
            uploaded_date
        )
        print(
            "TITLE:",
            title_text
        )
        print(
            "PDF URL:"
        )
        print(
            pdf_url
        )

        # ----------------------------------------------------
        # Store ONLY required fields
        # ----------------------------------------------------

        records.append(
            {
                "title": title_text,
                "uploaded_date": uploaded_date,
                "Month": parsed_date.strftime("%B"),
                "Year": parsed_date.year,
                "pdf_url": pdf_url
            }
        )

    return records


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def deduplicate(records):

    unique = {}

    for record in records:

        key = (
            record["title"].strip(),
            record["uploaded_date"],
            record["pdf_url"]
        )

        unique[key] = record

    return list(
        unique.values()
    )


# ============================================================
# FIND NEXT BUTTON
# ============================================================

def find_next_button(driver):

    buttons = driver.find_elements(
        By.TAG_NAME,
        "button"
    )

    for button in buttons:

        try:

            if not button.is_displayed():
                continue

            if (
                button.text
                .strip()
                .lower()
                == "next"
            ):
                return button

        except StaleElementReferenceException:

            continue

    return None


# ============================================================
# GET CURRENT PAGINATION SIGNATURE
# ============================================================

def get_pagination_signature(driver):

    body_text = driver.find_element(
        By.TAG_NAME,
        "body"
    ).text

    match = re.search(
        r"Showing\s+\d+\s+to\s+\d+\s+of\s+\d+\s+entries"
        r"(?:\s+\(filtered from \d+ total\))?",
        body_text
    )

    if match:
        return match.group(0)

    return None


# ============================================================
# GET PAGINATION DETAILS
# ============================================================

def get_pagination_details(driver):
    """Return the visible page range and the official result total.

    The FSSAI page exposes pagination as text such as
    ``Showing 1 to 10 of 316 entries``.  Using that total lets the
    scraper finish at the end of the official archive instead of relying
    on an arbitrary maximum number of pages.
    """

    body_text = driver.find_element(
        By.TAG_NAME,
        "body"
    ).text

    match = re.search(
        r"Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+entries"
        r"(?:\s+\(filtered from \d+ total\))?",
        body_text
    )

    if not match:
        return None

    return {
        "first": int(match.group(1)),
        "last": int(match.group(2)),
        "total": int(match.group(3)),
    }


# ============================================================
# CLICK NEXT PAGE
# ============================================================

def go_to_next_page(driver):

    old_signature = (
        get_pagination_signature(driver)
    )

    if old_signature is None:
        return False

    next_button = find_next_button(
        driver
    )

    if next_button is None:
        return False

    try:

        if not next_button.is_enabled():
            return False

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            next_button
        )

        time.sleep(0.3)

        driver.execute_script(
            "arguments[0].click();",
            next_button
        )

    except Exception:

        return False

    # --------------------------------------------------------
    # Wait for pagination text to change
    # --------------------------------------------------------

    try:

        def page_changed(d):

            new_signature = (
                get_pagination_signature(d)
            )

            return (
                new_signature is not None
                and
                new_signature != old_signature
            )

        WebDriverWait(
            driver,
            20
        ).until(
            page_changed
        )

        return True

    except TimeoutException:

        return False


# ============================================================
# MAIN SCRAPER
# ============================================================

def main(
    start_date=None,
    end_date=None,
    output_file=OUTPUT_FILE,
    save_raw=True,
):

    if start_date is None:
        start_date = DEFAULT_START_DATE

    if end_date is None:
        end_date = DEFAULT_END_DATE

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 70)
    print(
        "FSSAI GAZETTE NOTIFICATION EXTRACTOR"
    )
    print("=" * 70)

    print("\nSource:")
    print(
        SOURCE_URL
    )

    print("\nRequired date range:")

    print(
        start_date.strftime("%d-%m-%Y"),
        "to",
        end_date.strftime("%d-%m-%Y")
    )

    driver = create_driver()

    all_records = []

    try:

        print(
            "\nOpening official FSSAI page..."
        )

        driver.get(
            SOURCE_URL
        )

        wait_for_table(
            driver
        )

        page_number = 1
        seen_pages = set()

        while True:

            pagination = get_pagination_details(driver)

            if pagination is None:
                raise RuntimeError(
                    "Could not read pagination from the official FSSAI page"
                )

            page_signature = (
                pagination["first"],
                pagination["last"],
                pagination["total"],
            )

            # A repeated range means the portal did not advance.  Stop to
            # avoid an infinite loop, without imposing a cap on the archive.
            if page_signature in seen_pages:
                raise RuntimeError(
                    "FSSAI pagination repeated a page before the archive ended"
                )

            seen_pages.add(page_signature)

            print(
                f"\nProcessing page {page_number} "
                f"(entries {pagination['first']}-{pagination['last']} "
                f"of {pagination['total']})..."
            )

            records = extract_current_page(
                driver,
                page_number,
                start_date,
                end_date,
                save_raw=save_raw,
            )

            print(
                "  Matching records found:",
                len(records)
            )

            all_records.extend(
                records
            )

            # The final visible page has reached the official result total.
            # This intentionally supports every page in the archive, not
            # only the first few pages or a fixed historical date range.
            if pagination["last"] >= pagination["total"]:

                print("Reached the final official FSSAI result page.")

                break

            # ------------------------------------------------
            # PAGINATION
            # ------------------------------------------------

            moved = go_to_next_page(
                driver
            )

            if not moved:

                print(
                    "No further page detected."
                )

                break

            page_number += 1

            time.sleep(0.5)

    finally:

        driver.quit()

    # ========================================================
    # DEDUPLICATION
    # ========================================================

    all_records = deduplicate(
        all_records
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "DATE FILTERING COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "Unique notifications in required range:",
        len(all_records)
    )

    # ========================================================
    # FINAL JSON
    # ========================================================
    #
    # EXACT FORMAT REQUESTED:
    #
    # [
    #   {
    #     "title": "...",
    #     "uploaded_date": "...",
    #     "Month": "...",
    #     "Year": 2026,
    #     "pdf_url": "..."
    #   }
    # ]
    #
    # No status.
    # No verification fields.
    # No source_snippet.
    # ========================================================

    # Keep the latest notifications first, matching the official portal,
    # and give the UI a stable identifier for every returned result.
    all_records.sort(
        key=lambda record: datetime.strptime(
            record["uploaded_date"],
            "%d-%m-%Y"
        ),
        reverse=True
    )

    final_records = []

    for index, record in enumerate(all_records, start=1):

        final_records.append(
            {
                "id": index,
                "title": record["title"],
                "uploaded_date": record["uploaded_date"],
                "Month": record["Month"],
                "Year": record["Year"],
                "pdf_url": record["pdf_url"]
            }
        )

    output_file.write_text(
        json.dumps(
            final_records,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "EXTRACTION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "Total notifications:",
        len(final_records)
    )

    print(
        "JSON saved to:",
        output_file
    )

    return final_records


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
