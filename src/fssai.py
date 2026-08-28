"""
FSSAI Gazette Notification Extractor — Gemini 3 Flash Preview

Design decision: the fetch-integrity check (Step 0) is done in PYTHON, not
left to the model's own browsing tool. This is the fix for the root cause
you hit last time — an agent's internal fetch can fail/get blocked silently
and the model falls back to generating plausible-looking data from memory.
By fetching ourselves with requests, we guarantee: if the fetch fails, we
never even call the model.

Install:
    pip install google-genai requests beautifulsoup4

Env var required:
    GEMINI_API_KEY=<your key>
"""

import os
import re
import json
from datetime import datetime

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

load_dotenv()

TARGET_URL ="https://www.fssai.gov.in/food-law/notifications?notification=gazette-notification"
MODEL = "gemini-3-flash-preview"  # swap to "gemini-3.5-flash" once you migrate

# ---------------------------------------------------------------------------
# STEP 0 — Deterministic fetch integrity check (done in code, not by the LLM)
# ---------------------------------------------------------------------------

def fetch_page(url: str) -> dict:
    headers = {
        # A generic browser UA — gov sites frequently block default requests/python UAs
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as e:
        return {"ok": False, "reason": f"request exception: {e}"}

    if resp.status_code != 200:
        return {"ok": False, "reason": f"non-200 status: {resp.status_code}"}

    html = resp.text
    if not html or len(html.strip()) < 500:
        return {"ok": False, "reason": "empty or suspiciously short response body"}

    soup = BeautifulSoup(html, "html.parser")

    # Look for something table-like containing "gazette" or "notification" text.
    text_lower = soup.get_text(" ", strip=True).lower()
    has_relevant_text = "gazette" in text_lower or "notification" in text_lower
    has_download_link = any(
    "download" in a.get_text(" ", strip=True).lower()
    for a in soup.find_all("a")
)

    if not has_relevant_text or not has_download_link:
        return {
            "ok": False,
            "reason": "no notification table found in fetched content "
                    "(possible redirect, login wall, or JS-rendered page)",
        }

    return {"ok": True, "html": html, "soup": soup}


def extract_table_region(soup: BeautifulSoup) -> str:
    """
    Narrow the HTML down to just the table(s), so we feed the model a clean,
    small, high-signal chunk instead of the whole page (nav, footer, scripts).
    This also reduces the chance of the model losing rows near the end due
    to context noise.
    """
    tables = soup.find_all("table")
    if not tables:
        return str(soup)
    return "\n\n".join(str(t) for t in tables)


# ---------------------------------------------------------------------------
# STEP 1 — Grounded extraction via Gemini, fed ONLY the real fetched HTML
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """You are an AI Regulatory Intelligence Agent operating in STRICT GROUNDING MODE.

You are being given the ACTUAL, ALREADY-FETCHED raw HTML of the notification
table from {url} below. You did not fetch this yourself — it was fetched
deterministically and verified to contain a real table before being handed
to you. Do not attempt to fetch the URL yourself. Do not use any prior or
training knowledge about FSSAI, gazette notifications, past filenames, or
past dates to fill in data under any circumstances. If a row or field is not
literally present in the HTML below, it does not exist for this task.

=====================================================
STEP 1 — ROW-LEVEL EXTRACTION
=====================================================
For every table row whose "Uploaded on" date falls between 01-12-2025 and
31-05-2026, extract:

1. Physically locate the <a> tag or "Download" button for that row.
2. Resolve relative paths by joining with "https://www.fssai.gov.in/"
   (e.g. "../../docs/abc.pdf" -> "https://www.fssai.gov.in/docs/abc.pdf").
3. Copy a verbatim snippet of the raw HTML/text you extracted this row from
   (the table cell text and the href attribute value, exactly as they appear —
   this is your evidence, not a paraphrase).

RULES:
- NO GUESSING. If a field is not literally visible in the HTML below,
  output null for that field — never infer, complete a pattern, or reuse a
  filename convention you've seen before.
- It is fully acceptable, and expected, to return FEWER rows than the date
  range might suggest. Under-extraction is safe. Fabricating a row to fill
  a gap is a critical failure.
- Do not extrapolate beyond the last row you can actually see in the HTML.
  If the table appears to continue but you cannot see further rows, stop.
- If a pdf_url looks like a homepage, a redirect target, or a generic
  listing page rather than a specific file, set it to "PDF_NOT_FOUND"
  rather than guessing a filename.

Return ONLY valid JSON matching this schema:
{{
  "status": "OK",
  "notifications": [
    {{
      "title": "Exact title from the table",
      "uploaded_date": "DD-MM-YYYY",
      "Month": "Full Month Name",
      "Year": "YYYY",
      "pdf_url": "Full verified absolute URL or PDF_NOT_FOUND",
      "source_snippet": "Verbatim table cell text + href attribute exactly as fetched"
    }}
  ]
}}

=== RAW FETCHED HTML (table region only) ===
{table_html}
=== END RAW FETCHED HTML ===
"""


def call_gemini_extract(client: genai.Client, table_html: str) -> dict:
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(url=TARGET_URL, table_html=table_html)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    return json.loads(response.text)


# ---------------------------------------------------------------------------
# STEP 2 — Deterministic verification (no model call — cheap, catches fabrication)
# ---------------------------------------------------------------------------

def verify_entries(raw_html: str, notifications: list) -> list:
    verified = []
    for entry in notifications:
        snippet = entry.get("source_snippet") or ""
        url = entry.get("pdf_url") or ""

        snippet_found = bool(snippet) and snippet.strip() in raw_html
        url_ok = url == "PDF_NOT_FOUND" or (
            url.startswith("https://www.fssai.gov.in/") and url.split("/")[-1] in raw_html
        )
        date_ok = bool(re.match(r"^\d{2}-\d{2}-\d{4}$", entry.get("uploaded_date") or ""))

        entry["verified"] = bool(snippet_found and url_ok and date_ok)
        entry["verification_note"] = (
            "passed" if entry["verified"]
            else f"snippet_found={snippet_found}, url_ok={url_ok}, date_ok={date_ok}"
        )
        verified.append(entry)
    return verified


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run():
    fetch_result = fetch_page(TARGET_URL)

    if not fetch_result["ok"]:
        output = {"status": "FETCH_FAILED", "reason": fetch_result["reason"]}
        print(json.dumps(output, indent=2))
        return output

    table_html = extract_table_region(fetch_result["soup"])

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    extraction = call_gemini_extract(client, table_html)

    if extraction.get("status") != "OK":
        print(json.dumps(extraction, indent=2))
        return extraction

    verified_notifications = verify_entries(fetch_result["html"], extraction["notifications"])

    output = {
        "status": "OK",
        "run_at": datetime.utcnow().isoformat() + "Z",
        "notifications": verified_notifications,
        "verified_count": sum(1 for n in verified_notifications if n["verified"]),
        "unverified_count": sum(1 for n in verified_notifications if not n["verified"]),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return output


if __name__ == "__main__":
    run()