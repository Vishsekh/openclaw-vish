"""
Live button inspector — uses the same Chrome profile as the main script.
Visits a profile and dumps all buttons, then clicks More and dumps dropdown.
Also simulates clicking Connect to capture the modal buttons.

Usage:
    python inspect_buttons_live.py <linkedin_url> [--click-connect]
"""

import sys
import time
import os
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROJECT_DIR = Path(__file__).parent
PROFILE_DIR = PROJECT_DIR / ".uc-chrome-profile"


def get_chrome_version():
    import subprocess
    try:
        result = subprocess.run(
            ['reg', 'query', r'HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon', '/v', 'version'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'version' in line.lower():
                    return int(line.strip().split()[-1].split('.')[0])
    except Exception:
        pass
    return None


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    kwargs = {"options": options, "use_subprocess": True}
    v = get_chrome_version()
    if v:
        kwargs["version_main"] = v
        print(f"Chrome version: {v}")
    driver = uc.Chrome(**kwargs)
    time.sleep(3)
    try:
        driver.set_window_size(1280, 900)
    except Exception:
        pass
    return driver


def dump_buttons(driver, label=""):
    buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    print(f"\n{'='*60}")
    print(f"BUTTONS {label} ({len(buttons)} total)")
    print(f"{'='*60}")
    for i, btn in enumerate(buttons):
        try:
            text = (btn.text or "").strip()[:60]
            aria = btn.get_attribute("aria-label") or ""
            classes = (btn.get_attribute("class") or "")[:80]
            visible = btn.is_displayed()
            enabled = btn.is_enabled()
            if text or aria:
                print(f"  [{i:3d}] text='{text}'")
                print(f"        aria='{aria}'")
                print(f"        visible={visible} enabled={enabled}")
                print(f"        class='{classes}'")
                print()
        except Exception:
            pass


def dump_dropdowns(driver):
    print(f"\n{'='*60}")
    print("DROPDOWN CONTENTS")
    print(f"{'='*60}")
    for selector in [
        "div.artdeco-dropdown__content",
        "div[role='listbox']",
        "ul[role='menu']",
        "div.artdeco-dropdown__content-inner",
    ]:
        items = driver.find_elements(By.CSS_SELECTOR, selector)
        for i, item in enumerate(items):
            try:
                if item.text.strip():
                    print(f"  [{selector}][{i}]: {item.text.strip()[:200]}")
            except Exception:
                pass


def dump_dialogs(driver):
    print(f"\n{'='*60}")
    print("DIALOGS / MODALS")
    print(f"{'='*60}")
    dialogs = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
    for i, d in enumerate(dialogs):
        try:
            print(f"  Dialog[{i}] visible={d.is_displayed()}")
            # Find all buttons inside dialog
            btns = d.find_elements(By.CSS_SELECTOR, "button")
            for j, btn in enumerate(btns):
                text = (btn.text or "").strip()[:60]
                aria = btn.get_attribute("aria-label") or ""
                visible = btn.is_displayed()
                if text or aria:
                    print(f"    btn[{j}] text='{text}' aria='{aria}' visible={visible}")

            # Find textareas
            textareas = d.find_elements(By.CSS_SELECTOR, "textarea")
            for j, ta in enumerate(textareas):
                name = ta.get_attribute("name") or ""
                placeholder = ta.get_attribute("placeholder") or ""
                idd = ta.get_attribute("id") or ""
                print(f"    textarea[{j}] name='{name}' id='{idd}' placeholder='{placeholder}'")

            # Find inputs
            inputs = d.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email']")
            for j, inp in enumerate(inputs):
                name = inp.get_attribute("name") or ""
                print(f"    input[{j}] name='{name}'")
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_buttons_live.py <linkedin_url> [--click-connect]")
        sys.exit(1)

    url = sys.argv[1]
    click_connect = "--click-connect" in sys.argv

    print(f"Inspecting: {url}")
    driver = create_driver()

    try:
        # Check login
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        if "/feed" not in driver.current_url:
            print("Not logged in. Waiting 120s for manual login...")
            for i in range(24):
                time.sleep(5)
                if "/feed" in driver.current_url:
                    print("Login detected!")
                    break
            else:
                print("Login timeout.")
                return

        # Visit profile
        driver.get(url)
        time.sleep(5)

        print(f"\nCurrent URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        # Scroll to load lazy content
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Dump all buttons on profile page
        dump_buttons(driver, "ON PROFILE PAGE")

        # Click More dropdown and dump
        more_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "button[aria-label='More actions'], button[aria-label='More']"
        )
        for mb in more_buttons:
            if mb.is_displayed():
                print(f"\nClicking More button: '{mb.get_attribute('aria-label')}'")
                mb.click()
                time.sleep(2)
                dump_dropdowns(driver)
                # Close dropdown
                mb.click()
                time.sleep(1)
                break

        # If --click-connect, find and click the Connect button
        if click_connect:
            print("\n\n--- CLICKING CONNECT ---")
            connect_btn = None

            # Try aria-label with Invite
            for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                aria = (btn.get_attribute("aria-label") or "").lower()
                text = (btn.text or "").strip().lower()
                if ("connect" in aria or "invite" in aria or text == "connect") and btn.is_displayed():
                    connect_btn = btn
                    print(f"Found Connect: text='{btn.text}' aria='{btn.get_attribute('aria-label')}'")
                    break

            if not connect_btn:
                # Try More dropdown
                for mb in more_buttons:
                    if mb.is_displayed():
                        mb.click()
                        time.sleep(2)
                        spans = driver.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__content span")
                        for span in spans:
                            if "connect" in span.text.lower():
                                print(f"Found Connect in dropdown: '{span.text}'")
                                span.click()
                                time.sleep(2)
                                connect_btn = "dropdown"
                                break
                        break

            if connect_btn and connect_btn != "dropdown":
                connect_btn.click()
                time.sleep(3)

            if connect_btn:
                # Dump modal
                dump_dialogs(driver)
                dump_buttons(driver, "AFTER CLICKING CONNECT (MODAL)")

                # Close modal without sending
                dismiss = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                for d in dismiss:
                    if d.is_displayed():
                        d.click()
                        print("\nDismissed modal.")
                        break
            else:
                print("No Connect button found.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
