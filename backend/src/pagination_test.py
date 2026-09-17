from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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

        # ----------------------------------------------------
        # BEFORE CLICK
        # ----------------------------------------------------

        print("\nBEFORE CLICK:")

        before_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

        for line in before_text.splitlines():

            if (
                "Showing" in line
                or "entries" in line
                or line.strip() in ["1", "2", "3"]
            ):
                print(line)

        # ----------------------------------------------------
        # FIND NEXT BUTTON
        # ----------------------------------------------------

        buttons = driver.find_elements(
            By.TAG_NAME,
            "button"
        )

        next_button = None

        for button in buttons:

            if button.text.strip().lower() == "next":

                next_button = button
                break

        if next_button is None:

            print("\nNEXT BUTTON NOT FOUND")
            return

        print("\nNEXT BUTTON FOUND")

        print("Outer HTML:")
        print(
            next_button.get_attribute(
                "outerHTML"
            )
        )

        # ----------------------------------------------------
        # CLICK NEXT
        # ----------------------------------------------------

        print("\nCLICKING NEXT...")

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            next_button
        )

        time.sleep(1)

        driver.execute_script(
            "arguments[0].click();",
            next_button
        )

        # Give the JavaScript pagination time to update.
        time.sleep(4)

        # ----------------------------------------------------
        # AFTER CLICK
        # ----------------------------------------------------

        print("\nAFTER CLICK:")

        after_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

        for line in after_text.splitlines():

            if (
                "Showing" in line
                or "entries" in line
                or line.strip() in ["1", "2", "3"]
            ):
                print(line)

        print("\nCURRENT URL:")
        print(driver.current_url)

    finally:

        driver.quit()


if __name__ == "__main__":
    main()