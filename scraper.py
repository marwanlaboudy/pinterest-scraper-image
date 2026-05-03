import sys
from playwright.sync_api import sync_playwright


PINTEREST_HOME = "https://www.pinterest.com/"


def is_logged_in(page):
    try:
        # Go to homepage
        page.goto(PINTEREST_HOME, wait_until="domcontentloaded", timeout=60000)

        # If redirected to login → not logged in
        if "login" in page.url.lower():
            return False

        # Wait for profile/avatar element (only appears when logged in)
        page.wait_for_selector("div[data-test-id='header-profile']", timeout=5000)

        return True

    except Exception as e:
        print("Login check error:", e)
        return False


def run():
    with sync_playwright() as p:
        print("Launching browser...")

        browser = p.chromium.launch(
            headless=True,  # GitHub Actions safe
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            storage_state="pinterest_session.json"  # 🔥 your loaded session
        )

        page = context.new_page()

        print("Checking login status...")

        if is_logged_in(page):
            print("✅ LOGGED IN")

            # Optional debug info
            print("Current URL:", page.url)

        else:
            print("❌ NOT LOGGED IN (session expired or invalid)")
            browser.close()
            sys.exit(1)  # 🔥 fail the workflow properly

        # --- continue your scraper here ---
        # Example:
        # page.goto("https://www.pinterest.com/search/pins/?q=desk%20setup")

        browser.close()


if __name__ == "__main__":
    run()
