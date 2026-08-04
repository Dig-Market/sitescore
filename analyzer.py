"""
SiteScore Analyzer
Fetches a webpage and computes:
1. SEO Score (0-100) - traditional on-page SEO factors
2. AEO Score (0-100) - AI Answer Engine Optimization factors (ChatGPT/Perplexity/AI Overviews readiness)
"""
import re
import time
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from concurrent.futures import ThreadPoolExecutor, as_completed


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
        self.elapsed = None

    def fetch(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            start = time.time()
            resp = requests.get(self.url, headers=headers, timeout=10)
            self.elapsed = time.time() - start
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
        missing_imgs = []
        for i in imgs:
            if not i.get('alt', '').strip():
                src = i.get('src', 'unknown-source')
                # resolve to absolute-ish for display, keep it short
                fname = src.split('/')[-1].split('?')[0] if src else 'unknown'
                missing_imgs.append(fname or src)
        missing = len(missing_imgs)
        pct_ok = (total - missing) / total * 100 if total else 100
        detail = f'{missing} image(s) missing alt attributes'
        if missing_imgs:
            shown = missing_imgs[:8]
            more = f' (+{missing - len(shown)} more)' if missing > len(shown) else ''
            detail += ': ' + ', '.join(shown) + more + '. Add descriptive alt text to each (e.g. alt="red leather office chair" not alt="img123").'
        return {
            'name': 'Image Alt Text',
            'value': f'{total - missing}/{total} images have alt text' if total else 'No images found',
            'pass': pct_ok >= 80,
            'detail': detail,
            'items': missing_imgs[:20],
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

    def check_image_filenames(self):
        imgs = self.soup.find_all('img')
        bad_names = []
        generic_patterns = re.compile(r'^(img|image|dsc|photo|pic|untitled)[\-_]?\d*\.', re.IGNORECASE)
        for i in imgs:
            src = i.get('src', '')
            fname = src.split('/')[-1].split('?')[0] if src else ''
            if fname and (generic_patterns.match(fname) or re.match(r'^[a-f0-9]{8,}\.', fname, re.IGNORECASE)):
                bad_names.append(fname)
        return {
            'name': 'Image File Names',
            'value': f'{len(bad_names)} non-descriptive file name(s) found' if bad_names else 'File names look descriptive',
            'pass': len(bad_names) == 0,
            'detail': ('Rename these to describe the image content for SEO (e.g. "black-leather-recliner-chair.jpg" instead of "IMG_2837.jpg"): ' + ', '.join(bad_names[:8]) + (f' (+{len(bad_names)-8} more)' if len(bad_names) > 8 else '')) if bad_names else 'Image file names are descriptive rather than generic camera/CMS defaults',
            'items': bad_names[:20],
        }

    def run_seo_checks(self):
        return [
            self.check_title(),
            self.check_meta_description(),
            self.check_h1(),
            self.check_heading_structure(),
            self.check_images_alt(),
            self.check_image_filenames(),
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

    # ---------------- GEO CHECKS (Generative Engine Optimization) ----------------
    # GEO overlaps with AEO but focuses specifically on whether AI crawlers can
    # access and are being invited to use the content (as opposed to whether the
    # content itself is well-structured for extraction, which AEO covers).

    def check_semantic_html(self):
        semantic_tags = ['article', 'section', 'main', 'nav', 'header', 'footer']
        found = [t for t in semantic_tags if self.soup.find(t)]
        return {
            'name': 'Semantic HTML5 Structure',
            'value': f'{len(found)}/6 semantic tags used ({", ".join(found) if found else "none"})',
            'pass': len(found) >= 3,
            'detail': 'Semantic tags (article, section, main) help AI parsers identify the actual content vs. navigation/boilerplate' if len(found) >= 3 else 'Page relies on generic <div> structure — AI crawlers work better with semantic HTML5 tags'
        }

    def check_content_to_code_ratio(self):
        if not self.html:
            return {'name': 'Content-to-Code Ratio', 'value': 'N/A', 'pass': False, 'detail': 'Could not measure'}
        text_len = len(self.soup.get_text(strip=True))
        html_len = len(self.html)
        ratio = (text_len / html_len * 100) if html_len else 0
        return {
            'name': 'Content-to-Code Ratio',
            'value': f'{ratio:.1f}% text vs markup',
            'pass': ratio >= 10,
            'detail': 'Healthy ratio of readable content to HTML markup' if ratio >= 10 else 'Too much markup relative to content — heavy scripts/divs can bury content from AI extractors'
        }

    def check_meta_robots_ai(self):
        tag = self.soup.find('meta', attrs={'name': 'robots'})
        content = tag.get('content', '').lower() if tag else ''
        blocked = 'noindex' in content
        return {
            'name': 'Meta Robots (AI Indexing)',
            'value': content or 'Not set (default: indexable)',
            'pass': not blocked,
            'detail': 'Page is indexable by AI crawlers' if not blocked else 'This page has a noindex tag — AI engines and Google will not index or cite it'
        }

    def run_geo_checks(self):
        return [
            self.check_semantic_html(),
            self.check_content_to_code_ratio(),
            self.check_meta_robots_ai(),
        ]

    # ---------------- PAGE-LEVEL TECHNICAL CHECKS ----------------

    def check_viewport(self):
        tag = self.soup.find('meta', attrs={'name': 'viewport'})
        return {
            'name': 'Mobile Viewport Tag',
            'value': tag.get('content', '') if tag else 'Missing',
            'pass': bool(tag),
            'detail': 'Page is configured for mobile responsiveness' if tag else 'No viewport meta tag — page may not display correctly on mobile, hurting mobile rankings'
        }

    def check_page_weight(self):
        size_kb = len(self.html.encode('utf-8')) / 1024 if self.html else 0
        return {
            'name': 'Page Size',
            'value': f'{size_kb:.0f} KB (HTML)',
            'pass': size_kb < 500,
            'detail': 'Reasonable page weight' if size_kb < 500 else 'Large HTML payload — can slow down load times and hurt Core Web Vitals'
        }

    def check_response_time(self, elapsed_seconds):
        return {
            'name': 'Server Response Time',
            'value': f'{elapsed_seconds:.2f}s',
            'pass': elapsed_seconds < 1.5,
            'detail': 'Fast server response' if elapsed_seconds < 1.5 else 'Slow server response — this directly impacts Core Web Vitals and rankings'
        }

    def run_technical_page_checks(self, elapsed_seconds=None):
        checks = [self.check_viewport(), self.check_page_weight()]
        if elapsed_seconds is not None:
            checks.append(self.check_response_time(elapsed_seconds))
        return checks

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
        if self.status_code and self.status_code >= 400:
            return {'error': f'Page returned status {self.status_code}', 'url': self.url}

        seo_checks = self.run_seo_checks()
        aeo_checks = self.run_aeo_checks()
        geo_checks = self.run_geo_checks()
        tech_checks = self.run_technical_page_checks(self.elapsed)

        seo_score = self.score_from_checks(seo_checks)
        aeo_score = self.score_from_checks(aeo_checks)
        geo_score = self.score_from_checks(geo_checks)
        tech_score = self.score_from_checks(tech_checks)
        overall_score = round((seo_score + aeo_score + geo_score + tech_score) / 4)

        # collect internal links found on this page (used by the crawler)
        internal_links = set()
        for a in self.soup.find_all('a', href=True):
            href = a['href']
            absolute = urljoin(self.url, href)
            absolute, _ = urldefrag(absolute)
            if urlparse(absolute).netloc == self.domain:
                internal_links.add(absolute)

        return {
            'url': self.url,
            'domain': self.domain,
            'seo_score': seo_score,
            'aeo_score': aeo_score,
            'geo_score': geo_score,
            'tech_score': tech_score,
            'overall_score': overall_score,
            'seo_checks': seo_checks,
            'aeo_checks': aeo_checks,
            'geo_checks': geo_checks,
            'tech_checks': tech_checks,
            'title': (self.soup.find('title').get_text().strip() if self.soup.find('title') else ''),
            'internal_links': internal_links,
        }


class SiteCrawler:
    """
    Crawls a website starting from a given URL, discovering internal pages
    via links, and runs the full SEO+AEO+GEO+Technical audit on each page.
    Also runs site-wide checks: robots.txt, sitemap.xml, llms.txt, and
    cross-page duplicate title/meta detection.
    """
    def __init__(self, start_url, max_pages=15):
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'https://' + start_url
        self.start_url = start_url
        self.domain = urlparse(start_url).netloc
        self.scheme = urlparse(start_url).scheme
        self.max_pages = max_pages
        self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }

    def _base(self):
        return f'{self.scheme}://{self.domain}'

    def check_robots_txt(self):
        url = urljoin(self._base(), '/robots.txt')
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return {
                    'name': 'robots.txt',
                    'value': f'Not found (status {resp.status_code})',
                    'pass': False,
                    'detail': 'No robots.txt found — search engines and AI crawlers assume full access by default, but a robots.txt is standard practice for crawl control'
                }, resp.text if resp.status_code == 200 else ''
            body = resp.text
            ai_bots = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended']
            blocked = []
            lower = body.lower()
            for bot in ai_bots:
                # crude check: bot named with a Disallow: / right after it
                if bot.lower() in lower:
                    section = lower.split(bot.lower())[1][:200]
                    if 'disallow: /' in section and 'disallow: /\n' not in section.replace(' ', ''):
                        pass
                    if re.search(r'disallow:\s*/\s*($|\n)', section):
                        blocked.append(bot)
            return {
                'name': 'robots.txt',
                'value': f'Found. AI bots blocked: {", ".join(blocked) if blocked else "none detected"}',
                'pass': len(blocked) == 0,
                'detail': 'robots.txt allows AI crawlers to access the site' if not blocked else f'robots.txt appears to block AI crawlers ({", ".join(blocked)}) — this prevents citation by tools like ChatGPT and Perplexity'
            }, body
        except Exception as e:
            return {
                'name': 'robots.txt',
                'value': f'Could not fetch ({e})',
                'pass': False,
                'detail': 'Could not verify robots.txt'
            }, ''

    def check_sitemap(self, robots_body):
        candidates = ['/sitemap.xml', '/sitemap_index.xml']
        if robots_body and 'sitemap:' in robots_body.lower():
            for line in robots_body.splitlines():
                if line.lower().startswith('sitemap:'):
                    candidates.insert(0, line.split(':', 1)[1].strip())
        for c in candidates:
            url = c if c.startswith('http') else urljoin(self._base(), c)
            try:
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.status_code == 200 and ('<urlset' in resp.text or '<sitemapindex' in resp.text):
                    return {
                        'name': 'XML Sitemap',
                        'value': f'Found at {url}',
                        'pass': True,
                        'detail': 'Sitemap helps search engines and AI crawlers discover all pages'
                    }
            except Exception:
                continue
        return {
            'name': 'XML Sitemap',
            'value': 'Not found',
            'pass': False,
            'detail': 'No XML sitemap found — this makes it harder for crawlers to discover and index all pages on the site'
        }

    def check_llms_txt(self):
        url = urljoin(self._base(), '/llms.txt')
        try:
            resp = requests.get(url, headers=self.headers, timeout=8)
            found = resp.status_code == 200
        except Exception:
            found = False
        return {
            'name': 'llms.txt (AI content guide)',
            'value': 'Found' if found else 'Not found',
            'pass': found,
            'detail': 'llms.txt gives AI models a curated guide to your site content — an emerging standard for AI discoverability' if found else 'No llms.txt file — this is an emerging (optional but increasingly recommended) standard that helps AI models understand site structure. Not yet widespread, so low priority.'
        }

    def check_broken_links(self, all_links, max_check=25):
        """Checks a capped sample of unique internal links found across the crawl for broken (4xx/5xx) responses. Runs in parallel to stay fast."""
        unique_links = list(dict.fromkeys(all_links))[:max_check]
        broken = []

        def check_one(link):
            try:
                resp = requests.head(link, headers=self.headers, timeout=5, allow_redirects=True)
                if resp.status_code >= 400:
                    resp2 = requests.get(link, headers=self.headers, timeout=5)
                    if resp2.status_code >= 400:
                        return (link, resp2.status_code)
                return None
            except Exception:
                return (link, 'unreachable')

        if unique_links:
            with ThreadPoolExecutor(max_workers=10) as executor:
                for result in executor.map(check_one, unique_links):
                    if result:
                        broken.append(result)

        checked_count = len(unique_links)
        if broken:
            items = [f'{url} ({code})' for url, code in broken[:15]]
            return {
                'name': 'Broken Internal Links',
                'value': f'{len(broken)} broken link(s) found (checked {checked_count})',
                'pass': False,
                'detail': 'Fix or remove these links — broken links waste crawl budget and hurt user experience: ' + '; '.join(items[:8]) + (f' (+{len(broken)-8} more)' if len(broken) > 8 else ''),
                'items': items,
            }
        return {
            'name': 'Broken Internal Links',
            'value': f'None found (checked {checked_count} links)',
            'pass': True,
            'detail': 'No broken internal links detected in the sample checked'
        }

    def fetch_pagespeed(self, url, strategy='mobile'):
        """
        Calls Google PageSpeed Insights for real Core Web Vitals and specific
        speed-optimization opportunities. Uses PAGESPEED_API_KEY env var if set
        (free from Google Cloud Console) for a much higher rate limit; falls
        back to unauthenticated calls otherwise, which are heavily rate-limited.
        """
        api_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
        params = {'url': url, 'strategy': strategy, 'category': 'performance'}
        api_key = os.environ.get('PAGESPEED_API_KEY')
        if api_key:
            params['key'] = api_key
        try:
            resp = requests.get(api_url, params=params, timeout=45)
            if resp.status_code != 200:
                return {'error': f'PageSpeed API returned status {resp.status_code}'}
            data = resp.json()
            lighthouse = data.get('lighthouseResult', {})
            perf_score = lighthouse.get('categories', {}).get('performance', {}).get('score')
            audits = lighthouse.get('audits', {})

            metrics = {}
            for key, label in [
                ('largest-contentful-paint', 'Largest Contentful Paint'),
                ('first-contentful-paint', 'First Contentful Paint'),
                ('total-blocking-time', 'Total Blocking Time'),
                ('cumulative-layout-shift', 'Cumulative Layout Shift'),
                ('speed-index', 'Speed Index'),
            ]:
                a = audits.get(key, {})
                if a:
                    metrics[label] = a.get('displayValue', 'N/A')

            opportunity_keys = [
                'render-blocking-resources', 'uses-optimized-images', 'unminified-css',
                'unminified-javascript', 'uses-text-compression', 'uses-responsive-images',
                'offscreen-images', 'unused-css-rules', 'unused-javascript',
                'efficient-animated-content', 'uses-long-cache-ttl', 'total-byte-weight',
            ]
            opportunities = []
            for key in opportunity_keys:
                a = audits.get(key)
                if a and a.get('score') is not None and a.get('score') < 0.9:
                    savings = a.get('displayValue', '')
                    opportunities.append({
                        'title': a.get('title', key),
                        'savings': savings,
                        'description': a.get('description', '').split('. ')[0] + '.' if a.get('description') else '',
                    })

            return {
                'performance_score': round(perf_score * 100) if perf_score is not None else None,
                'metrics': metrics,
                'opportunities': opportunities,
            }
        except Exception as e:
            return {'error': str(e)}

    def discover_links(self, homepage_analysis):
        to_visit = list(homepage_analysis.get('internal_links', []))
        # prioritize likely-useful pages, skip obvious junk (files, anchors already stripped)
        skip_ext = ('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.svg', '.css', '.js', '.xml', '.mp4')
        clean = [u for u in to_visit if not u.lower().endswith(skip_ext)]
        return clean

    def crawl(self):
        results = {'error': None}

        # Site-wide technical checks first
        robots_check, robots_body = self.check_robots_txt()
        sitemap_check = self.check_sitemap(robots_body)
        llms_check = self.check_llms_txt()
        site_technical_checks = [robots_check, sitemap_check, llms_check]

        # Homepage
        homepage = SiteAnalyzer(self.start_url)
        homepage_result = homepage.analyze()
        if 'error' in homepage_result:
            err = homepage_result['error']
            if 'status 403' in err or 'status 406' in err:
                err += ' — this site may be blocking automated tools (bot protection/firewall). Try again, or this site may need to be checked manually.'
            return {'error': err, 'url': self.start_url}

        pages = [homepage_result]
        visited = {self.start_url, urldefrag(self.start_url)[0]}

        candidates = self.discover_links(homepage_result)
        to_fetch = []
        for link in candidates:
            if len(to_fetch) + len(pages) >= self.max_pages:
                break
            if link in visited:
                continue
            visited.add(link)
            to_fetch.append(link)

        # Fetch remaining pages in parallel to stay within request time limits
        if to_fetch:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(lambda u: SiteAnalyzer(u).analyze(), link): link for link in to_fetch}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if 'error' not in result:
                            pages.append(result)
                    except Exception:
                        continue

        # Aggregate scores across pages
        def avg(key):
            vals = [p[key] for p in pages if key in p]
            return round(sum(vals) / len(vals)) if vals else 0

        seo_avg = avg('seo_score')
        aeo_avg = avg('aeo_score')
        geo_avg = avg('geo_score')
        tech_page_avg = avg('tech_score')

        # Broken link check across all internal links discovered site-wide
        all_links_seen = set()
        for p in pages:
            all_links_seen.update(p.get('internal_links', []))
        broken_links_check = self.check_broken_links(list(all_links_seen))
        site_technical_checks.append(broken_links_check)

        # Real speed diagnostics (Google PageSpeed Insights) — homepage only,
        # since a full Lighthouse run per page would make multi-page audits too slow.
        pagespeed = self.fetch_pagespeed(self.start_url)

        # site-wide technical score blends page-level technical avg with site-wide checks
        site_tech_pass = sum(1 for c in site_technical_checks if c['pass'])
        site_tech_score = round((site_tech_pass / len(site_technical_checks)) * 100)
        combined_tech_score = round((tech_page_avg + site_tech_score) / 2)

        overall = round((seo_avg + aeo_avg + geo_avg + combined_tech_score) / 4)

        # Duplicate title / meta description detection across crawled pages
        title_map = {}
        meta_map = {}
        for p in pages:
            title_check = next((c for c in p['seo_checks'] if c['name'] == 'Title Tag'), None)
            meta_check = next((c for c in p['seo_checks'] if c['name'] == 'Meta Description'), None)
            if title_check and title_check['value'] not in ('Missing',):
                title_map.setdefault(title_check['value'], []).append(p['url'])
            if meta_check and meta_check['value'] not in ('Missing',):
                meta_map.setdefault(meta_check['value'], []).append(p['url'])

        duplicate_titles = {k: v for k, v in title_map.items() if len(v) > 1}
        duplicate_metas = {k: v for k, v in meta_map.items() if len(v) > 1}

        site_wide_issues = []
        if duplicate_titles:
            site_wide_issues.append({
                'name': 'Duplicate Title Tags',
                'value': f'{len(duplicate_titles)} title(s) reused across {sum(len(v) for v in duplicate_titles.values())} pages',
                'pass': False,
                'detail': 'Multiple pages share the same title tag — this confuses search engines about which page to rank for a query'
            })
        else:
            site_wide_issues.append({
                'name': 'Duplicate Title Tags',
                'value': 'None found',
                'pass': True,
                'detail': 'Each crawled page has a unique title tag'
            })
        if duplicate_metas:
            site_wide_issues.append({
                'name': 'Duplicate Meta Descriptions',
                'value': f'{len(duplicate_metas)} description(s) reused across {sum(len(v) for v in duplicate_metas.values())} pages',
                'pass': False,
                'detail': 'Multiple pages share the same meta description — reduces click-through rate differentiation in search results'
            })
        else:
            site_wide_issues.append({
                'name': 'Duplicate Meta Descriptions',
                'value': 'None found',
                'pass': True,
                'detail': 'Each crawled page has a unique meta description'
            })

        return {
            'url': self.start_url,
            'domain': self.domain,
            'pages_crawled': len(pages),
            'seo_score': seo_avg,
            'aeo_score': aeo_avg,
            'geo_score': geo_avg,
            'tech_score': combined_tech_score,
            'overall_score': overall,
            'site_technical_checks': site_technical_checks,
            'site_wide_issues': site_wide_issues,
            'duplicate_titles': duplicate_titles,
            'duplicate_metas': duplicate_metas,
            'pagespeed': pagespeed,
            'pages': pages,
        }


if __name__ == '__main__':
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://example.com'
    result = SiteAnalyzer(url).analyze()
    print(json.dumps(result, indent=2))
