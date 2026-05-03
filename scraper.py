import os
import sys
import requests
import subprocess
from PIL import Image, ImageDraw, ImageFont
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


# 🔥 NEW: create SHOP button
def create_button():
    W, H = 500, 110
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, W-1, H-1], radius=55, fill=(255,255,255,245))
    draw.rounded_rectangle([0, 0, W-1, H-1], radius=55, outline=(20,20,20,255), width=4)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 48)
    except:
        font = ImageFont.load_default()

    text = "SHOP NOW"
    bbox = draw.textbbox((0, 0), text, font=font)

    x = (W - (bbox[2]-bbox[0])) // 2 - bbox[0]
    y = (H - (bbox[3]-bbox[1])) // 2 - bbox[1]

    draw.text((x+2, y+2), text, fill=(100,100,100,180), font=font)
    draw.text((x, y), text, fill=(20,20,20,255), font=font)

    img.save("shop_now_btn.png")


# 🔥 NEW: convert image → video
def convert_to_video(image_path):
    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", "shop_now_btn.png",
        "-vf",
        "scale=720:1280:force_original_aspect_ratio=decrease,"
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2,"
        "overlay=(W-w)/2:H-160",
        "-t", "5",
        "-r", "25",
        "-pix_fmt", "yuv420p",
        "output.mp4"
    ]

    subprocess.run(cmd, check=True)


def run():
    IMAGE_URL = sys.argv[1] if len(sys.argv) > 1 else None
    IMAGE_PATH = DEFAULT_IMAGE_PATH

    if IMAGE_URL:
        print("Downloading image from:", IMAGE_URL)
        IMAGE_PATH = download_image(IMAGE_URL)
        print("Saved to:", IMAGE_PATH)

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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

        page = context.new_page()

        print("Opening Pinterest...")
        page.goto("https://www.pinterest.com/")
        page.wait_for_timeout(4000)

        print("Clicking search...")
        page.wait_for_selector("input[placeholder='Search']", timeout=20000)
        page.click("input[placeholder='Search']")
        page.wait_for_timeout(2000)

        print("Clicking Lens...")
        page.wait_for_selector("button[aria-label='Lens']", timeout=10000)
        page.click("button[aria-label='Lens']")
        page.wait_for_timeout(3000)

        print("Uploading image...")
        page.wait_for_selector("input[data-test-id='lens-file-upload']", timeout=10000)
        page.locator("input[data-test-id='lens-file-upload']").set_input_files(IMAGE_PATH)

        print("Waiting for results...")
        page.wait_for_timeout(8000)

        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(2000)

        print("Extracting visible pins...")

        pins = page.locator("div[data-test-id='pin'] img")
        total = pins.count()
        print("Visible pins:", total)

        os.makedirs("images", exist_ok=True)

        saved = 0

        for i in range(total):
            try:
                src = pins.nth(i).get_attribute("src")

                if not src:
                    continue

                if "pinimg.com" not in src:
                    continue

                if "/236x/" not in src:
                    continue

                high_res = src.replace("/236x/", "/736x/")

                print("Trying:", high_res)

                r = requests.get(high_res, timeout=10)

                if r.status_code == 200 and len(r.content) > 20000:
                    path = f"images/img_{saved}.jpg"

                    with open(path, "wb") as f:
                        f.write(r.content)

                    print("Saved:", path)
                    saved += 1

                if saved >= MAX_IMAGES:
                    break

            except Exception as e:
                print("Error:", e)

        print("Done. Downloaded", saved, "image(s)")

        browser.close()

    # 🔥 NEW PART: VIDEO CREATION
    if saved > 0:
        print("Creating SHOP button...")
        create_button()

        print("Converting to video...")
        convert_to_video("images/img_0.jpg")

        print("Saved as output.mp4")
    else:
        print("No image found, skipping video creation")


if __name__ == "__main__":
    run()
