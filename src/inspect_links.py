from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from pathlib import Path
import time


TARGET_URL = (
    "https://www.fssai.gov.in/"
    "food-law/notifications?notification=gazette-notification"
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

        time.sleep(8)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        print("\nPDF/DOWNLOAD LINKS FOUND:\n")

        count = 0

        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)
            href = a["href"]

            if "pdf" in href.lower() or "download" in text.lower():
                count += 1
                print(f"{count}. TEXT: {text}")
                print(f"   HREF: {href}")
                print()

        print("TOTAL PDF/DOWNLOAD LINKS:", count)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()