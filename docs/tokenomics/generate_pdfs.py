#!/usr/bin/env python3
"""
Generate branded PDFs for PURECORTEX tokenomics documents.
Uses weasyprint to render Markdown → HTML → PDF with brand styling.

Brand palette:
  - Obsidian:    #050505 (background/header)
  - Neural Blue: #007AFF (accent/headings)
  - Pure White:  #FFFFFF (text on dark)
  - Graphite:    #1A1A1A (secondary bg)

Usage:
    .venv/bin/python generate_pdfs.py
"""

import os
import base64
import markdown
from weasyprint import HTML

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "..", "branding", "final", "png", "primary_1200.png")
ICON_PATH = os.path.join(BASE_DIR, "..", "..", "branding", "final", "png", "icon_512.png")
OUTPUT_DIR = os.path.join(BASE_DIR, "pdf")

# ── Documents to convert ──────────────────────────────────────────────
DOCUMENTS = [
    {
        "input": os.path.join(BASE_DIR, "constitution", "PREAMBLE.md"),
        "output": "PureCortex_Constitution_Preamble.pdf",
        "title": "The PURECORTEX Constitution",
        "subtitle": "Preamble — Immutable Foundation",
    },
    {
        "input": os.path.join(BASE_DIR, "constitution", "ARTICLES.md"),
        "output": "PureCortex_Constitution_Articles.pdf",
        "title": "The PURECORTEX Constitution",
        "subtitle": "Articles I–VII — Governance Framework",
    },
    {
        "input": os.path.join(BASE_DIR, "TOKENOMICS_SUMMARY.md"),
        "output": "PureCortex_Tokenomics_Summary.pdf",
        "title": "PURECORTEX Tokenomics",
        "subtitle": "Token Economics & Governance Overview",
    },
]


def load_image_base64(path: str) -> str:
    """Load an image and return as base64 data URI."""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


