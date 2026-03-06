# OpenClaw - LinkedIn Outreach Toolkit

AI-powered LinkedIn outreach automation. Uses OpenClaw to research leads and generate personalized messages, then automates sending connection requests via undetected-chromedriver.

## How It Works

1. **OpenClaw** (AI agent) reads your raw leads, researches them, and generates personalized connection messages
2. **Python scripts** automate sending those connection requests on LinkedIn via browser automation

---

## Step-by-Step Setup Guide

### Step 1: Install Prerequisites

Make sure you have these installed on your machine:

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **Google Chrome** — [Download](https://www.google.com/chrome/)
- **Git** — [Download](https://git-scm.com/downloads)
- **OpenClaw** — [Install instructions](https://github.com/nichochar/openclaw)

### Step 2: Set Up OpenClaw with Your API Key

Run the OpenClaw setup wizard:
```bash
openclaw doctor
```
When prompted, enter your **OpenAI API key** (`sk-...`). You can get one from [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

This saves your key locally in `~/.openclaw/openclaw.json` — it is NOT stored in the project.

### Step 3: Clone the Repo

```bash
git clone https://github.com/Vishsekh/openclaw-vish.git
cd openclaw-vish
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Use OpenClaw to Find Leads & Generate Messages

Open OpenClaw and describe your target audience. For example:
> "Find 10 senior retail decision-makers in India (CEOs, MDs, Directors) with their LinkedIn URLs, roles, companies, and a recent personalization hook for each."

OpenClaw will:
- **Research and find leads** — names, roles, companies, LinkedIn URLs, and personalization hooks
- **Save them to `leads-raw.json`**

Then feed it the prompt from `message-gen-prompt.txt` to generate personalized connection messages. OpenClaw will:
- Read `leads-raw.json`
- Generate a personalized connection message for each lead (under 300 chars)
- Output the results to `leads-with-messages.json`

**Important:** Update the file paths in `message-gen-prompt.txt` to match your local machine before running.

### Step 7: Validate Leads

```bash
python validate_leads.py
```
This checks all LinkedIn URLs, auto-fixes 404s, and flags duplicates. Always run this before sending.

### Step 8: Send Connection Requests

```bash
python linkedin_connect_uc.py
```
- **First run:** Chrome opens automatically — log in to your LinkedIn account manually in the browser window
- The script detects your login and starts sending connection requests with personalized messages
- **Future runs:** Your login is saved in `.uc-chrome-profile/`, no need to log in again
- Safe to re-run — it skips already-sent connections
- Built-in rate limiting: 15/day, 80/week

### Step 9: Export Results to CSV

```bash
python export_csv.py
```

---

## Other Useful Commands

### Debug tools
```bash
python inspect_linkedin.py <linkedin_url> [--wait]
python inspect_buttons_live.py <linkedin_url> [--click-connect]
```

## Project Files

| File | Description |
|------|-------------|
| `linkedin_connect_uc.py` | Main automation script — sends connection requests |
| `validate_leads.py` | Pre-flight URL validator — run before sending |
| `export_csv.py` | Export leads to CSV |
| `inspect_linkedin.py` | Debug: inspect profile buttons |
| `inspect_buttons_live.py` | Debug: live button inspector |
| `leads-raw.json` | Your raw lead data (edit this with your leads) |
| `leads-with-messages.json` | Leads + AI-generated messages (created by OpenClaw) |
| `linkedin-connect-results.json` | Connection request results log |
| `retail-leads-india.csv` | Exported CSV of leads |
| `message-gen-prompt.txt` | Prompt for OpenClaw to generate messages |
| `linkedin-connect-prompt.txt` | Prompt for connection request automation |
| `IDEAS.md` | Future improvement ideas |
