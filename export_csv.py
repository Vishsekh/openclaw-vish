import json
import csv
from pathlib import Path

project_dir = Path(__file__).parent
input_file = project_dir / "leads-with-messages.json"
output_file = project_dir / "retail-leads-india.csv"

with open(input_file, "r", encoding="utf-8") as f:
    leads = json.load(f)

fieldnames = [
    "name", "role", "company", "linkedin_url",
    "personalization_hook", "hook_explanation", "connection_message"
]

with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for lead in leads:
        writer.writerow({k: lead.get(k, "") for k in fieldnames})

print(f"Exported {len(leads)} leads to {output_file}")
