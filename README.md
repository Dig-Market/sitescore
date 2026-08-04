# SiteScore — Full-Site SEO + AEO + GEO + Technical Audit Tool

A web tool that crawls an entire website (not just one page) and scores it on four things:
1. **SEO Score** — traditional on-page SEO (title tags, meta descriptions, headings, alt text, etc.)
2. **AEO Score** — AI Answer Engine Optimization: how ready the page is to be cited by ChatGPT, Perplexity, and Google AI Overviews.
3. **GEO Score** — Generative Engine Optimization: whether AI crawlers can actually access and parse the content (semantic HTML, robots.txt access for AI bots, content-to-code ratio).
4. **Technical Score** — mobile-friendliness, page weight, server response time, robots.txt, XML sitemap, duplicate titles/meta descriptions across pages.

Enter a homepage URL, the tool discovers and crawls internal pages automatically (up to a configurable limit), scores every page, flags site-wide issues (like duplicate titles across pages), and generates a branded client-ready PDF report.

**Not included:** off-page/backlink analysis. That requires a paid data source (Ahrefs/SEMrush/Moz API) since backlink data isn't present on the website itself — see "Adding backlink data" below if you want to wire this in later.

## What's new in this version

- **Full detail per page** — every crawled page gets its own "Issues Found + How to Fix" list (not just the homepage), both on-screen and in the PDF.
- **Exact image file names** flagged for missing alt text and non-descriptive names (e.g. `IMG_2837.jpg`), so you know exactly which image to fix.
- **Broken internal links** — checks a sample of internal links for 404s/errors and lists the exact broken URL.
- **Real speed diagnostics** via Google PageSpeed Insights (free, no signup needed for light use) — actual Core Web Vitals plus specific slow-down causes (render-blocking resources, unoptimized images, unminified CSS/JS, etc.). Run on the homepage only, since a full Lighthouse test per page would make multi-page crawls too slow.

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

## Adding backlink data (Semrush/Ahrefs/Moz)

Off-page scoring needs a paid API key from **your own** Semrush/Ahrefs/Moz account (not a shared/reseller login — those don't expose API access). Once you have one:

1. Get your API key from your account's API dashboard (e.g. Semrush: Profile → API Access).
2. Add a new method to `analyzer.py`, e.g. `SiteCrawler.fetch_backlink_data()`, that calls the relevant API endpoint with your key.
3. Add the returned metrics (referring domains, toxic backlink %, domain authority, etc.) as a new `off_page_checks` list, scored the same way as the other check lists.
4. Add it to the aggregate score in `crawl()` and to the PDF report in `report_generator.py`.

Keep the API key out of the code — store it as an environment variable (`SEMRUSH_API_KEY`) and read it with `os environ.get(...)`, then set it in Render under Environment → Environment Variables.

## Extending the scoring engine

All scoring logic lives in `analyzer.py` inside four methods: `run_seo_checks()`, `run_aeo_checks()`, `run_geo_checks()`, and `run_technical_page_checks()`. Site-wide checks (robots.txt, sitemap, duplicate titles) live in the `SiteCrawler` class. Each check is a small method that returns:

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
