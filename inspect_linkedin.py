"""
LinkedIn UI Inspector — helps debug selector issues.
Opens a LinkedIn profile and prints out available buttons and their attributes.

Usage:
    python inspect_linkedin.py <linkedin_profile_url>
"""

import sys
import time
import os
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

PROJECT_DIR = Path(__file__).parent
PROFILE_DIR = PROJECT_DIR / ".uc-chrome-profile"


def get_chrome_version():
    """Try to detect Chrome major version on Windows."""
    import subprocess
    try:
        result = subprocess.run(
            ['reg', 'query', r'HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon', '/v', 'version'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'version' in line.lower():
                    version = line.strip().split()[-1]
                    return int(version.split('.')[0])
    except Exception:
        pass
    return None


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    kwargs = {"options": options, "use_subprocess": True}
    chrome_version = get_chrome_version()
    if chrome_version:
        kwargs["version_main"] = chrome_version
        print(f"Detected Chrome version: {chrome_version}")
    driver = uc.Chrome(**kwargs)
    time.sleep(3)
    try:
        driver.set_window_size(1280, 900)
    except Exception:
        time.sleep(2)
        try:
            driver.set_window_size(1280, 900)
        except Exception:
            pass
    return driver


def inspect_profile(url):
    print(f"Inspecting: {url}")
    driver = create_driver()

    try:
        driver.get(url)
        time.sleep(5)

        print(f"\nCurrent URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        # Print all buttons
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        print(f"\nFound {len(buttons)} buttons:\n")

        for i, btn in enumerate(buttons):
            try:
                text = btn.text.strip()[:50] if btn.text else ""
                aria = btn.get_attribute("aria-label") or ""
                classes = btn.get_attribute("class") or ""
                visible = btn.is_displayed()
                if text or aria:
                    print(f"  [{i}] text='{text}' | aria-label='{aria}' | visible={visible}")
                    print(f"       class='{classes[:80]}'")
            except Exception:
                pass

        # Print dropdowns
        print("\n\nDropdown contents:")
        dropdowns = driver.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__content")
        for i, dd in enumerate(dropdowns):
            try:
                spans = dd.find_elements(By.TAG_NAME, "span")
                for sp in spans:
                    if sp.text.strip():
                        print(f"  Dropdown[{i}] span: '{sp.text.strip()}'")
            except Exception:
                pass

        # Also scroll and check for More dropdown
        print("\n\nChecking 'More' dropdown...")
        more_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='More actions'], button[aria-label='More']")
        for mb in more_buttons:
            if mb.is_displayed():
                print(f"  Found More button: '{mb.get_attribute('aria-label')}'")
                mb.click()
                time.sleep(2)
                dropdowns = driver.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__content")
                for i, dd in enumerate(dropdowns):
                    try:
                        spans = dd.find_elements(By.TAG_NAME, "span")
                        for sp in spans:
                            if sp.text.strip():
                                print(f"    Dropdown[{i}] span: '{sp.text.strip()}'")
                    except Exception:
                        pass
                # Also check li elements
                lis = driver.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown__content li")
                for li in lis:
                    try:
                        if li.text.strip():
                            print(f"    Dropdown li: '{li.text.strip()}'")
                    except Exception:
                        pass
                break

        if "--wait" in sys.argv:
            input("\nPress Enter to close browser...")

    finally:
        driver.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_linkedin.py <linkedin_profile_url> [--wait]")
        sys.exit(1)
    inspect_profile(sys.argv[1])
