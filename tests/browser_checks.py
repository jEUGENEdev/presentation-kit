"""Browser regression checks. Run from any directory: python tests/browser_checks.py."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from scripts.browser import launch,ready,ROOT

def check(condition,message):
    if not condition:raise AssertionError(message)

def setting(page, selector, value=None):
    if not page.locator('#settings').is_visible():page.locator('#settings-button').click()
    if value is None:page.locator(selector).click()
    else:page.locator(selector).select_option(value)
    if page.locator('#settings').is_visible():page.locator('#settings-close').click()

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
            setting(page,'#notes-button');check(page.locator('#notes').is_visible(),'Notes')
            page.locator('#overview-button').click();check(page.locator('#overview').is_visible(),'Overview')
            page.locator('[data-goto="5"]').click();check(page.evaluate('deckState().slide')==6,'Overview jump')
            page.locator('[data-case="2"]').click();check(page.locator('#score-value').inner_text()=='85','Manual scoring example')
            check(page.evaluate('deckState().slide')==6,'Case click advanced slide')
            # Themes and travelers survive navigation without changing the slide index.
            setting(page,'#theme-button')
            check(page.evaluate('deckState().theme')=='dark','Dark theme toggle')
            page.reload();page.wait_for_function('window.deckState')
            check(page.evaluate('deckState().theme')=='dark','Theme persistence')
            setting(page,'#theme-button')
            page.evaluate('window.__go(4)')
            check(page.evaluate('deckState().traveler')=='packet','Contextual traveler')
            setting(page,'#traveler-select','star')
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
            setting(live,'#motion-button')
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
            # Real touch emulation with OS reduced motion: manual enable must revive CSS and JS.
            mobile_context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2,reduced_motion='reduce')
            mobile=mobile_context.new_page();mobile_errors=ready(mobile,export=False)
            check(mobile.locator('#motion-notice').is_visible(),'Missing motion explanation')
            check(mobile.evaluate('deckState().timers')==0,'System reduced motion ignored')
            for selector in ['#prev','#next','#overview-button','#settings-button']:
                box=mobile.locator(selector).bounding_box()
                check(box['height']>=44 and box['x']>=0 and box['x']+box['width']<=390,'Mobile control clipped or too small')
            mobile.locator('#enable-motion').tap()
            check(mobile.evaluate('deckState().motionEnabled && deckState().forceMotion'),'Manual enable blocked by OS preference')
            check(mobile.locator('.hero-star').evaluate('(e)=>getComputedStyle(e).animationName')!='none','CSS animations still blocked')
            mobile.locator('#hopper').wait_for(state='visible',timeout=4000)
            first=mobile.locator('#hopper').evaluate('(e)=>getComputedStyle(e).transform')
            mobile.wait_for_timeout(150)
            second=mobile.locator('#hopper').evaluate('(e)=>getComputedStyle(e).transform')
            check(first!=second,'Traveler is visible but not moving')
            mobile.reload();mobile.wait_for_function('window.deckState')
            check(mobile.evaluate('deckState().motionEnabled'),'Motion choice did not persist')
            mobile.locator('#settings-button').tap()
            check(mobile.locator('#motion-button').inner_text()=='Выключить анимации','Incorrect action label')
            folder=ROOT/'build/mobile-ui';folder.mkdir(parents=True,exist_ok=True)
            mobile.screenshot(path=str(folder/'settings.png'))
            import base64
            print('MOBILE_REVIEW:'+base64.b64encode((folder/'settings.png').read_bytes()).decode('ascii'))
            mobile.locator('#motion-button').tap()
            state=mobile.evaluate('deckState()')
            check(not state['motionEnabled'] and state['timers']==state['frames']==state['effects']==0,'Mobile stop did not cancel work')
            mobile.locator('#settings-close').tap();mobile.locator('#next').tap()
            check(mobile.evaluate('deckState().slide')==2,'Mobile labeled next action')
            mobile.goto((ROOT/'dist/index.html').as_uri()+'?export=1&motion=on')
            mobile.wait_for_function('window.deckState')
            check(mobile.evaluate('deckState().timers===0 && deckState().frames===0'),'Export animated despite static contract')
            check(not mobile_errors,f'Mobile JavaScript errors: {mobile_errors}')
            mobile_context.close()
            print('PASS: 12 slides, 3 viewport sizes, offline assets, navigation, overview, notes, scoring, themes, travelers, swipe, cancellation, reduced motion, touch animation opt-in, labeled controls')
        finally:browser.close()

if __name__=='__main__':run()
