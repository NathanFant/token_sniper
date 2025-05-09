"""
Token Sniper - Hack Reactor Attendance Bot (Test Mode By Default)

This script auto-snipes Hack Reactor attendance tokens using Playwright.
When run in TEST_MODE, it injects a fake token at a random refresh cycle to simulate detection.

To use:
1. Install dependencies (see README)
2. Create a .env file with your EMAIL and PASSWORD
3. Run this script

Author: Nathan Fant
"""

import asyncio
import multiprocessing
import random
import time
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()

EMAIL = os.getenv("EMAIL")  # Make your own .env file and put in your email
PASSWORD = os.getenv("PASSWORD")  # Make your own .env file and put in your password
ATTENDANCE_URL = "https://sis.galvanize.com/cohorts/188/attendance/mine/"  # Change this to your class' url for attendance.
INPUT_ID = "form-token"
BUTTON_TEXT = "I'm here!"
TEST_MODE = True  # Set to False to use the bot for realsies
TOKEN_SELECTOR = "#test-token" if TEST_MODE else "span.tag.is-danger.is-size-6"


def run_sniper(worker_id, stop_event):
    print(f"Worker {worker_id} started")
    asyncio.run(main(worker_id, stop_event))


async def main(worker_id, stop_event):
    start = None
    elapsed = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)

            context = await browser.new_context()
            page = await context.new_page()

            # Manual login flow
            await page.goto(ATTENDANCE_URL)
            await page.click("text=Use Galvanize Single Sign-On")
            await page.wait_for_selector("#user_email")
            await page.fill("#user_email", EMAIL)
            await page.fill("#user_password", PASSWORD)
            await page.click("input[type='submit']")
            await page.goto(ATTENDANCE_URL)
            await page.wait_for_selector(f"#{INPUT_ID}")

            token = None
            refreshes = 0
            inject_after = random.randint(1, 100)

            while not stop_event.is_set():
                await page.reload(wait_until="domcontentloaded")

                if TEST_MODE:
                    refreshes += 1
                    if refreshes >= inject_after:
                        print(f"🧪 Worker {worker_id}: Injecting fake token")
                        await page.evaluate(
                            """
                            const fakeToken = document.createElement('span');
                            fakeToken.className = 'tag is-danger is-size-6';
                            fakeToken.id = 'test-token';
                            fakeToken.textContent = 'F4K3';
                            const inputBox = document.getElementById('form-token');
                            inputBox.parentElement.insertBefore(fakeToken, inputBox);
                            """
                        )

                token = await page.evaluate(
                    f'document.querySelector("{TOKEN_SELECTOR}")?.textContent?.trim() || null'
                )

                if token:
                    start = time.time()
                    break
                else:
                    await asyncio.sleep(0.01)

            await page.fill(f"#{INPUT_ID}", token)
            await page.click(f"text={BUTTON_TEXT}")
            elapsed = (time.time() - start) * 1000
            print(f"✅ Worker {worker_id}: Submitted token in {elapsed:.2f} ms")
            stop_event.set()
            await asyncio.sleep(1)
            await browser.close()

    except Exception:
        await browser.close()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn")
    stop_event = multiprocessing.Event()
    num_workers = multiprocessing.cpu_count()
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=run_sniper, args=(i, stop_event))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
