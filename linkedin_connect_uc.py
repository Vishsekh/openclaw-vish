"""
LinkedIn Connection Request Automation
Uses undetected-chromedriver to bypass LinkedIn's bot detection.
Reads leads from leads-with-messages.json and sends connection requests.

Usage:
    python linkedin_connect_uc.py

First run: Chrome opens, log in to LinkedIn manually, script detects login and proceeds.
Subsequent runs: Uses persistent profile, no login needed.
Safe to re-run — skips already-sent connections.
"""

import json
import time
import random
import re
import os
import signal
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

# --- Configuration ---
PROJECT_DIR = Path(__file__).parent
LEADS_FILE = PROJECT_DIR / "leads-with-messages.json"
RESULTS_FILE = PROJECT_DIR / "linkedin-connect-results.json"
PROFILE_DIR = PROJECT_DIR / ".uc-chrome-profile"
DELAY_BETWEEN_REQUESTS = (12, 25)  # random range in seconds
LOGIN_WAIT_TIMEOUT = 180  # 3 minutes to log in manually
MAX_RETRIES = 1  # retry failed leads this many times

# Daily/weekly rate limits (LinkedIn safe thresholds)
DAILY_SEND_LIMIT = 15   # max connection requests per 24 hours
WEEKLY_SEND_LIMIT = 80  # max connection requests per 7 days

# Generic connection message template (fallback if lead has no connection_message)
MESSAGE_TEMPLATE = "Hi {first_name}, I follow India's retail space closely and your work caught my attention. Would love to connect and stay in touch."


def load_leads():
    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_leads(leads):
    """Save leads back to file (e.g. after URL corrections)."""
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)


