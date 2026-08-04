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


if __name__ == '__main__':
    # quick manual test
    from analyzer import SiteAnalyzer
    from bs4 import BeautifulSoup
    test_html = open('test_page.html').read() if False else None