def get_css() -> str:
    """Return the branded CSS stylesheet."""
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    @page {
        size: letter;
        margin: 0.8in 0.9in 1in 0.9in;
        @bottom-center {
            content: counter(page);
            font-family: 'Inter', sans-serif;
            font-size: 9pt;
            color: #666;
        }
        @bottom-right {
            content: "PURECORTEX — Confidential";
            font-family: 'Inter', sans-serif;
            font-size: 8pt;
            color: #999;
        }
    }

    @page :first {
        margin-top: 0;
        @bottom-center { content: none; }
        @bottom-right { content: none; }
    }

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 10.5pt;
        line-height: 1.65;
        color: #1A1A1A;
    }

    /* ── Cover / Header ─────────────────────────────────────── */
    .cover {
        background: linear-gradient(135deg, #050505 0%, #0a1628 50%, #050505 100%);
        color: #FFFFFF;
        padding: 2.5in 0.9in 1.5in 0.9in;
        margin: -0.8in -0.9in 0 -0.9in;
        page-break-after: always;
        text-align: center;
    }

    .cover img.logo {
        width: 280px;
        margin-bottom: 40px;
    }

    .cover h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 28pt;
        color: #FFFFFF;
        letter-spacing: -0.5px;
        margin-bottom: 12px;
    }

    .cover h1 span.blue {
        color: #007AFF;
    }

    .cover .subtitle {
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        font-size: 13pt;
        color: #8ab4f8;
        margin-bottom: 40px;
    }

    .cover .meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9pt;
        color: #666;
        margin-top: 60px;
    }

    .cover .divider {
        width: 60px;
        height: 3px;
        background: #007AFF;
        margin: 30px auto;
        border-radius: 2px;
    }

    /* ── Headings ────────────────────────────────────────────── */
    h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 20pt;
        color: #050505;
        margin-top: 30px;
        margin-bottom: 12px;
        letter-spacing: -0.3px;
        border-bottom: 3px solid #007AFF;
        padding-bottom: 8px;
    }

    h2 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 15pt;
        color: #007AFF;
        margin-top: 24px;
        margin-bottom: 8px;
    }

    h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 12pt;
        color: #1A1A1A;
        margin-top: 18px;
        margin-bottom: 6px;
    }

    h4 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 11pt;
        color: #333;
        margin-top: 14px;
        margin-bottom: 4px;
    }

    /* ── Body text ───────────────────────────────────────────── */
    p {
        margin-bottom: 10px;
        text-align: justify;
        hyphens: auto;
    }

    strong {
        font-weight: 700;
        color: #050505;
    }

    em {
        font-style: italic;
    }

    /* ── Lists ───────────────────────────────────────────────── */
    ul, ol {
        margin: 8px 0 12px 20px;
    }

    li {
        margin-bottom: 4px;
    }

    li > ul, li > ol {
        margin-top: 4px;
        margin-bottom: 4px;
    }

    /* ── Tables ──────────────────────────────────────────────── */
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 9.5pt;
    }

    thead {
        background: #050505;
        color: #FFFFFF;
    }

    thead th {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        padding: 8px 10px;
        text-align: left;
        border: none;
    }

    tbody td {
        padding: 7px 10px;
        border-bottom: 1px solid #e0e0e0;
    }

    tbody tr:nth-child(even) {
        background: #f8f9fa;
    }

    tbody tr:hover {
        background: #e8f0fe;
    }

    /* ── Code ────────────────────────────────────────────────── */
    code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9pt;
        background: #f0f4f8;
        padding: 1px 5px;
        border-radius: 3px;
        color: #007AFF;
    }

    pre {
        background: #1A1A1A;
        color: #e0e0e0;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 12px 0;
        font-size: 8.5pt;
        line-height: 1.5;
        overflow-x: auto;
        border-left: 4px solid #007AFF;
    }

    pre code {
        background: none;
        color: inherit;
        padding: 0;
    }

    /* ── Blockquotes ─────────────────────────────────────────── */
    blockquote {
        border-left: 4px solid #007AFF;
        background: #f0f7ff;
        padding: 12px 16px;
        margin: 12px 0;
        font-style: italic;
        color: #333;
    }

    /* ── Horizontal rule ─────────────────────────────────────── */
    hr {
        border: none;
        border-top: 2px solid #007AFF;
        margin: 24px 0;
        opacity: 0.3;
    }

    /* ── Utilities ───────────────────────────────────────────── */
    .page-break {
        page-break-before: always;
    }
    """


def md_to_branded_pdf(input_path: str, output_path: str, title: str, subtitle: str):
    """Convert a Markdown file to a branded PDF."""
    with open(input_path, "r") as f:
        md_content = f.read()

    # Convert Markdown to HTML
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "toc", "attr_list"],
    )

    # Load logo as base64
    logo_b64 = load_image_base64(LOGO_PATH)

    # Build full HTML document
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <style>{get_css()}</style>
</head>
<body>
    <div class="cover">
        <img class="logo" src="{logo_b64}" alt="PURECORTEX">
        <h1>{title}</h1>
        <div class="divider"></div>
        <div class="subtitle">{subtitle}</div>
        <div class="meta">
            March 2026 &nbsp;|&nbsp; Algorand Blockchain &nbsp;|&nbsp; purecortex.ai
        </div>
    </div>
    {html_body}
</body>
</html>"""

    HTML(string=html_doc).write_pdf(output_path)
    print(f"  Generated: {output_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("PURECORTEX Branded PDF Generator")
    print("=" * 60)

    for doc in DOCUMENTS:
        input_path = doc["input"]
        output_path = os.path.join(OUTPUT_DIR, doc["output"])

        if not os.path.exists(input_path):
            print(f"  SKIP (not found): {input_path}")
            continue

        print(f"\n  Processing: {os.path.basename(input_path)}")
        md_to_branded_pdf(input_path, output_path, doc["title"], doc["subtitle"])

    print(f"\n{'=' * 60}")
    print(f"All PDFs saved to: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
