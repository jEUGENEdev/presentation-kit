#!/usr/bin/env python3
"""Capture deterministic slides, optionally both themes and visual review sheets."""
import argparse
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright
from scripts.browser import ROOT,launch,ready

def contact_sheet(folder):
    from PIL import Image
    sheet=Image.new('RGB',(1440,1080),'#ddd')
    for i in range(12):
        with Image.open(folder/f'slide-{i+1:02}.png') as frame:
            frame.thumbnail((480,270))
            sheet.paste(frame,((i%3)*480,(i//3)*270))
    path=folder/'contact-sheet.jpg'
    sheet.save(path,quality=84)
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/shots')
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--delay',type=int,default=4500)
    parser.add_argument('--theme',choices=['light','dark','both'],default='light')
    parser.add_argument('--review-log',action='store_true',help='Embed review sheets in logs for text-only CI clients')
    args=parser.parse_args()
    themes=['light','dark'] if args.theme=='both' else [args.theme]
    with sync_playwright() as p:
        browser=launch(p)
        try:
            for theme in themes:
                folder=args.output/theme;folder.mkdir(parents=True,exist_ok=True)
                page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
                errors=ready(page,export=not args.live,theme=theme)
                for i in range(12):
                    page.evaluate('(i)=>window.__go(i)',i)
                    if args.live:page.wait_for_timeout(args.delay)
                    page.screenshot(path=str(folder/f'slide-{i+1:02}.png'))
                if errors:raise RuntimeError('\n'.join(errors))
                sheet=contact_sheet(folder)
                if args.review_log:
                    print(f'REVIEW_IMAGE_{theme}:'+base64.b64encode(sheet.read_bytes()).decode('ascii'))
                print(f'12 {theme} slides captured; no JavaScript errors')
                page.close()
        finally:browser.close()

if __name__=='__main__':main()
