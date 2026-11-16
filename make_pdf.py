#!/usr/bin/env python3
"""Export a vector PDF with selectable text, deterministic charts and 12 pages."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from scripts.browser import ROOT,launch,ready

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/star-guard-deck.pdf')
    args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=launch(p)
        try:
            page=browser.new_page(viewport={'width':1920,'height':1080})
            errors=ready(page)
            page.pdf(path=str(args.output),prefer_css_page_size=True,print_background=True,display_header_footer=False)
            if errors:raise RuntimeError('\n'.join(errors))
        finally:browser.close()
    from pypdf import PdfReader
    pdf=PdfReader(args.output)
    if len(pdf.pages)!=12:raise RuntimeError(f'Expected 12 PDF pages, got {len(pdf.pages)}')
    if not all((page.extract_text() or '').strip() for page in pdf.pages):raise RuntimeError('Missing searchable text in PDF')
    print(f'Exported {args.output.name}: 12 pages, selectable text')

if __name__=='__main__':main()
