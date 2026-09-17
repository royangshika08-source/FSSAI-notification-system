from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


TARGET_URL = (
    "https://www.fssai.gov.in/"
    "food-law/notifications?notification=gazette-notification"

)

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "raw"
    / "fssai_page_1.html"
)


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)

    try:
        print("Opening FSSAI Gazette page...")

        driver.get(TARGET_URL)

        WebDriverWait(driver, 30).until(
            lambda d: len(
                d.find_element("tag name", "body").text.strip()
            ) > 500
        )

        html = driver.page_source
        body_text = driver.find_element("tag name", "body").text

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(html, encoding="utf-8")

        print("STATUS: Browser page loaded")
        print("TITLE:", driver.title)
        print("BODY TEXT LENGTH:", len(body_text))
        print("HTML LENGTH:", len(html))
        print("DOWNLOAD WORD:", "Download" in body_text)
        print("HTML SAVED TO:", OUTPUT_FILE)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()