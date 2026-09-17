import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


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
        print("Opening official FSSAI URL...")
        driver.get(TARGET_URL)

        # Give the JavaScript application time to load.
        time.sleep(8)

        print("\nCURRENT URL:")
        print(driver.current_url)

        print("\nTITLE:")
        print(driver.title)

        print("\nPAGE TEXT:")
        print(driver.find_element("tag name", "body").text[:2000])

        print("\nRESOURCE REQUESTS:")
        resources = driver.execute_script("""
            return performance.getEntriesByType('resource')
                .map(entry => entry.name);
        """)

        seen = set()

        for url in resources:
            if url not in seen:
                seen.add(url)

                lower_url = url.lower()

                if any(keyword in lower_url for keyword in [
                    "api",
                    "notification",
                    "notifications",
                    "food-law",
                    "json",
                    "php",
                    "graphql",
                    "search"
                ]):
                    print(url)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()