def load_results():
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def check_rate_limits(results):
    """
    Check if we've hit daily/weekly LinkedIn rate limits.
    Returns (can_send, daily_sent, weekly_sent, daily_remaining).
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    send_statuses = {"sent", "sent_no_modal"}
    daily_sent = 0
    weekly_sent = 0

    for r in results:
        if r.get("status") not in send_statuses:
            continue
        try:
            ts = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, KeyError):
            continue
        if ts > day_ago:
            daily_sent += 1
        if ts > week_ago:
            weekly_sent += 1

    daily_remaining = max(0, DAILY_SEND_LIMIT - daily_sent)
    weekly_remaining = max(0, WEEKLY_SEND_LIMIT - weekly_sent)
    can_send = min(daily_remaining, weekly_remaining)

    return can_send, daily_sent, weekly_sent, daily_remaining


def save_results(results):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def human_delay(low=0.5, high=2.0):
    """Small random jitter to look more human."""
    time.sleep(random.uniform(low, high))


def extract_first_name(full_name):
    """Extract first name, stripping trailing punctuation (e.g. 'P.' -> 'P')."""
    first = full_name.split()[0]
    return re.sub(r'[.\-,]+$', '', first)


def get_chrome_version():
    """Try to detect Chrome major version on Windows."""
    import subprocess
    try:
        # Try registry query for Chrome version on Windows
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

    # Try common Chrome paths
    chrome_paths = [
        os.path.expandvars(r'%PROGRAMFILES%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run(
                    [path, '--version'], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip().split()[-1]
                    return int(version_str.split('.')[0])
            except Exception:
                pass
    return None


def create_driver():
    """Create an undetected Chrome driver with persistent profile."""
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")

    chrome_version = get_chrome_version()
    kwargs = {
        "options": options,
        "use_subprocess": True,
    }
    if chrome_version:
        kwargs["version_main"] = chrome_version
        print(f"Detected Chrome version: {chrome_version}")

    driver = uc.Chrome(**kwargs)
    # Wait for browser window to be ready before resizing
    time.sleep(3)
    try:
        driver.set_window_size(1280, 900)
    except Exception:
        time.sleep(2)
        try:
            driver.set_window_size(1280, 900)
        except Exception:
            pass  # proceed with default size
    return driver


def wait_for_login(driver):
    """Navigate to LinkedIn and wait for the user to log in if needed."""
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(3)

    # Check if already logged in
    if "/feed" in driver.current_url:
        print("Already logged in to LinkedIn.")
        return True

    print(f"Please log in to LinkedIn in the Chrome window. Waiting up to {LOGIN_WAIT_TIMEOUT}s...")
    elapsed = 0
    while elapsed < LOGIN_WAIT_TIMEOUT:
        time.sleep(5)
        elapsed += 5
        if "/feed" in driver.current_url or "/mynetwork" in driver.current_url:
            print("Login detected!")
            return True
        print(f"  Waiting... ({elapsed}s / {LOGIN_WAIT_TIMEOUT}s)")

    print("Login timeout. Please run the script again after logging in.")
    return False


def close_modal_if_present(driver):
    """Close any open modal/overlay that might block interactions."""
    try:
        dismiss_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
        for btn in dismiss_buttons:
            if btn.is_displayed():
                btn.click()
                time.sleep(1)
                return True
    except Exception:
        pass
    return False


def is_profile_404(driver):
    """Check if the current page is a LinkedIn 404 or auth wall."""
    current_url = driver.current_url
    if "/404" in current_url or "page-not-found" in current_url:
        return "404"
    if "/authwall" in current_url or "/login" in current_url:
        return "authwall"
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "this page doesn" in page_text or "page not found" in page_text:
            return "404"
    except Exception:
        pass
    return None


def search_linkedin_profile(driver, name, company):
    """
    Search LinkedIn for a person's profile when the URL is wrong.
    Returns the correct profile URL or None.
    """
    from urllib.parse import quote
    query = f"{name} {company}"
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(query)}"

    print(f"    [SEARCH] Searching LinkedIn for: {query}")
    driver.get(search_url)
    human_delay(3.0, 5.0)

    # Close any popups
    close_modal_if_present(driver)

    try:
        # Find search result links — LinkedIn people results have /in/ URLs
        result_links = driver.find_elements(
            By.CSS_SELECTOR, "a.app-aware-link[href*='/in/']"
        )

        name_parts = [p.lower().strip(".") for p in name.split()]
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        for link in result_links:
            href = link.get_attribute("href") or ""
            if "/in/" not in href:
                continue

            # Get the text near this link to verify it's the right person
            try:
                # The result card contains the person's name as link text
                link_text = link.text.strip().lower()
                # Also check the parent container for company info
                container = link.find_element(By.XPATH, "./ancestor::li")
                container_text = container.text.lower()
            except Exception:
                link_text = ""
                container_text = ""

            # Match: first name AND (last name OR company) must appear
            text_to_check = link_text + " " + container_text
            has_first = first_name in text_to_check
            has_last = last_name in text_to_check if last_name else True
            has_company = any(
                word.lower() in text_to_check
                for word in company.split()
                if len(word) > 3  # skip short words like "Ltd", "Inc"
            )

            if has_first and (has_last or has_company):
                # Extract clean profile URL
                profile_url = href.split("?")[0].rstrip("/")
                if not profile_url.startswith("http"):
                    profile_url = "https://www.linkedin.com" + profile_url
                print(f"    [SEARCH] Found match: {profile_url}")
                return profile_url

        print(f"    [SEARCH] No matching profile found in search results.")
        return None

    except Exception as e:
        print(f"    [SEARCH] Search failed: {e}")
        return None


def scroll_to_load_buttons(driver):
    """Scroll down and back up to trigger lazy-loaded content."""
    driver.execute_script("window.scrollTo(0, 400);")
    human_delay(0.8, 1.5)
    driver.execute_script("window.scrollTo(0, 0);")
    human_delay(0.5, 1.0)


def js_click(driver, element):
    """Click via JavaScript when regular click is intercepted."""
    driver.execute_script("arguments[0].click();", element)


def find_connect_button(driver, lead_name):
    """
    Find the Connect button on a LinkedIn profile page.
    Covers all known LinkedIn UI variations (2024-2026):
      - Primary Connect button on profile
      - Connect hidden behind "More" dropdown (Follow-primary profiles)
      - Connect inside profile header (pv-top-card) or action bar
      - Various aria-label formats: "Invite X to connect", "Connect with X"
    """
    first_name = extract_first_name(lead_name)
    first_name_lower = first_name.lower()
    human_delay(1.0, 2.0)

    # Scroll to ensure buttons are loaded
    scroll_to_load_buttons(driver)

    # --- Strategy 0: aria-label contains "Invite" and "connect" ---
    try:
        buttons = driver.find_elements(
            By.CSS_SELECTOR, "button[aria-label*='Invite'][aria-label*='connect']"
        )
        for btn in buttons:
            if btn.is_displayed() and btn.is_enabled():
                return btn
    except Exception:
        pass

    # --- Strategy 1: Any button with "connect" + first_name in aria-label ---
    # Covers: "Invite {Name} to connect", "Connect with {Name}", etc.
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        for btn in buttons:
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            if "connect" in aria_label and first_name_lower in aria_label:
                if btn.is_displayed() and btn.is_enabled():
                    return btn
    except Exception:
        pass

    # --- Strategy 2: Connect button by span text in profile header ---
    # LinkedIn wraps button text in <span class="artdeco-button__text">Connect</span>
    try:
        for xpath in [
            "//div[contains(@class, 'pv-top-card')]//button[.//span[text()='Connect']]",
            "//section[contains(@class, 'pv-top-card')]//button[.//span[text()='Connect']]",
            "//main[@id='main']//section[1]//button[.//span[text()='Connect']]",
            "//div[contains(@class, 'ph5')]//button[.//span[text()='Connect']]",
        ]:
            connect_buttons = driver.find_elements(By.XPATH, xpath)
            for btn in connect_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    return btn
    except Exception:
        pass

    # --- Strategy 3: Any visible artdeco-button with text "Connect" ---
    try:
        connect_buttons = driver.find_elements(
            By.XPATH,
            "//button[contains(@class, 'artdeco-button') and .//span[text()='Connect']]"
        )
        for btn in connect_buttons:
            if btn.is_displayed() and btn.is_enabled():
                return btn
    except Exception:
        pass

    # --- Strategy 4: Look in "More" dropdown ---
    # High-profile users show Follow as primary; Connect is hidden in More dropdown
    try:
        more_btn = None
        for selector in [
            "button[aria-label='More actions']",
            "button[aria-label='More']",
            "button.artdeco-dropdown__trigger[aria-label*='More']",
        ]:
            more_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for mb in more_buttons:
                if mb.is_displayed():
                    more_btn = mb
                    break
            if more_btn:
                break

        if more_btn:
            more_btn.click()
            human_delay(1.0, 2.0)

            # Try clicking Connect from dropdown using multiple selector strategies
            dropdown_found = False

            # 4a: Find dropdown item by XPath — span or div text "Connect"
            for xpath in [
                "//div[contains(@class, 'artdeco-dropdown__content')]//span[text()='Connect']",
                "//div[contains(@class, 'artdeco-dropdown__content')]//span[contains(text(), 'Connect')]",
                "//ul[@role='menu']//span[text()='Connect']",
                "//div[contains(@class, 'artdeco-dropdown__content')]//li//div[text()='Connect']",
            ]:
                try:
                    items = driver.find_elements(By.XPATH, xpath)
                    for item in items:
                        if item.is_displayed() or item.text.strip().lower() == "connect":
                            # Click the parent clickable element
                            try:
                                parent = item.find_element(
                                    By.XPATH,
                                    "./ancestor::button | ./ancestor::div[@role='button'] | "
                                    "./ancestor::li[@role='menuitem'] | ./ancestor::a"
                                )
                                js_click(driver, parent)
                            except NoSuchElementException:
                                js_click(driver, item)
                            human_delay(0.5, 1.0)
                            dropdown_found = True
                            break
                except Exception:
                    continue
                if dropdown_found:
                    break

            # 4b: Broad text scan of all dropdown items
            if not dropdown_found:
                try:
                    all_items = driver.find_elements(
                        By.CSS_SELECTOR,
                        "div.artdeco-dropdown__content span, "
                        "div.artdeco-dropdown__content li, "
                        "div.artdeco-dropdown__content div[role='button']"
                    )
                    for item in all_items:
                        if item.text.strip().lower() == "connect":
                            js_click(driver, item)
                            human_delay(0.5, 1.0)
                            dropdown_found = True
                            break
                except Exception:
                    pass

            if dropdown_found:
                return "clicked_from_dropdown"

            # Close dropdown if Connect wasn't found in it
            try:
                more_btn.click()
                human_delay(0.3, 0.5)
            except Exception:
                pass
    except Exception:
        pass

    # --- Strategy 5: Broadest fallback — any button with text "Connect" on page ---
    try:
        all_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        for btn in all_buttons:
            try:
                if btn.text.strip() == "Connect" and btn.is_displayed() and btn.is_enabled():
                    return btn
            except StaleElementReferenceException:
                continue
    except Exception:
        pass

    return None


def check_already_connected(driver, first_name):
    """Check if already connected, pending, or following."""
    first_name_lower = first_name.lower()

    # Check for Message button with person's name (= already connected)
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        for btn in buttons:
            aria = (btn.get_attribute("aria-label") or "").lower()
            if "message" in aria and first_name_lower in aria:
                if btn.is_displayed():
                    return "already_connected"
    except Exception:
        pass

    # Check for Pending button
    try:
        pending_buttons = driver.find_elements(
            By.XPATH, "//button[.//span[text()='Pending']]"
        )
        for btn in pending_buttons:
            if btn.is_displayed():
                return "already_pending"
    except Exception:
        pass

    # Check for "Following" button state
    try:
        following_buttons = driver.find_elements(
            By.XPATH, "//button[.//span[text()='Following']]"
        )
        for btn in following_buttons:
            if btn.is_displayed():
                # Following doesn't mean connected — Connect may be in More dropdown
                return None
    except Exception:
        pass

    return None


def send_connection_request(driver, lead, progress=""):
    """Send a connection request to a single lead. Returns status string."""
    name = lead["name"]
    first_name = extract_first_name(name)
    url = lead["linkedin_url"]

    print(f"\n{progress}--- Processing: {name} ---")
    print(f"    URL: {url}")

    try:
        driver.get(url)
        human_delay(3.0, 5.0)

        # Close any popups
        close_modal_if_present(driver)

        # Check if profile exists — LinkedIn redirects bad URLs to /404/
        page_status = is_profile_404(driver)
        if page_status == "authwall":
            print(f"    [FAIL] Profile hit auth wall — may need re-login!")
            return "auth_wall"
        if page_status == "404":
            print(f"    [WARN] URL is a 404 — searching for correct profile...")
            correct_url = search_linkedin_profile(driver, name, lead.get("company", ""))
            if correct_url:
                # Update the lead in-place so results file gets the correct URL
                lead["linkedin_url"] = correct_url
                print(f"    [SEARCH] Navigating to corrected URL: {correct_url}")
                driver.get(correct_url)
                human_delay(3.0, 5.0)
                close_modal_if_present(driver)
                # Verify the corrected URL isn't also a 404
                if is_profile_404(driver):
                    print(f"    [FAIL] Corrected URL also failed!")
                    return "profile_not_found"
            else:
                print(f"    [FAIL] Could not find correct LinkedIn profile!")
                return "profile_not_found"

        # Check if already connected or pending
        status = check_already_connected(driver, first_name)
        if status == "already_connected":
            print(f"    [SKIP] Already connected!")
            return "already_connected"
        if status == "already_pending":
            print(f"    [SKIP] Connection request already pending!")
            return "already_pending"

        # Find and click Connect
        connect_btn = find_connect_button(driver, name)

        if connect_btn is None:
            print(f"    [FAIL] Connect button not found!")
            return "connect_button_not_found"

        if connect_btn != "clicked_from_dropdown":
            try:
                connect_btn.click()
            except ElementClickInterceptedException:
                js_click(driver, connect_btn)
            human_delay(1.5, 2.5)

        # Handle the connection modal / popover
        # LinkedIn has several flows:
        #   1. Normal: modal with "Add a note" -> textarea -> "Send invitation"
        #   2. "How do you know?" popover: select "Other" -> then normal modal
        #   3. Direct send: no modal, request sent immediately
        #   4. "Send without a note" button variant
        try:
            # Wait for modal or popover
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div[role='dialog'], div[role='alertdialog'], div.artdeco-modal, "
                    "div.send-invite, section.artdeco-modal"
                ))
            )

            # --- Handle "How do you know this person?" popover ---
            # LinkedIn sometimes asks how you know someone before showing the note modal
            try:
                how_know_btns = driver.find_elements(
                    By.XPATH,
                    "//button[@aria-label='Other'] | "
                    "//button[.//span[text()='Other']] | "
                    "//label[contains(text(), 'Other')]"
                )
                for btn in how_know_btns:
                    if btn.is_displayed():
                        print(f"    Handling 'How do you know?' — selecting 'Other'")
                        btn.click()
                        human_delay(0.5, 1.0)
                        # After selecting Other, click Connect/Send to proceed
                        try:
                            proceed_btn = driver.find_element(
                                By.XPATH,
                                "//div[role='dialog']//button[@aria-label='Connect' or "
                                "@aria-label='Send' or .//span[text()='Connect']]"
                            )
                            proceed_btn.click()
                            human_delay(1.0, 2.0)
                        except NoSuchElementException:
                            pass
                        break
            except Exception:
                pass

            # --- Click "Add a note" ---
            note_added = False
            try:
                add_note_xpaths = [
                    "//button[contains(@aria-label, 'Add a note')]",
                    "//button[.//span[text()='Add a note']]",
                    "//button[contains(text(), 'Add a note')]",
                ]
                for xpath in add_note_xpaths:
                    try:
                        add_note_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        add_note_btn.click()
                        human_delay(0.5, 1.5)
                        note_added = True
                        break
                    except TimeoutException:
                        continue
            except Exception:
                pass

            # --- Type the message ---
            if note_added:
                if lead.get("connection_message"):
                    message = lead["connection_message"]
                else:
                    message = MESSAGE_TEMPLATE.format(first_name=first_name)

                # Try multiple textarea selectors
                textarea = None
                for sel in [
                    "textarea[name='message']",
                    "textarea#custom-message",
                    "div[role='dialog'] textarea",
                    "textarea.connect-button-send-invite__custom-message",
                ]:
                    try:
                        textarea = driver.find_element(By.CSS_SELECTOR, sel)
                        if textarea.is_displayed():
                            break
                        textarea = None
                    except NoSuchElementException:
                        continue

                if textarea:
                    textarea.clear()
                    textarea.send_keys(message)
                    human_delay(0.5, 1.0)
                    print(f"    Message: {message[:80]}{'...' if len(message) > 80 else ''}")
                else:
                    print(f"    [WARN] Could not find message textarea.")
            else:
                print(f"    'Add a note' not available, sending without note.")

            # --- Click Send ---
            send_xpaths = [
                "//button[@aria-label='Send invitation']",
                "//button[@aria-label='Send now']",
                "//button[@aria-label='Send']",
                "//button[.//span[text()='Send invitation']]",
                "//button[.//span[text()='Send now']]",
                "//button[.//span[text()='Send']]",
                "//button[.//span[text()='Send without a note']]",
                "//div[role='dialog']//button[contains(@class, 'artdeco-button--primary')]",
            ]
            send_clicked = False
            for xpath in send_xpaths:
                try:
                    send_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    send_btn.click()
                    send_clicked = True
                    human_delay(1.5, 2.5)
                    break
                except (TimeoutException, NoSuchElementException):
                    continue

            if send_clicked:
                print(f"    [OK] Connection request SENT!")
                return "sent"
            else:
                # Last resort: click any primary button in dialog
                try:
                    primary = driver.find_element(
                        By.CSS_SELECTOR,
                        "div[role='dialog'] button.artdeco-button--primary"
                    )
                    if primary.is_displayed():
                        js_click(driver, primary)
                        human_delay(1.5, 2.5)
                        print(f"    [OK] Connection request SENT (primary button fallback)!")
                        return "sent"
                except NoSuchElementException:
                    pass
                print(f"    [FAIL] Could not find Send button in modal!")
                return "send_button_not_found"

        except TimeoutException:
            # No modal appeared — connection may have been sent directly
            print(f"    [OK] No modal appeared — connection may have been sent directly.")
            return "sent_no_modal"

    except Exception as e:
        print(f"    [FAIL] ERROR: {e}")
        return f"error: {str(e)[:100]}"


def export_csv(leads):
    """Export leads to CSV for assignment deliverable."""
    import csv
    csv_file = PROJECT_DIR / "retail-leads-india.csv"
    fieldnames = [
        "name", "role", "company", "linkedin_url",
        "personalization_hook", "hook_explanation", "connection_message"
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow({k: lead.get(k, "") for k in fieldnames})
    print(f"CSV exported: {csv_file} ({len(leads)} leads)")


def print_summary(results):
    """Print a summary table of all results."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        status = r['status']
        if status in ("sent", "sent_no_modal"):
            prefix = "[OK]"
        elif status in ("already_connected", "already_pending"):
            prefix = "[SKIP]"
        else:
            prefix = "[FAIL]"
        print(f"  {prefix:6s} {r['name']:30s} -- {status}")
    print(f"\nResults saved to: {RESULTS_FILE}")


