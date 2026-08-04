# SiteScore — SEO + AEO Audit Tool

A web tool that scores any website on two things:
1. **SEO Score** — traditional on-page SEO (title tags, meta descriptions, headings, alt text, etc.)
2. **AEO Score** — AI Answer Engine Optimization: how ready the page is to be cited by ChatGPT, Perplexity, and Google AI Overviews.

Enter a URL, get an instant on-screen score breakdown, and download a branded client-ready PDF report.

---

## Project structure

```
sitescore/
├── app.py                 # Flask app (routes, PDF generation trigger)
├── analyzer.py             # Core scoring logic — fetches page, runs checks
├── report_generator.py     # Builds the branded PDF using ReportLab
├── templates/
│   └── index.html          # Web UI (single page, vanilla JS, no frameworks)
├── reports/                 # Generated PDFs land here (created automatically)
└── requirements.txt
```

---

## Run locally

```bash
pip install -r requirements.txt
python3 app.py
```

Then open `http://localhost:5000` in your browser.

---

## Deploy it live (so clients/other agencies can use it)

Easiest free/cheap options for a Flask app like this:

### Option A — Render.com (recommended, free tier available)
1. Push this folder to a GitHub repo.
2. Go to render.com → New → Web Service → connect your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Deploy. You'll get a live URL like `sitescore.onrender.com`.

### Option B — Railway.app
1. Push to GitHub.
2. railway.app → New Project → Deploy from GitHub repo.
3. Railway auto-detects Flask and deploys. Add `Procfile` if needed:
   ```
   web: gunicorn app:app
   ```

### Option C — Your own VPS (DigitalOcean, Hostinger, etc.)
1. Install Python, clone the repo.
2. `pip install -r requirements.txt`
3. Run with gunicorn behind nginx:
   ```bash
   gunicorn --bind 0.0.0.0:8000 app:app
   ```
4. Point nginx + your domain at port 8000.

Once deployed, connect a custom domain (e.g. `audit.dig-market.com`) and you have a live product.

---

## How to monetize it (matches the plan we discussed)

1. **Free tier**: anyone can run 1 audit for free, no PDF download — this is your lead magnet / cold outreach tool.
2. **Paid tier**: Stripe subscription ($15–30/month) unlocks unlimited audits + PDF downloads + white-label (their agency name/logo on the report instead of "Dig Market").
3. **Use it yourself first**: run it against your own client sites (splendas.com, smithsblade.com, etc.) to generate the AI-visibility audit section for your existing SEO reports — this alone saves you manual report-building time.

### Adding Stripe (next step, not yet built)
When you're ready, we add:
- `/pricing` page
- Stripe Checkout session on signup
- A `users` table (SQLite is enough to start) to track who has paid access
- Gate `/download/<filename>` behind a login check

Let me know when you want this piece built.

---

## Extending the scoring engine

All scoring logic lives in `analyzer.py` inside two methods: `run_seo_checks()` and `run_aeo_checks()`. Each check is a small method that returns:

```python
{
    'name': 'Check Name',
    'value': 'what was found',
    'pass': True/False,
    'detail': 'explanation shown in the PDF/UI'
}
```

To add a new check (e.g. page speed via Google PageSpeed API), write a new method following this pattern and add it to the relevant `run_*_checks()` list.

## Customizing the PDF branding

Colors and layout are in `report_generator.py` at the top:
```python
PRIMARY = HexColor('#1a1a2e')   # header/dark color
ACCENT = HexColor('#0f9d58')    # pass/green color
```
Change these to match Dig Market's brand, or make them dynamic per-client for white-label reports.
