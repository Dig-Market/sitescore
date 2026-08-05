"""
SiteScore PDF Report Generator
Generates a branded client-facing PDF from analyzer results.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import datetime

# Brand colors - change these to match your agency branding
PRIMARY = HexColor('#1a1a2e')
ACCENT = HexColor('#0f9d58')
WARN = HexColor('#d93025')
LIGHT_GREY = HexColor('#f5f5f5')
TEXT_GREY = HexColor('#555555')


def _score_color(score):
    if score >= 80:
        return ACCENT
    elif score >= 50:
        return HexColor('#f4b400')
    return WARN


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle', fontSize=24, leading=28, textColor=PRIMARY,
        spaceAfter=8, fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='ReportSubtitle', fontSize=11, leading=15, textColor=TEXT_GREY,
        spaceBefore=6, spaceAfter=14
    ))
    styles.add(ParagraphStyle(
        name='SectionHeading', fontSize=15, leading=19, textColor=PRIMARY,
        spaceBefore=18, spaceAfter=8, fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='ScoreBig', fontSize=36, leading=42, alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='ScoreLabel', fontSize=10, leading=13, alignment=TA_CENTER,
        textColor=TEXT_GREY
    ))
    styles.add(ParagraphStyle(
        name='CheckDetail', fontSize=9, leading=13, textColor=TEXT_GREY, leftIndent=10
    ))
    return styles


def build_score_table(seo_score, aeo_score, overall_score, styles):
    def score_para(score):
        color = _score_color(score)
        return Paragraph(f'<font color="{color.hexval()}">{score}</font>', styles['ScoreBig'])

    data = [
        [score_para(overall_score), score_para(seo_score), score_para(aeo_score)],
        [Paragraph('OVERALL', styles['ScoreLabel']),
         Paragraph('SEO SCORE', styles['ScoreLabel']),
         Paragraph('AEO SCORE', styles['ScoreLabel'])],
    ]
    col_width = 2.1 * inch
    t = Table(data, colWidths=[col_width, col_width, col_width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 14),
    ]))
    return t


def build_checks_table(checks, styles):
    cell_style = ParagraphStyle(name='CellText', fontSize=9, textColor=HexColor('#222222'), leading=11)
    header_style = ParagraphStyle(name='CellHeader', fontSize=9, textColor=HexColor('#ffffff'), fontName='Helvetica-Bold')

    rows = [[
        Paragraph('Check', header_style),
        Paragraph('Result', header_style),
        Paragraph('Status', header_style),
    ]]
    for c in checks:
        status = 'PASS' if c['pass'] else 'NEEDS WORK'
        color = ACCENT if c['pass'] else WARN
        status_style = ParagraphStyle(name='Status', fontSize=9, textColor=color, fontName='Helvetica-Bold')
        rows.append([
            Paragraph(c['name'], cell_style),
            Paragraph(c['value'][:90], cell_style),
            Paragraph(status, status_style),
        ])

    t = Table(rows, colWidths=[1.7*inch, 3.9*inch, 1.0*inch], repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), LIGHT_GREY]),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


def build_issues_table(checks, styles):
    """
    Ubersuggest-style 'action items' table: shows ONLY failing checks with
    the specific fix instructions (the 'detail' text), which includes exact
    file names / URLs where available. Passing checks are omitted here since
    the goal is a fix-it list, not a full audit trail.
    """
    failed = [c for c in checks if not c['pass']]
    if not failed:
        return Paragraph('No issues found on this page. All checks passed.', ParagraphStyle(
            name='AllGood', fontSize=10, textColor=ACCENT, fontName='Helvetica-Bold'
        ))

    name_style = ParagraphStyle(name='IssueName', fontSize=9.5, fontName='Helvetica-Bold', textColor=HexColor('#1a1a2e'), leading=12)
    fix_style = ParagraphStyle(name='IssueFix', fontSize=8.5, textColor=TEXT_GREY, leading=11)

    rows = [[Paragraph('Issue', ParagraphStyle(name='H1', fontSize=9, textColor=HexColor('#ffffff'), fontName='Helvetica-Bold')),
             Paragraph('How to fix it', ParagraphStyle(name='H2', fontSize=9, textColor=HexColor('#ffffff'), fontName='Helvetica-Bold'))]]
    for c in failed:
        rows.append([
            Paragraph(c['name'], name_style),
            Paragraph(c['detail'], fix_style),
        ])

    t = Table(rows, colWidths=[1.6*inch, 5.0*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), WARN),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#fff8f7')]),
    ]))
    return t


def build_pagespeed_section(pagespeed, styles):
    if not pagespeed or pagespeed.get('error'):
        return [Paragraph(
            'Speed diagnostics could not be retrieved for this page (the checker may be temporarily rate-limited — this does not affect the other scores).',
            ParagraphStyle(name='PSErr', fontSize=9, textColor=TEXT_GREY)
        )]

    elements = []
    score = pagespeed.get('performance_score')
    if score is not None:
        color = _score_color(score)
        elements.append(Paragraph(
            f'Google PageSpeed Performance Score: <font color="{color.hexval()}"><b>{score}/100</b></font> (mobile)',
            ParagraphStyle(name='PSScore', fontSize=11, spaceAfter=8)
        ))

    metrics = pagespeed.get('metrics', {})
    if metrics:
        cell_style = ParagraphStyle(name='MetricCell', fontSize=9, textColor=HexColor('#222222'))
        header_style = ParagraphStyle(name='MetricHeader', fontSize=9, textColor=HexColor('#ffffff'), fontName='Helvetica-Bold')
        rows = [[Paragraph('Metric', header_style), Paragraph('Value', header_style)]]
        for k, v in metrics.items():
            rows.append([Paragraph(k, cell_style), Paragraph(str(v), cell_style)])
        t = Table(rows, colWidths=[3.3*inch, 3.3*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), LIGHT_GREY]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

    opportunities = pagespeed.get('opportunities', [])
    if opportunities:
        elements.append(Paragraph('Specific things slowing this page down:', ParagraphStyle(
            name='OppHead', fontSize=10, fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=6
        )))
        for o in opportunities:
            text = f"<b>{o['title']}</b>"
            if o.get('savings'):
                text += f" — potential savings: {o['savings']}"
            elements.append(Paragraph(text, ParagraphStyle(name='OppItem', fontSize=9, leading=13, spaceAfter=4, leftIndent=8)))
    elif score is not None:
        elements.append(Paragraph('No major speed issues detected.', ParagraphStyle(name='OppNone', fontSize=9, textColor=ACCENT)))

    return elements


def build_recommendations(checks, styles):
    failed = [c for c in checks if not c['pass']]
    if not failed:
        return [Paragraph('All checks passed. No immediate action items.', styles['Normal'])]
    items = []
    for c in failed:
        items.append(Paragraph(f"<b>{c['name']}:</b> {c['detail']}", styles['CheckDetail']))
        items.append(Spacer(1, 4))
    return items


def generate_report(analysis, output_path, agency_name="Dig Market", client_name=None):
    """
    analysis: dict returned by SiteAnalyzer.analyze()
    output_path: where to save the PDF
    """
    styles = build_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        leftMargin=0.6*inch, rightMargin=0.6*inch
    )
    story = []

    # Header
    story.append(Paragraph(f'{agency_name}', ParagraphStyle(
        name='Brand', fontSize=12, textColor=ACCENT, fontName='Helvetica-Bold'
    )))
    story.append(Paragraph('SEO & AI Search Visibility Report', styles['ReportTitle']))
    subtitle = analysis['url']
    if client_name:
        subtitle = f'Prepared for {client_name} — {subtitle}'
    story.append(Paragraph(subtitle, styles['ReportSubtitle']))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y')}",
        ParagraphStyle(name='Date', fontSize=9, textColor=TEXT_GREY)
    ))
    story.append(Spacer(1, 20))

    # Score summary
    story.append(build_score_table(
        analysis['seo_score'], analysis['aeo_score'], analysis['overall_score'], styles
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        'This report evaluates two dimensions of search visibility: traditional '
        'on-page SEO (how well the page ranks in Google/Bing) and AI Answer '
        'Engine Optimization or AEO (how likely the page is to be surfaced or '
        'cited by AI tools such as ChatGPT, Perplexity, and Google AI Overviews).',
        styles['Normal']
    ))

    # SEO Section
    story.append(Paragraph('On-Page SEO Analysis', styles['SectionHeading']))
    story.append(build_checks_table(analysis['seo_checks'], styles))
    story.append(Spacer(1, 8))
    story.append(Paragraph('Recommendations:', ParagraphStyle(
        name='RecHead', fontSize=10, fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=4
    )))
    story.extend(build_recommendations(analysis['seo_checks'], styles))

    story.append(PageBreak())

    # AEO Section
    story.append(Paragraph('AI Search Visibility (AEO) Analysis', styles['SectionHeading']))
    story.append(Paragraph(
        'AI answer engines increasingly answer user queries directly, often '
        'without a click-through to the source site. Pages that are structured '
        'for direct extraction are more likely to be cited as the source.',
        styles['Normal']
    ))
    story.append(Spacer(1, 10))
    story.append(build_checks_table(analysis['aeo_checks'], styles))
    story.append(Spacer(1, 8))
    story.append(Paragraph('Recommendations:', ParagraphStyle(
        name='RecHead2', fontSize=10, fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=4
    )))
    story.extend(build_recommendations(analysis['aeo_checks'], styles))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f'Report generated by {agency_name} — SiteScore Analysis Tool',
        ParagraphStyle(name='Footer', fontSize=8, textColor=TEXT_GREY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return output_path


def build_score_table_4(scores, styles):
    """scores: dict with keys overall, seo, aeo, geo, tech"""
    def score_para(score):
        color = _score_color(score)
        return Paragraph(f'<font color="{color.hexval()}">{score}</font>', ParagraphStyle(
            name='ScoreBig4', fontSize=28, leading=32, alignment=TA_CENTER, fontName='Helvetica-Bold'
        ))
    labels = ['OVERALL', 'SEO', 'AEO', 'GEO', 'TECHNICAL']
    keys = ['overall', 'seo', 'aeo', 'geo', 'tech']
    data = [
        [score_para(scores[k]) for k in keys],
        [Paragraph(l, styles['ScoreLabel']) for l in labels],
    ]
    col_width = 1.26 * inch
    t = Table(data, colWidths=[col_width] * 5)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
    ]))
    return t


def build_simple_check_table(checks, styles):
    """Same as build_checks_table but usable standalone for site-wide checks."""
    return build_checks_table(checks, styles)


def build_pages_summary_table(pages, styles):
    cell_style = ParagraphStyle(name='PageCell', fontSize=8.5, textColor=HexColor('#222222'), leading=11)
    header_style = ParagraphStyle(name='PageHeader', fontSize=8.5, textColor=HexColor('#ffffff'), fontName='Helvetica-Bold')

    rows = [[
        Paragraph('Page URL', header_style),
        Paragraph('SEO', header_style),
        Paragraph('AEO', header_style),
        Paragraph('GEO', header_style),
        Paragraph('Tech', header_style),
    ]]
    for p in pages:
        url_display = p['url']
        if len(url_display) > 55:
            url_display = url_display[:52] + '...'
        rows.append([
            Paragraph(url_display, cell_style),
            Paragraph(str(p['seo_score']), cell_style),
            Paragraph(str(p['aeo_score']), cell_style),
            Paragraph(str(p['geo_score']), cell_style),
            Paragraph(str(p['tech_score']), cell_style),
        ])

    t = Table(rows, colWidths=[3.9*inch, 0.65*inch, 0.65*inch, 0.65*inch, 0.65*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), LIGHT_GREY]),
    ]))
    return t


def generate_site_report(crawl_result, output_path, agency_name="Dig Market", client_name=None):
    """
    crawl_result: dict returned by SiteCrawler.crawl()
    Generates a multi-page site-wide audit report.
    """
    styles = build_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        leftMargin=0.6*inch, rightMargin=0.6*inch
    )
    story = []

    # Header
    story.append(Paragraph(f'{agency_name}', ParagraphStyle(
        name='Brand', fontSize=12, textColor=ACCENT, fontName='Helvetica-Bold'
    )))
    story.append(Paragraph('Site-Wide SEO, AEO & GEO Audit', styles['ReportTitle']))
    subtitle = f"{crawl_result['url']} — {crawl_result['pages_crawled']} pages crawled"
    if client_name:
        subtitle = f'Prepared for {client_name} — {subtitle}'
    story.append(Paragraph(subtitle, styles['ReportSubtitle']))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y')}",
        ParagraphStyle(name='Date', fontSize=9, textColor=TEXT_GREY)
    ))
    story.append(Spacer(1, 20))

    scores = {
        'overall': crawl_result['overall_score'],
        'seo': crawl_result['seo_score'],
        'aeo': crawl_result['aeo_score'],
        'geo': crawl_result['geo_score'],
        'tech': crawl_result['tech_score'],
    }
    story.append(build_score_table_4(scores, styles))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        'This report averages scores across every crawled page and checks site-wide '
        'factors: SEO (on-page ranking fundamentals), AEO (readiness to be cited by AI '
        'answer engines like ChatGPT and Perplexity), GEO (accessibility to generative '
        'AI crawlers), and Technical health (mobile-friendliness, speed, crawlability).',
        styles['Normal']
    ))

    story.append(Spacer(1, 16))
    story.append(Paragraph('Site-Wide Technical Checks', styles['SectionHeading']))
    story.append(build_simple_check_table(crawl_result['site_technical_checks'], styles))

    # Full detail for broken links (URLs get truncated in the table above)
    broken_check = next((c for c in crawl_result['site_technical_checks'] if c['name'] == 'Broken Internal Links'), None)
    if broken_check and not broken_check['pass'] and broken_check.get('items'):
        story.append(Spacer(1, 8))
        story.append(Paragraph('Broken links found:', ParagraphStyle(name='BrokenHead', fontSize=10, fontName='Helvetica-Bold', spaceAfter=4)))
        for item in broken_check['items']:
            story.append(Paragraph(f'• {item}', ParagraphStyle(name='BrokenItem', fontSize=9, textColor=WARN, leftIndent=10, spaceAfter=2)))

    story.append(Spacer(1, 16))
    story.append(Paragraph('Cross-Page Issues', styles['SectionHeading']))
    story.append(build_simple_check_table(crawl_result['site_wide_issues'], styles))

    if crawl_result.get('duplicate_titles'):
        story.append(Spacer(1, 8))
        story.append(Paragraph('Pages sharing the same title tag:', ParagraphStyle(name='DupHead', fontSize=10, fontName='Helvetica-Bold', spaceAfter=4)))
        for title, urls in crawl_result['duplicate_titles'].items():
            story.append(Paragraph(f'"{title}"', ParagraphStyle(name='DupTitle', fontSize=9, fontName='Helvetica-Bold', leftIndent=10, spaceBefore=4)))
            for u in urls:
                story.append(Paragraph(f'• {u}', ParagraphStyle(name='DupUrl', fontSize=8.5, textColor=TEXT_GREY, leftIndent=18, spaceAfter=1)))

    story.append(PageBreak())
    story.append(Paragraph('Per-Page Score Breakdown', styles['SectionHeading']))
    story.append(Paragraph(
        f"Scores for each of the {crawl_result['pages_crawled']} pages crawled. "
        'Use this to spot which specific pages need the most attention.',
        styles['Normal']
    ))
    story.append(Spacer(1, 10))
    story.append(build_pages_summary_table(crawl_result['pages'], styles))

    # Speed diagnostics (homepage only — full Lighthouse run is too slow to run per-page)
    story.append(PageBreak())
    story.append(Paragraph('Speed Diagnostics (Homepage)', styles['SectionHeading']))
    story.append(Paragraph(
        'Real-world speed test via Google PageSpeed Insights. Run on the homepage only — '
        'a full test on every page would make multi-page audits take too long.',
        styles['Normal']
    ))
    story.append(Spacer(1, 10))
    story.extend(build_pagespeed_section(crawl_result.get('pagespeed'), styles))

    # Per-page "issues + fixes" detail. For small audits, every page gets full
    # detail. For large audits (lots of pages), the PDF would become enormous,
    # so we only include pages that actually have issues, capped at 60 —
    # the live web dashboard has full click-to-expand detail for every page.
    pages_with_issues = []
    for p in crawl_result['pages']:
        all_checks = p['seo_checks'] + p['aeo_checks'] + p['geo_checks'] + p['tech_checks']
        if any(not c['pass'] for c in all_checks):
            pages_with_issues.append((p, all_checks))

    detail_cap = 60
    truncated = len(pages_with_issues) > detail_cap

    story.append(PageBreak())
    story.append(Paragraph('Per-Page Issues & Fixes', styles['SectionHeading']))
    if len(crawl_result['pages']) > detail_cap:
        note = (
            f"{len(pages_with_issues)} of {len(crawl_result['pages'])} crawled pages have at least one issue. "
        )
        if truncated:
            note += f"Showing the first {detail_cap} below — see the live web dashboard for every page."
        else:
            note += "Pages with no issues are omitted from this section."
        story.append(Paragraph(note, styles['Normal']))
        story.append(Spacer(1, 8))

    for p, all_checks in pages_with_issues[:detail_cap]:
        story.append(PageBreak())
        story.append(Paragraph(f"Issues Found: {p['url']}", styles['SectionHeading']))
        story.append(Spacer(1, 6))
        story.append(build_issues_table(all_checks, styles))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f'Report generated by {agency_name} — SiteScore Analysis Tool',
        ParagraphStyle(name='Footer', fontSize=8, textColor=TEXT_GREY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return output_path


if __name__ == '__main__':
    # quick manual test
    from analyzer import SiteAnalyzer
    from bs4 import BeautifulSoup
    test_html = open('test_page.html').read() if False else None
