# OpenClaw - LinkedIn Outreach Toolkit

Fully automated LinkedIn outreach pipeline powered by OpenClaw. Just describe your target audience and OpenClaw handles everything — finding leads, generating personalized messages, validating URLs, and sending connection requests.

## How It Works

You give OpenClaw a single prompt like:
> "Find 10 senior retail decision-makers in India and send them personalized LinkedIn connection requests."

OpenClaw then runs the entire pipeline automatically:

1. **Finds leads** — researches names, roles, companies, LinkedIn URLs, and personalization hooks
2. **Generates messages** — writes personalized connection messages (under 300 chars) for each lead
3. **Validates URLs** — checks all LinkedIn profiles, auto-fixes 404s
4. **Sends connection requests** — opens Chrome, logs into LinkedIn, and sends each request with the personalized message
5. **Exports results** — saves everything to CSV and JSON

No manual steps. No copy-pasting. OpenClaw orchestrates the Python scripts end-to-end.

---

## Setup Guide

### Step 1: Install Prerequisites

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **Google Chrome** — [Download](https://www.google.com/chrome/)
- **Git** — [Download](https://git-scm.com/downloads)
- **Node.js 22+** — [Download](https://nodejs.org/) (required for OpenClaw)

### Step 2: Install OpenClaw

**macOS / Linux / WSL2:**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

**Windows (PowerShell — run as Administrator):**
```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

**Or install via npm:**
```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

Verify it's installed:
```bash
openclaw --version
```

### Step 3: Set Up Your API Key

```bash
openclaw doctor
```
When prompted, enter your **OpenAI API key** (`sk-...`). Get one from [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

Your key is saved locally in `~/.openclaw/openclaw.json` — it is NOT stored in the project.

### Step 4: Clone the Repo

```bash
git clone https://github.com/Vishsekh/openclaw-vish.git
cd openclaw-vish
```

### Step 5: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Run It

Open OpenClaw in the project directory and give it your target audience. For example:

> "Find 10 senior retail decision-makers in India (CEOs, MDs, Directors) with their LinkedIn profiles. Generate personalized connection messages and send them connection requests."

OpenClaw will automatically:
- Research and find leads → saves to `leads-raw.json`
- Generate personalized messages → saves to `leads-with-messages.json`
- Run `validate_leads.py` to check all URLs
- Run `linkedin_connect_uc.py` to send connection requests
- Run `export_csv.py` to export results

**First run only:** When Chrome opens, log in to your LinkedIn account manually. OpenClaw waits for you and then continues. Future runs remember your login.

That's it. One prompt, fully automated.

---

## Rate Limits & Safety

- **15 connection requests/day**, **80/week** (built-in LinkedIn-safe limits)
- Safe to re-run — automatically skips already-sent connections
- Random delays between requests to mimic human behavior

## Debug Tools

If something goes wrong, you can inspect LinkedIn profiles manually:
```bash
python inspect_linkedin.py <linkedin_url> [--wait]
python inspect_buttons_live.py <linkedin_url> [--click-connect]
```

## Project Files

| File | Description |
|------|-------------|
| `linkedin_connect_uc.py` | Sends connection requests via browser automation |
| `validate_leads.py` | Validates LinkedIn URLs, auto-fixes 404s |
| `export_csv.py` | Exports leads to CSV |
| `inspect_linkedin.py` | Debug: inspect profile buttons |
| `inspect_buttons_live.py` | Debug: live button inspector |
| `leads-raw.json` | Raw leads found by OpenClaw |
| `leads-with-messages.json` | Leads + AI-generated messages |
| `linkedin-connect-results.json` | Connection request results log |
| `retail-leads-india.csv` | Exported CSV |
| `message-gen-prompt.txt` | Prompt template for message generation |
| `linkedin-connect-prompt.txt` | Prompt template for connection automation |
| `IDEAS.md` | Future improvement ideas |
