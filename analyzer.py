"""
SiteScore Analyzer
Fetches a webpage and computes:
1. SEO Score (0-100) - traditional on-page SEO factors
2. AEO Score (0-100) - AI Answer Engine Optimization factors (ChatGPT/Perplexity/AI Overviews readiness)
"""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


class SiteAnalyzer:
    def __init__(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.url = url
        self.domain = urlparse(url).netloc
        self.soup = None
        self.html = None
        self.status_code = None
        self.load_error = None

    def fetch(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; SiteScoreBot/1.0)'}
            resp = requests.get(self.url, headers=headers, timeout=15)
            self.status_code = resp.status_code
            self.html = resp.text
            self.soup = BeautifulSoup(self.html, 'lxml')
            return True
        except Exception as e:
            self.load_error = str(e)
            return False

    # ---------------- SEO CHECKS ----------------

    def check_title(self):
        tag = self.soup.find('title')
        text = tag.get_text().strip() if tag else ''
        length = len(text)
        ok = 30 <= length <= 60
        return {
            'name': 'Title Tag',
            'value': text or 'Missing',
            'pass': bool(text) and ok,
            'detail': f'{length} characters (ideal: 30-60)' if text else 'No title tag found'
        }

    def check_meta_description(self):
        tag = self.soup.find('meta', attrs={'name': 'description'})
        content = tag.get('content', '').strip() if tag else ''
        length = len(content)
        ok = 120 <= length <= 160
        return {
            'name': 'Meta Description',
            'value': content or 'Missing',
            'pass': bool(content) and ok,
            'detail': f'{length} characters (ideal: 120-160)' if content else 'No meta description found'
        }

    def check_h1(self):
        h1s = self.soup.find_all('h1')
        count = len(h1s)
        return {
            'name': 'H1 Heading',
            'value': h1s[0].get_text().strip() if h1s else 'Missing',
            'pass': count == 1,
            'detail': f'{count} H1 tag(s) found (ideal: exactly 1)'
        }

    def check_heading_structure(self):
        h2 = len(self.soup.find_all('h2'))
        h3 = len(self.soup.find_all('h3'))
        return {
            'name': 'Heading Structure',
            'value': f'{h2} H2s, {h3} H3s',
            'pass': h2 >= 2,
            'detail': 'Good subheading structure' if h2 >= 2 else 'Add more H2 subheadings to break up content'
        }

    def check_images_alt(self):
        imgs = self.soup.find_all('img')
        total = len(imgs)
        missing = sum(1 for i in imgs if not i.get('alt', '').strip())
        pct_ok = (total - missing) / total * 100 if total else 100
        return {
            'name': 'Image Alt Text',
            'value': f'{total - missing}/{total} images have alt text' if total else 'No images found',
            'pass': pct_ok >= 80,
            'detail': f'{missing} image(s) missing alt attributes'
        }

    def check_word_count(self):
        text = self.soup.get_text(separator=' ', strip=True)
        words = len(re.findall(r'\w+', text))
        return {
            'name': 'Content Length',
            'value': f'{words} words',
            'pass': words >= 500,
            'detail': 'Good content depth' if words >= 500 else 'Thin content — aim for 500+ words for competitive topics'
        }

    def check_internal_links(self):
        links = self.soup.find_all('a', href=True)
        internal = 0
        for l in links:
            href = l['href']
            if href.startswith('/') or self.domain in href:
                internal += 1
        return {
            'name': 'Internal Linking',
            'value': f'{internal} internal links',
            'pass': internal >= 3,
            'detail': 'Solid internal link structure' if internal >= 3 else 'Add more internal links to related pages'
        }

    def check_https(self):
        is_https = self.url.startswith('https://')
        return {
            'name': 'HTTPS Security',
            'value': 'Enabled' if is_https else 'Not enabled',
            'pass': is_https,
            'detail': 'Site uses secure HTTPS' if is_https else 'Site is not using HTTPS — a ranking and trust factor'
        }

    def check_canonical(self):
        tag = self.soup.find('link', attrs={'rel': 'canonical'})
        return {
            'name': 'Canonical Tag',
            'value': tag.get('href', '') if tag else 'Missing',
            'pass': bool(tag),
            'detail': 'Canonical tag present' if tag else 'No canonical tag — risk of duplicate content issues'
        }

    def run_seo_checks(self):
        return [
            self.check_title(),
            self.check_meta_description(),
            self.check_h1(),
            self.check_heading_structure(),
            self.check_images_alt(),
            self.check_word_count(),
            self.check_internal_links(),
            self.check_https(),
            self.check_canonical(),
        ]

    # ---------------- AEO CHECKS (AI Answer Engine Optimization) ----------------

    def check_schema_markup(self):
        scripts = self.soup.find_all('script', attrs={'type': 'application/ld+json'})
        types_found = []
        for s in scripts:
            if s.string and 'FAQPage' in s.string:
                types_found.append('FAQPage')
            if s.string and 'Article' in s.string:
                types_found.append('Article')
            if s.string and 'Organization' in s.string:
                types_found.append('Organization')
        return {
            'name': 'Structured Data (Schema)',
            'value': ', '.join(set(types_found)) if types_found else 'None found',
            'pass': len(scripts) > 0,
            'detail': 'Schema markup helps AI engines understand and cite your content' if scripts else 'No JSON-LD schema found — AI engines rely heavily on structured data'
        }

    def check_faq_format(self):
        text = self.soup.get_text().lower()
        headings = [h.get_text().strip() for h in self.soup.find_all(['h2', 'h3'])]
        question_headings = [h for h in headings if h.endswith('?') or h.lower().startswith(('what', 'how', 'why', 'when', 'where', 'who', 'is', 'can', 'does'))]
        return {
            'name': 'Question-Based Headings',
            'value': f'{len(question_headings)} question-style headings',
            'pass': len(question_headings) >= 2,
            'detail': 'AI engines favor content structured around direct questions and answers' if len(question_headings) >= 2 else 'Add question-style H2/H3s (e.g. "What is...", "How does...") — this is how AI engines extract answers'
        }

    def check_direct_answers(self):
        paragraphs = self.soup.find_all('p')
        short_direct = 0
        for p in paragraphs[:20]:
            text = p.get_text().strip()
            word_count = len(text.split())
            if 10 <= word_count <= 40:
                short_direct += 1
        return {
            'name': 'Direct-Answer Paragraphs',
            'value': f'{short_direct} concise paragraphs found',
            'pass': short_direct >= 3,
            'detail': 'Short, direct paragraphs are more likely to be quoted by AI answer engines' if short_direct >= 3 else 'Content paragraphs are too long or too fragmented — AI engines prefer 15-40 word direct-answer blocks'
        }

    def check_author_eeat(self):
        text = self.html.lower() if self.html else ''
        signals = 0
        if 'author' in text:
            signals += 1
        if any(k in text for k in ['published', 'updated on', 'last updated']):
            signals += 1
        if any(k in text for k in ['about us', 'about the author']):
            signals += 1
        return {
            'name': 'E-E-A-T Signals',
            'value': f'{signals}/3 trust signals found',
            'pass': signals >= 2,
            'detail': 'Author bio, publish/update dates, and about pages build the trust signals AI engines use for citation' if signals >= 2 else 'Add visible author info and publish/update dates — AI engines weigh source credibility heavily'
        }

    def check_lists_tables(self):
        lists = len(self.soup.find_all(['ul', 'ol']))
        tables = len(self.soup.find_all('table'))
        return {
            'name': 'Lists & Tables',
            'value': f'{lists} lists, {tables} tables',
            'pass': (lists + tables) >= 1,
            'detail': 'Structured lists/tables are easily extracted and cited by AI engines' if (lists + tables) >= 1 else 'Add bullet lists or tables — AI engines extract these more reliably than prose'
        }

    def check_summary_snippet(self):
        paragraphs = self.soup.find_all('p')
        first_para = paragraphs[0].get_text().strip() if paragraphs else ''
        word_count = len(first_para.split())
        has_early_answer = 20 <= word_count <= 60
        return {
            'name': 'Upfront Summary',
            'value': f'First paragraph: {word_count} words',
            'pass': has_early_answer,
            'detail': 'Leading with a concise answer helps AI engines extract your content as a direct response' if has_early_answer else 'Open with a concise 20-60 word direct-answer paragraph before going into detail'
        }

    def run_aeo_checks(self):
        return [
            self.check_schema_markup(),
            self.check_faq_format(),
            self.check_direct_answers(),
            self.check_author_eeat(),
            self.check_lists_tables(),
            self.check_summary_snippet(),
        ]

    # ---------------- SCORING ----------------

    @staticmethod
    def score_from_checks(checks):
        if not checks:
            return 0
        passed = sum(1 for c in checks if c['pass'])
        return round((passed / len(checks)) * 100)

    def analyze(self):
        if not self.fetch():
            return {'error': self.load_error, 'url': self.url}

        seo_checks = self.run_seo_checks()
        aeo_checks = self.run_aeo_checks()

        seo_score = self.score_from_checks(seo_checks)
        aeo_score = self.score_from_checks(aeo_checks)
        overall_score = round((seo_score + aeo_score) / 2)

        return {
            'url': self.url,
            'domain': self.domain,
            'seo_score': seo_score,
            'aeo_score': aeo_score,
            'overall_score': overall_score,
            'seo_checks': seo_checks,
            'aeo_checks': aeo_checks,
        }


if __name__ == '__main__':
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://example.com'
    result = SiteAnalyzer(url).analyze()
    print(json.dumps(result, indent=2))
