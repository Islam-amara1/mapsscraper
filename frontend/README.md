# CRM Frontend

Streamlit-based CRM for managing leads from scraped data.

Note: There is also a newer SvelteKit UI in `web/` for a more “SaaS-like” experience.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run frontend/app.py
```

## Features

- **Leads Tab**: View/edit all leads with inline editing
- **Import Tab**: Import new `data/results/*.csv` into CRM (idempotent)
- **Callbacks Tab**: Track upcoming call follow-ups
- **Auto import**: On app start, imports any new scraper CSVs automatically

## CRM Fields

- Contact name + role
- Clinic name + size
- Call outcome (interested / callback / not interested)
- Next action + date
- Notes on conversation

## Data

SQLite database at `data/crm.db`
