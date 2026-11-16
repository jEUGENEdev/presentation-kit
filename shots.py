#!/usr/bin/env python3
"""Capture deterministic slide screenshots for visual review."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from scripts.browser import ROOT,launch,ready

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/shots')
    parser.add_argument('--live',action='store_true',help='Capture live animation instead of export state')
    parser.add_argument('--delay',type=int,default=4500)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=launch(p)
        try:
            page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
            errors=ready(page,export=not args.live)
            for i in range(12):
                page.evaluate('(i)=>window.__go(i)',i)
                if args.live:page.wait_for_timeout(args.delay)
                page.screenshot(path=str(args.output/f'slide-{i+1:02}.png'))
            if errors:raise RuntimeError('\n'.join(errors))
            print(f'12 slides captured in {args.output}; no JavaScript errors')
        finally:browser.close()

if __name__=='__main__':main()
