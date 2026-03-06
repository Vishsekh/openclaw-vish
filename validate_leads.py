"""
LinkedIn Lead Validator — Pre-flight check before automation.
Validates all LinkedIn URLs, auto-fixes 404s, and checks for duplicates.

Usage:
    python validate_leads.py

Run this BEFORE linkedin_connect_uc.py to catch bad URLs early.
"""

import json
import time
import re
from pathlib import Path
from urllib.parse import quote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

PROJECT_DIR = Path(__file__).parent
LEADS_FILE = PROJECT_DIR / "leads-with-messages.json"


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
                    version = line.strip().split()[-1]
                    return int(version.split('.')[0])
    except Exception:
        pass
    return None


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROJECT_DIR / '.uc-chrome-profile'}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    kwargs = {"options": options, "use_subprocess": True}
    chrome_version = get_chrome_version()
    if chrome_version:
        kwargs["version_main"] = chrome_version
    driver = uc.Chrome(**kwargs)
    time.sleep(3)
    try:
        driver.set_window_size(1280, 900)
    except Exception:
        pass
    return driver


def is_404(driver):
    url = driver.current_url
    if "/404" in url or "page-not-found" in url:
        return True
    try:
        text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "this page doesn" in text or "page not found" in text:
            return True
    except Exception:
        pass
    return False


def is_authwall(driver):
    return "/authwall" in driver.current_url or "/login" in driver.current_url


def search_correct_url(driver, name, company):
    """Search LinkedIn for the correct profile URL."""
    query = f"{name} {company}"
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(query)}"
    driver.get(search_url)
    time.sleep(4)

    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.app-aware-link[href*='/in/']")
        name_parts = [p.lower().strip(".") for p in name.split()]
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        for link in links:
            href = link.get_attribute("href") or ""
            if "/in/" not in href:
                continue
            try:
                container = link.find_element(By.XPATH, "./ancestor::li")
                text = (link.text + " " + container.text).lower()
            except Exception:
                text = link.text.lower()

            has_first = first_name in text
            has_last = last_name in text if last_name else True
            has_company = any(w.lower() in text for w in company.split() if len(w) > 3)

            if has_first and (has_last or has_company):
                profile_url = href.split("?")[0].rstrip("/")
                if not profile_url.startswith("http"):
                    profile_url = "https://www.linkedin.com" + profile_url
                return profile_url
    except Exception:
        pass
    return None


def validate_leads():
    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        leads = json.load(f)

    print(f"Validating {len(leads)} leads...\n")

    # Check for duplicate URLs
    urls = [l["linkedin_url"] for l in leads]
    dupes = set(u for u in urls if urls.count(u) > 1)
    if dupes:
        print(f"[WARN] Duplicate URLs found: {dupes}\n")

    # Check for duplicate names
    names = [l["name"] for l in leads]
    dupe_names = set(n for n in names if names.count(n) > 1)
    if dupe_names:
        print(f"[WARN] Duplicate names found: {dupe_names}\n")

    # Check message lengths
    for lead in leads:
        msg = lead.get("connection_message", "")
        if len(msg) > 300:
            print(f"[WARN] {lead['name']}: message is {len(msg)} chars (max 300)")
        if not msg:
            print(f"[WARN] {lead['name']}: no connection_message")

    # Validate URLs by visiting each profile
    print("\nLaunching browser for URL validation...")
    driver = create_driver()
    fixed = 0
    failed = 0

    try:
        # Check login
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        if "/feed" not in driver.current_url:
            print("[ERROR] Not logged in to LinkedIn. Please log in first.")
            print("Waiting 60s for manual login...")
            time.sleep(60)
            if "/feed" not in driver.current_url:
                print("[ERROR] Still not logged in. Aborting.")
                return

        for i, lead in enumerate(leads):
            name = lead["name"]
            url = lead["linkedin_url"]
            print(f"  [{i+1}/{len(leads)}] {name}: {url} ... ", end="", flush=True)

            driver.get(url)
            time.sleep(3)

            if is_authwall(driver):
                print("AUTH WALL - needs re-login")
                failed += 1
                continue

            if is_404(driver):
                print("404!", end=" ")
                # Try to find correct URL
                correct = search_correct_url(driver, name, lead.get("company", ""))
                if correct:
                    print(f"-> FIXED: {correct}")
                    lead["linkedin_url"] = correct
                    fixed += 1
                else:
                    print("-> COULD NOT FIX")
                    failed += 1
            else:
                # Verify the profile name matches
                try:
                    title = driver.title
                    first_name = name.split()[0].lower().strip(".")
                    if first_name in title.lower():
                        print("OK")
                    else:
                        print(f"OK (title: {title})")
                except Exception:
                    print("OK")

            time.sleep(1)

        # Save if any URLs were fixed
        if fixed > 0:
            with open(LEADS_FILE, "w", encoding="utf-8") as f:
                json.dump(leads, f, indent=2, ensure_ascii=False)
            print(f"\n[SAVED] Fixed {fixed} URLs in {LEADS_FILE}")

        print(f"\nValidation complete: {len(leads) - failed - fixed} OK, {fixed} fixed, {failed} failed")

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    validate_leads()
