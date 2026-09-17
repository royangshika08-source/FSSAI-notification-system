from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
import threading

from datetime import datetime
from src.scrape_notifications import main as scrape_notifications
from src.model.gemini_analysis import analyze_notification_text
from src.notification_monitor import (
    check_for_new_notifications,
    mark_notifications_read,
)


app = FastAPI()
notification_check_lock = threading.Lock()


class ReadNotificationsRequest(BaseModel):
    notification_ids: list[str]


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PROJECT PATHS
# ============================================================

# Go from:
# data/backend/main.py
# up to the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# data/
DATA_DIR = BASE_DIR / "data"

# Extracted JSON files are here:
# data/extracted/
EXTRACTED_DIR = DATA_DIR / "extracted"

# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "FSSAI Notification Backend is running"
    }


# ============================================================
# GET EXTRACTED NOTIFICATION
# ============================================================

@app.get("/api/notification/{file_name}")
def get_notification(file_name: str):

    file_path = EXTRACTED_DIR / file_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Extracted JSON file not found: {file_name}"
        )

    try:

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

# ============================================================
# FETCH NOTIFICATIONS BY DATE RANGE
# ============================================================

@app.get("/api/notifications")
def get_notifications(
    start_date: str,
    end_date: str
):
    try:

        # Convert UI dates: DD-MM-YYYY
        start = datetime.strptime(
            start_date,
            "%d-%m-%Y"
        ).date()

        end = datetime.strptime(
            end_date,
            "%d-%m-%Y"
        ).date()

        # Validate range
        if start > end:
            raise HTTPException(
                status_code=400,
                detail="Start date cannot be after end date"
            )

        print("\n" + "=" * 70)
        print("FETCHING NOTIFICATIONS BY DATE RANGE")
        print("=" * 70)

        print(
            f"Start date: {start.strftime('%d-%m-%Y')}"
        )

        print(
            f"End date: {end.strftime('%d-%m-%Y')}"
        )

        # Run the existing scraper
        result = scrape_notifications(
            start_date=start,
            end_date=end
        )

        # Read the generated notifications.json
        notifications_file = (
            BASE_DIR
            / "data"
            / "output"
            / "notifications.json"
        )

        if not notifications_file.exists():
            raise HTTPException(
                status_code=500,
                detail="Notification output file was not created"
            )

        with open(
            notifications_file,
            "r",
            encoding="utf-8"
        ) as file:

            notifications = json.load(file)

        return {
            "status": "OK",
            "start_date": start_date,
            "end_date": end_date,
            "count": len(notifications),
            "notifications": notifications
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use DD-MM-YYYY"
        )

    except HTTPException:
        raise

    except Exception as e:
        import traceback

        print("NOTIFICATION FETCH ERROR:", repr(e))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# NEW GAZETTE NOTIFICATION MONITOR
# ============================================================

@app.get("/api/notifications/new")
def get_new_notifications():
    """Check the official FSSAI source and return unread notifications."""
    if not notification_check_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="An FSSAI notification check is already in progress"
        )

    try:
        result = check_for_new_notifications()

        return {
            "status": "OK",
            "count": len(result["fresh_notifications"]),
            "unread_count": len(result["notifications"]),
            "notifications": result["notifications"],
            "new_notifications": result["fresh_notifications"],
            "last_successful_check": result["last_successful_check"],
        }
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to check FSSAI notifications: {error}"
        )
    finally:
        notification_check_lock.release()


@app.post("/api/notifications/mark-read")
def mark_new_notifications_read(request: ReadNotificationsRequest):
    if not request.notification_ids:
        return {"status": "OK", "updated": 0}

    try:
        updated = mark_notifications_read(request.notification_ids)
        return {"status": "OK", "updated": updated}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

# ============================================================
# GEMINI ANALYSIS
# ============================================================

@app.get("/api/analyze-notification/{file_name}")
def analyze_notification(file_name: str):

    file_path = EXTRACTED_DIR / file_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Extracted JSON file not found: {file_name}"
        )

    try:

        # ----------------------------------------------------
        # Load extracted notification text
        # ----------------------------------------------------

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        # Original PDF filename stored inside extracted JSON
        original_pdf_file_name = data.get(
            "file_name"
        )

        notification_text = data.get(
            "text",
            ""
        )

        if not notification_text:

            raise HTTPException(
                status_code=400,
                detail="No extracted text found in notification file"
            )

        # ----------------------------------------------------
        # Load notification metadata
        # ----------------------------------------------------

        download_log = (
            BASE_DIR
            / "data"
            / "output"
            / "pdf_downloads.json"
        )

        pdf_url = None
        uploaded_date = None
        notification_title = None

        if download_log.exists():

            with open(
                download_log,
                "r",
                encoding="utf-8"
            ) as file:

                downloads = json.load(file)

            # Find metadata using the exact PDF filename
            for item in downloads:

                if item.get("file_name") == original_pdf_file_name:

                    pdf_url = item.get("pdf_url")
                    uploaded_date = item.get("uploaded_date")
                    notification_title = item.get("title")

                    break

        # ----------------------------------------------------
        # Clean missing metadata
        # ----------------------------------------------------

        if pdf_url in ("None", "", None):
            pdf_url = None

        if uploaded_date in ("None", "", None):
            uploaded_date = None

        if notification_title in ("None", "", None):
            notification_title = None

        # ----------------------------------------------------
        # Send complete information to Gemini
        # ----------------------------------------------------

        print(
            "\nAnalyzing selected notification with Gemini..."
        )

        analysis = analyze_notification_text(
            notification_text=notification_text,
            pdf_url=pdf_url,
            notification_title=notification_title,
            uploaded_date=uploaded_date,
            file_name=original_pdf_file_name
        )

        result = json.loads(analysis)
        
        # ----------------------------------------------------
        # Ensure notification metadata is always preserved
        # ----------------------------------------------------

        for regulation in result.get("regulations", []):

            if not regulation.get("pdf_name"):
                regulation["pdf_name"] = original_pdf_file_name

            if not regulation.get("pdf_link"):
                regulation["pdf_link"] = pdf_url
        # ----------------------------------------------------
        # Ensure affected area metadata is always available
        # ----------------------------------------------------

        regulations = result.get("regulations", [])
        affected_areas = result.get("affected_areas", [])

        default_subsection = ""

        if regulations:
            default_subsection = regulations[0].get(
                "subsection",
                ""
        )

        for area in affected_areas:

         if not area.get("subsection"):
            area["subsection"] = default_subsection

        # ----------------------------------------------------
        # Make sure missing values are displayed consistently
        # ----------------------------------------------------

        for regulation in result.get(
            "regulations",
            []
        ):

            for field in [
                "title",
                "section",
                "subsection",
                "change",
                "pdf_name",
                "pdf_link"
            ]:

                if regulation.get(field) in (
                    None,
                    "",
                    "None",
                    "null"
                ):

                    regulation[field] = ""

        return result

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        print("GEMINI ERROR:", repr(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
