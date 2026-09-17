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

        # Find every PDF/download link rendered by the page.
        links = driver.execute_script("""
            return Array.from(document.querySelectorAll('a'))
                .filter(a =>
                    a.href.toLowerCase().includes('.pdf') ||
                    a.innerText.toLowerCase().includes('pdf')
                )
                .slice(0, 10)
                .map(a => {
                    let p = a;
                    let ancestors = [];

                    for (let i = 0; i < 6 && p; i++, p = p.parentElement) {
                        ancestors.push({
                            tag: p.tagName,
                            className: p.className,
                            text: (p.innerText || '').trim().substring(0, 500)
                        });
                    }

                    return {
                        href: a.href,
                        text: a.innerText.trim(),
                        ancestors: ancestors
                    };
                });
        """)

        print("\nPDF LINK STRUCTURE:\n")

        for i, item in enumerate(links, 1):
            print("=" * 70)
            print(f"LINK {i}")
            print("HREF:", item["href"])
            print("TEXT:", item["text"])

            for j, ancestor in enumerate(item["ancestors"]):
                print(
                    f"\n  ANCESTOR {j}: "
                    f"<{ancestor['tag']}> "
                    f"class={ancestor['className']}"
                )
                print("  TEXT:", ancestor["text"])

    finally:
        driver.quit()


if __name__ == "__main__":
    main()