"""Browser regression checks. Run from any directory: python tests/browser_checks.py."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from scripts.browser import launch,ready,ROOT

def check(condition,message):
    if not condition:raise AssertionError(message)

def run():
    with sync_playwright() as p:
        browser=launch(p)
        try:
            page=browser.new_page(viewport={'width':1920,'height':1080})
            requests=[];page.on('request',lambda r:requests.append(r.url))
            page.emulate_media(reduced_motion='reduce')
            errors=ready(page,export=False)
            for i in range(12):
                page.evaluate('(i)=>window.__go(i)',i)
                check(page.locator('.slide.active').count()==1,f'Slide {i+1}: active state')
                # Text should remain inside the stage; font metrics are checked in Chromium.
                overflow=page.evaluate('''() => [...document.querySelectorAll('.slide.active h1,.slide.active h2,.slide.active h3,.slide.active p,.slide.active table,.slide.active figure')].filter(e=>{const r=e.getBoundingClientRect();return r.left < -1 || r.right > 1921 || r.top < -1 || r.bottom > 1081;}).map(e=>({tag:e.tagName,text:e.textContent.slice(0,70)}))''')
                check(not overflow,f'Slide {i+1} overflows: {overflow}')
            check(not [r for r in requests if r.startswith(('http://','https://'))],'Offline deck made a network request')
            for width,height in [(1366,768),(390,844),(844,390)]:
                page.set_viewport_size({'width':width,'height':height})
                rect=page.locator('#stage').bounding_box()
                check(abs(rect['x']+rect['width']/2-width/2)<1,'Stage not horizontally centered')
                check(abs(rect['y']+rect['height']/2-height/2)<1,'Stage not vertically centered')
            page.set_viewport_size({'width':1920,'height':1080})
            page.evaluate('window.__go(0)');page.keyboard.press('ArrowRight')
            check(page.evaluate('deckState().slide')==2,'Keyboard navigation')
            page.locator('#next').click()
            check(page.evaluate('deckState().slide')==3,'Control click navigated more than once')
            page.locator('#notes-button').click();check(page.locator('#notes').is_visible(),'Notes')
            page.locator('#overview-button').click();check(page.locator('#overview').is_visible(),'Overview')
            page.locator('[data-goto="5"]').click();check(page.evaluate('deckState().slide')==6,'Overview jump')
            page.locator('[data-case="2"]').click();check(page.locator('#score-value').inner_text()=='85','Manual scoring example')
            check(page.evaluate('deckState().slide')==6,'Case click advanced slide')
            # Themes and travelers survive navigation without changing the slide index.
            page.locator('#theme-button').click()
            check(page.evaluate('deckState().theme')=='dark','Dark theme toggle')
            page.reload();page.wait_for_function('window.deckState')
            check(page.evaluate('deckState().theme')=='dark','Theme persistence')
            page.locator('#theme-button').click()
            page.evaluate('window.__go(4)')
            check(page.evaluate('deckState().traveler')=='packet','Contextual traveler')
            page.locator('#traveler-button').click()
            check(page.evaluate('deckState().traveler')=='star','Traveler selection')
            page.evaluate('window.__go(7)')
            check(page.evaluate('deckState().traveler')=='star','Manual traveler override')
            # Long swipe followed by browser-generated click must move once.
            page.evaluate('window.__go(0)')
            page.dispatch_event('#viewport','pointerdown',{'pointerId':1,'isPrimary':True,'clientX':1200,'clientY':900})
            page.dispatch_event('#viewport','pointerup',{'pointerId':1,'isPrimary':True,'clientX':800,'clientY':900})
            page.dispatch_event('#viewport','click',{'clientX':800,'clientY':900})
            check(page.evaluate('deckState().slide')==2,'Swipe caused double navigation')
            # Navigation storm exercises cancellation of delayed hops and scoring frames.
            live=browser.new_page(viewport={'width':1920,'height':1080})
            live_errors=ready(live,export=False)
            for i in [5,0,11,7,5,8,11,0]:live.evaluate('(i)=>window.__go(i)',i)
            live.locator('#motion-button').click()
            state=live.evaluate('deckState()')
            check(state['timers']==state['frames']==state['effects']==0,'Pause left scheduled work')
            live.evaluate('window.__go(1)')
            check(live.locator('.slide.active h2').evaluate('(e)=>getComputedStyle(e).opacity')=='1','Paused navigation hid heading')
            live.emulate_media(reduced_motion='reduce')
            live.evaluate('window.__go(5)')
            state=live.evaluate('deckState()')
            check(state['timers']==state['frames']==state['effects']==0,'Reduced motion left scheduled work')
            live.wait_for_timeout(1000)
            check(not errors+live_errors,f'JavaScript errors: {errors+live_errors}')
            print('PASS: 12 slides, 3 viewport sizes, offline assets, navigation, overview, notes, scoring, themes, travelers, swipe, cancellation, reduced motion')
        finally:browser.close()

if __name__=='__main__':run()
