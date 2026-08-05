"""
SiteScore - Flask Web Application
Runs the audit as a background job so long crawls never hit a request
timeout: /analyze starts the job and returns immediately, the frontend
polls /status/<job_id> until it's done.
"""
import os
import uuid
import threading
import time
from flask import Flask, render_template, request, send_file, jsonify

from analyzer import SiteCrawler
from report_generator import generate_site_report

app = Flask(__name__)
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# In-memory job store: job_id -> {status, result, error, created_at}
# 'status' is one of: 'running', 'done', 'error'
JOBS = {}
JOBS_LOCK = threading.Lock()


def _cleanup_old_jobs():
    """Remove jobs older than 30 minutes to avoid unbounded memory growth."""
    cutoff = time.time() - 1800
    with JOBS_LOCK:
        stale = [jid for jid, j in JOBS.items() if j.get('created_at', 0) < cutoff]
        for jid in stale:
            JOBS.pop(jid, None)


def run_audit_job(job_id, url, agency_name, client_name, max_pages):
    try:
        def on_progress(pages_done, pages_target):
            with JOBS_LOCK:
                if job_id in JOBS:
                    JOBS[job_id]['pages_done'] = pages_done
                    JOBS[job_id]['pages_target'] = pages_target

        crawler = SiteCrawler(url, max_pages=max_pages)
        result = crawler.crawl(progress_callback=on_progress)

        if result.get('error'):
            with JOBS_LOCK:
                JOBS[job_id]['status'] = 'error'
                JOBS[job_id]['error'] = f"Couldn't load that site: {result['error']}"
            return

        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]['stage'] = 'Generating PDF report...'

        filename = f"sitescore_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)
        generate_site_report(result, filepath, agency_name=agency_name, client_name=client_name or None)

        for p in result['pages']:
            p.pop('internal_links', None)

        result['pdf_filename'] = filename

        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'done'
            JOBS[job_id]['result'] = result
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id]['status'] = 'error'
            JOBS[job_id]['error'] = f'Unexpected error: {e}'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    _cleanup_old_jobs()

    url = request.form.get('url', '').strip()
    agency_name = request.form.get('agency_name', 'Dig Market').strip() or 'Dig Market'
    client_name = request.form.get('client_name', '').strip()
    try:
        max_pages = int(request.form.get('max_pages', 15))
    except ValueError:
        max_pages = 15
    max_pages = max(1, min(max_pages, 500))

    if not url:
        return jsonify({'error': 'Please enter a URL'}), 400

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            'status': 'running', 'result': None, 'error': None,
            'created_at': time.time(), 'pages_done': 0, 'pages_target': max_pages,
            'stage': None,
        }

    thread = threading.Thread(
        target=run_audit_job,
        args=(job_id, url, agency_name, client_name, max_pages),
        daemon=True,
    )
    thread.start()

    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'error': 'Job not found (it may have expired).'}), 404

    if job['status'] == 'error':
        return jsonify({'status': 'error', 'error': job['error']})
    if job['status'] == 'done':
        return jsonify({'status': 'done', 'result': job['result']})
    return jsonify({
        'status': 'running',
        'pages_done': job.get('pages_done', 0),
        'pages_target': job.get('pages_target', 0),
        'stage': job.get('stage'),
    })


@app.route('/download/<filename>')
def download(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(REPORTS_DIR, safe_name)
    if not os.path.exists(filepath):
        return "Report not found", 404
    return send_file(filepath, as_attachment=True, download_name='SiteScore_Report.pdf')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
