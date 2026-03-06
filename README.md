# OpenClaw - LinkedIn Outreach Toolkit

Automated LinkedIn connection request sender with personalized messages. Uses undetected-chromedriver to bypass bot detection.

## Prerequisites

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **Google Chrome** — must be installed on your system

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Vishsekh/openclaw-vish.git
   cd openclaw-vish
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your leads** — Edit `leads-with-messages.json` with your lead data. Each lead should have:
   ```json
   {
     "name": "Full Name",
     "role": "Job Title",
     "company": "Company Name",
     "linkedin_url": "https://www.linkedin.com/in/username",
     "connection_message": "Your personalized message (max 300 chars)"
   }
   ```

## Usage

### Validate leads (run first)
```bash
python validate_leads.py
```
Checks all LinkedIn URLs, auto-fixes 404s, and flags duplicates. Run this before sending requests.

### Send connection requests
```bash
python linkedin_connect_uc.py
```
- First run: Chrome opens, log in to LinkedIn manually. The script detects login and proceeds.
- Subsequent runs: Uses a persistent Chrome profile (`.uc-chrome-profile/`), no login needed.
- Safe to re-run — skips already-sent connections.
- Built-in rate limiting: 15/day, 80/week.

### Export leads to CSV
```bash
python export_csv.py
```

### Debug tools
```bash
python inspect_linkedin.py <linkedin_url> [--wait]
python inspect_buttons_live.py <linkedin_url> [--click-connect]
```

## Files

| File | Description |
|------|-------------|
| `linkedin_connect_uc.py` | Main automation script |
| `validate_leads.py` | Pre-flight URL validator |
| `export_csv.py` | Export leads to CSV |
| `inspect_linkedin.py` | Debug: inspect profile buttons |
| `inspect_buttons_live.py` | Debug: live button inspector |
| `leads-with-messages.json` | Lead data with personalized messages |
| `leads-raw.json` | Raw lead data |
| `linkedin-connect-results.json` | Connection request results log |
| `retail-leads-india.csv` | Exported CSV of leads |
| `message-gen-prompt.txt` | Prompt template for generating messages |
| `linkedin-connect-prompt.txt` | Prompt template for connection requests |
| `IDEAS.md` | Project ideas and notes |
