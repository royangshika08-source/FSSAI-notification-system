from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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

        print("Opening FSSAI page...")

        driver.get(TARGET_URL)

        time.sleep(8)

        print("\nPAGINATION ELEMENTS:\n")

        elements = driver.execute_script("""
            return Array.from(document.querySelectorAll('*'))
                .filter(el => {
                    const text = (el.innerText || '').trim();
                    return text === 'Next' ||
                           text === '2' ||
                           text.includes('Showing 1 to 10');
                })
                .slice(-20)
                .map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className,
                    text: (el.innerText || '').trim().substring(0, 200),
                    href: el.href || '',
                    outerHTML: el.outerHTML.substring(0, 1000)
                }));
        """)

        for i, element in enumerate(elements, 1):

            print("=" * 80)
            print(f"ELEMENT {i}")
            print("TAG:", element["tag"])
            print("ID:", element["id"])
            print("CLASS:", element["className"])
            print("TEXT:", element["text"])
            print("HREF:", element["href"])
            print("HTML:")
            print(element["outerHTML"])

    finally:

        driver.quit()


if __name__ == "__main__":
    main()