import os
import sys
import requests
from playwright.sync_api import sync_playwright

DEFAULT_IMAGE_PATH = "query.png"
MAX_IMAGES = 1

def download_image(url, path=DEFAULT_IMAGE_PATH):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.aliexpress.com/"
    }
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    else:
        raise Exception(f"Failed to download image: {r.status_code}")

def run():
    IMAGE_URL = sys.argv[1] if len(sys.argv) > 1 else None
    IMAGE_PATH = DEFAULT_IMAGE_PATH

    if IMAGE_URL:
        print("Downloading image from:", IMAGE_URL)
        IMAGE_PATH = download_image(IMAGE_URL)
        print("Saved to:", IMAGE_PATH)
    else:
        print("No image URL provided, using local file:", IMAGE_PATH)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            storage_state="pinterest_session.json",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = context.new_page()

        print("Opening Pinterest...")
        page.goto("https://www.pinterest.com/")
        page.wait_for_timeout(4000)
        print("Current URL:", page.url)
        page.screenshot(path="step1_home.png")

        print("Clicking search bar...")
        page.wait_for_selector("input[placeholder='Search']", timeout=20000)
        page.click("input[placeholder='Search']")
        page.wait_for_timeout(2000)
        page.screenshot(path="step2_search_clicked.png")

        print("Clicking Lens button...")
        page.wait_for_selector("button[aria-label='Lens']", timeout=10000)
        page.click("button[aria-label='Lens']")
        page.wait_for_timeout(3000)
        print("Current URL after lens click:", page.url)
        page.screenshot(path="step3_lens_clicked.png")

        print("Looking for file input...")
        file_inputs = page.locator("input[type='file']").all()
        print(f"File inputs found: {len(file_inputs)}")

        print("Uploading image...")
        page.locator("input[type='file']").first.set_input_files(IMAGE_PATH)
        page.wait_for_timeout(3000)
        print("Current URL after upload:", page.url)
        page.screenshot(path="step4_after_upload.png")

        print("Waiting for results to load...")
        page.wait_for_timeout(8000)
        print("Current URL after wait:", page.url)

        # Close search dropdown so lens results are visible
        page.keyboard.press("Escape")
        page.wait_for_timeout(2000)
        page.screenshot(path="step5_results.png")

        print("Scrolling...")
        for i in range(5):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(2000)
            print(f"  Scroll {i+1} done")

        page.screenshot(path="step6_after_scroll.png")

        images = page.locator("img").all()
        print(f"Total images found: {len(images)}")

        print("All image srcs:")
        for i, img in enumerate(images[:20]):
            try:
                src = img.get_attribute("src") or ""
                print(f"  [{i}] {src}")
            except:
                pass

        os.makedirs("images", exist_ok=True)
        count = 0
        saved_urls = set()

        for img in images:
            try:
                src = img.get_attribute("src") or ""
                if not src:
                    continue
                if "pinimg.com" not in src:
                    continue
                if src in saved_urls:
                    continue
                if any(x in src for x in ["avatar", "logo", "icon"]):
                    continue

                # Skip low res thumbnails
                if "/200x/" in src:
                    continue

                # Upgrade to highest res
                high_res = (
                    src.replace("/236x/", "/736x/")
                       .replace("/474x/", "/736x/")
                       .replace("/564x/", "/736x/")
                )

                saved_urls.add(src)

                print(f"Trying: {high_res}")
                r = requests.get(high_res, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0"
                })
                print(f"Status: {r.status_code}")

                if r.status_code == 200:
                    ext = "jpg" if "jpg" in high_res else "png"
                    filepath = f"images/img_{count}.{ext}"
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    print("Saved:", high_res)
                    count += 1

                if count >= MAX_IMAGES:
                    break

            except Exception as e:
                print("Failed:", e)

        print("Downloaded", count, "images")
        browser.close()

if __name__ == "__main__":
    run()
