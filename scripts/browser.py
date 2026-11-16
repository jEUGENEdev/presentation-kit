"""Portable browser discovery shared by screenshots, PDF export and UI tests."""
import os
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def launch(playwright):
    explicit=os.environ.get('CHROME_PATH')
    if explicit:
        if not Path(explicit).is_file():
            raise RuntimeError(f'CHROME_PATH is not a file: {explicit}')
        return playwright.chromium.launch(executable_path=explicit)
    if Path(playwright.chromium.executable_path).is_file():
        return playwright.chromium.launch()
    for name in ['google-chrome','chromium','chromium-browser','chrome','msedge']:
        path=shutil.which(name)
        if path: return playwright.chromium.launch(executable_path=path)
    raise RuntimeError('Chromium not found. Run: python -m playwright install chromium, or set CHROME_PATH.')

def ready(page, path=None, export=True):
    path=Path(path) if path else ROOT/'dist/index.html'
    if not path.exists(): raise RuntimeError('Build first: python build.py')
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(path.resolve().as_uri()+('?export=1' if export else ''))
    page.evaluate('document.fonts.ready')
    page.wait_for_function('window.deckState && window.deckState().total === 12')
    page.wait_for_function('[...document.images].every(i => i.complete && i.naturalWidth > 0)')
    return errors