def main():
    print("=" * 60)
    print("LinkedIn Connection Request Automation")
    print("=" * 60)

    # Load leads and previous results
    leads = load_leads()
    results = load_results()
    done_statuses = {"sent", "sent_no_modal", "already_connected", "already_pending"}
    sent_urls = {r["linkedin_url"] for r in results if r.get("status") in done_statuses}

    # Filter out already-processed leads
    remaining = [l for l in leads if l["linkedin_url"] not in sent_urls]
    print(f"\nTotal leads: {len(leads)}")
    print(f"Already processed: {len(leads) - len(remaining)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("\nAll leads have been processed! Nothing to do.")
        return

    # Check rate limits before starting
    can_send, daily_sent, weekly_sent, daily_remaining = check_rate_limits(results)
    print(f"\nRate limits: {daily_sent}/{DAILY_SEND_LIMIT} today, {weekly_sent}/{WEEKLY_SEND_LIMIT} this week")
    if can_send == 0:
        print("[RATE LIMIT] Daily or weekly send limit reached. Try again later.")
        return
    if can_send < len(remaining):
        print(f"[RATE LIMIT] Can only send {can_send} more today. Will process {can_send} of {len(remaining)} remaining.")
        remaining = remaining[:can_send]

    # Launch browser
    print("\nLaunching Chrome...")
    driver = create_driver()
    interrupted = False

    try:
        # Wait for login
        if not wait_for_login(driver):
            driver.quit()
            return

        total = len(remaining)
        failed_leads = []

        # Process each lead
        for i, lead in enumerate(remaining):
            original_url = lead["linkedin_url"]
            progress = f"[{i + 1}/{total}] "
            status = send_connection_request(driver, lead, progress)

            # If URL was corrected during processing, save leads file
            if lead["linkedin_url"] != original_url:
                print(f"    [FIX] URL corrected: {original_url} -> {lead['linkedin_url']}")
                save_leads(leads)

            # Save result
            results.append({
                "name": lead["name"],
                "company": lead["company"],
                "linkedin_url": lead["linkedin_url"],
                "status": status,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            save_results(results)

            if status in ("connect_button_not_found", "send_button_not_found"):
                failed_leads.append(lead)

            # Delay between requests
            if i < total - 1:
                delay = random.uniform(*DELAY_BETWEEN_REQUESTS)
                print(f"\n    Waiting {delay:.0f}s before next request...")
                time.sleep(delay)

        # Retry failed leads
        if failed_leads and MAX_RETRIES > 0:
            print(f"\n{'=' * 60}")
            print(f"[RETRY] Retrying {len(failed_leads)} failed lead(s)...")
            print(f"{'=' * 60}")

            for i, lead in enumerate(failed_leads):
                progress = f"[RETRY {i + 1}/{len(failed_leads)}] "
                # Refresh the page to get a clean state
                status = send_connection_request(driver, lead, progress)

                # Update the result for this lead (replace the failed entry)
                for r in results:
                    if r["linkedin_url"] == lead["linkedin_url"] and r["status"] in ("connect_button_not_found", "send_button_not_found"):
                        r["status"] = status
                        r["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        break
                save_results(results)

                if i < len(failed_leads) - 1:
                    delay = random.uniform(*DELAY_BETWEEN_REQUESTS)
                    print(f"\n    Waiting {delay:.0f}s before next retry...")
                    time.sleep(delay)

        # Auto-export CSV with latest data (URLs may have been corrected)
        export_csv(leads)
        print_summary(results)

    except KeyboardInterrupt:
        interrupted = True
        print("\n\n[INTERRUPTED] Ctrl+C detected. Saving results...")
        save_results(results)
        save_leads(leads)
        export_csv(leads)
        print_summary(results)

    finally:
        print("\nClosing browser...")
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
