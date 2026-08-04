"""
SiteScore - Flask Web Application
Simple web interface: enter a URL, get an SEO + AEO PDF report.
"""
import os
import uuid
from flask import Flask, render_template, request, send_file, jsonify

from analyzer import SiteAnalyzer
from report_generator import generate_report

app = Flask(__name__)
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url', '').strip()
    agency_name = request.form.get('agency_name', 'Dig Market').strip() or 'Dig Market'
    client_name = request.form.get('client_name', '').strip()

    if not url:
        return jsonify({'error': 'Please enter a URL'}), 400

    analyzer = SiteAnalyzer(url)
    result = analyzer.analyze()

    if 'error' in result:
        return jsonify({'error': f"Couldn't load that site: {result['error']}"}), 400

    # Generate PDF
    filename = f"sitescore_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    generate_report(result, filepath, agency_name=agency_name, client_name=client_name or None)

    result['pdf_filename'] = filename
    return jsonify(result)


@app.route('/download/<filename>')
def download(filename):
    # basic safety: only allow files from reports dir, no path traversal
    safe_name = os.path.basename(filename)
    filepath = os.path.join(REPORTS_DIR, safe_name)
    if not os.path.exists(filepath):
        return "Report not found", 404
    return send_file(filepath, as_attachment=True, download_name='SiteScore_Report.pdf')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
