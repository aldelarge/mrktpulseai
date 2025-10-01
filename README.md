# mrktpulseAI — AI-Powered Market Newsletter & Stock Briefs

Daily market recap + personalized stock summaries.  
Scrapes market data & headlines → analyzes with GPT → emails subscribers → shows a lightweight dashboard.

<p align="left">
  <!-- Badges: replace USER/REPO -->
  <a href="https://github.com/USER/mrktpulseAI/actions"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/USER/mrktpulseAI/ci.yml?label=CI"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

## What it does (TL;DR)
- **Ingests data**: major indices, trending tickers, sector performance, bond yields, earnings & macro headlines (Polygon API, StockNewsAPI).
- **Understands news**: GPT summarizes and scores sentiment; generates a **daily market write-up** and **per-ticker briefs**.
- **Delivers**: sends via **SendGrid**; manages paid subscriptions via **Stripe** (webhooks), with a Flask dashboard for users.
- **Automates**: scheduled daily runs (Heroku Scheduler/cron) + minute-level tasks for dashboard freshness.

## Tech Stack
- **Backend**: Python, Flask, SQLAlchemy (Postgres/SQLite)
- **Data/APIs**: Polygon, StockNewsAPI (plus future: Reddit/Twitter sentiment), OpenAI GPT
- **Email/Payments**: SendGrid, Stripe
- **Scheduling**: cron / Heroku Scheduler
- **Infra**: Heroku (Procfile, env vars)
- **Tests/CI**: pytest, ruff/black, GitHub Actions

## Quickstart

> Python 3.10+ recommended

```bash
# 1) Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 2) Config
cp .env.example .env  # fill the values below

# 3) Database
flask db upgrade      # if using Flask-Migrate; otherwise create DB

# 4) Run app
flask run             # or: python -m flask run
