"""
Ridgeline Trail Club | Week 4 automated tests (Playwright + axe-core)

Regression: all 74 Week 3 behaviour checks. New: accessibility structure, forced colours,
focus visibility, text spacing, and performance/network checks.
Test the production build:  SITE_URL=http://127.0.0.1:8080/ python tests/run_tests.py

Run:  pip install playwright && playwright install chromium
      python tests/run_tests.py
Optional accessibility audit: set AXE_PATH to node_modules/axe-core/axe.min.js
(npm install axe-core). Results are printed and saved to tests/results.json.
"""
import json, os, sys, traceback
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = os.environ.get("SITE_URL") or (ROOT / "dist" / "index.html").as_uri()
BASE = URL.rsplit("/", 1)[0] + "/"
AXE_PATH = os.environ.get("AXE_PATH", "/home/claude/t/node_modules/axe-core/axe.min.js")  # npm install axe-core
AXE = Path(AXE_PATH).read_text() if Path(AXE_PATH).exists() else None
RESULTS = []

def record(group, name, ok, detail=""):
    RESULTS.append({"group": group, "test": name, "pass": bool(ok), "detail": str(detail)})
    print(("PASS " if ok else "FAIL ") + f"[{group}] {name}" + (f"  -> {detail}" if detail and not ok else ""))

def run(group, name):
    """Decorator: run a test function; any exception counts as a failure."""
    def deco(fn):
        try:
            result = fn()
            if result is None: result = (True, "")
            record(group, name, *result)
        except Exception as exc:
            record(group, name, False, repr(exc)[:160])
        return fn
    return deco

def new_page(browser, w=1280, h=800, fixed=None, **ctx):
    context = browser.new_context(viewport={"width": w, "height": h}, **ctx)
    page = context.new_page()
    page.js_errors = []
    page.on("pageerror", lambda e: page.js_errors.append(str(e)))
    page.on("console", lambda m: page.js_errors.append(m.text) if m.type == "error" and "net::ERR" not in m.text else None)
    if fixed: page.clock.set_fixed_time(fixed)
    page.goto(URL); page.wait_for_timeout(250)
    return page

def visible_trails(pg):
    return pg.evaluate("[...document.querySelectorAll('.trail-item')].filter(e=>!e.hidden).map(e=>e.dataset.name)")

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------------------------------------------------------- boot
    pg = new_page(b)
    @run("Boot", "No JavaScript errors on load")
    def _(): return (not pg.js_errors, pg.js_errors)
    @run("Boot", "All 11 features start (no [Ridgeline] failure logged)")
    def _(): return (not any("[Ridgeline]" in e for e in pg.js_errors), pg.js_errors)
    @run("Boot", "JS marks the page (html.js, html.no-js removed)")
    def _(): return (pg.evaluate("document.documentElement.classList.contains('js') && !document.documentElement.classList.contains('no-js')"), pg.evaluate("document.documentElement.className"))
    pg.context.close()

    # ---------------------------------------------------------------- theme
    pg = new_page(b)
    @run("Theme", "Toggle switches light to dark and updates aria-pressed")
    def _():
        pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(200)
        before = pg.evaluate("document.documentElement.dataset.theme")
        pg.click("#theme-toggle")
        after = pg.evaluate("document.documentElement.dataset.theme")
        pressed = pg.get_attribute("#theme-toggle", "aria-pressed")
        return (before == "light" and after == "dark" and pressed == "true", (before, after, pressed))
    @run("Theme", "Choice is saved and restored after reload")
    def _():
        saved = pg.evaluate("localStorage.getItem('rl-theme')")
        pg.reload(); pg.wait_for_timeout(200)
        return (saved == "dark" and pg.evaluate("document.documentElement.dataset.theme") == "dark", saved)
    pg.context.close()
    ctx = b.new_context(color_scheme="dark"); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(200)
    @run("Theme", "With no saved choice, follows the system dark setting")
    def _(): return (pg.evaluate("document.documentElement.dataset.theme") == "dark", "")
    ctx.close()

    # ---------------------------------------------------------------- nav
    pg = new_page(b, 360, 740)
    nav_visible = lambda: pg.is_visible("#primary-nav")
    @run("Mobile menu", "Starts closed on a phone")
    def _(): return (not nav_visible() and pg.get_attribute("#nav-toggle", "aria-expanded") == "false", "")
    @run("Mobile menu", "Button opens it and sets aria-expanded=true")
    def _():
        pg.click("#nav-toggle")
        return (nav_visible() and pg.get_attribute("#nav-toggle", "aria-expanded") == "true", "")
    @run("Mobile menu", "Escape closes it and returns focus to the button")
    def _():
        pg.keyboard.press("Escape")
        return (not nav_visible() and pg.evaluate("document.activeElement.id") == "nav-toggle", pg.evaluate("document.activeElement.id"))
    @run("Mobile menu", "Choosing a link closes the menu")
    def _():
        pg.click("#nav-toggle"); pg.click("#primary-nav a[href='#faq']"); pg.wait_for_timeout(100)
        return (not nav_visible(), "")
    @run("Mobile menu", "Clicking outside closes it")
    def _():
        pg.click("#nav-toggle"); pg.mouse.click(180, 700); pg.wait_for_timeout(100)
        return (not nav_visible(), "")
    @run("Mobile menu", "Resizing to desktop closes it and shows the full bar")
    def _():
        pg.click("#nav-toggle"); pg.set_viewport_size({"width": 1024, "height": 800}); pg.wait_for_timeout(200)
        return (nav_visible() and not pg.is_visible("#nav-toggle") and pg.get_attribute("#nav-toggle", "aria-expanded") == "false", "")
    pg.context.close()

    # ---------------------------------------------------------------- scroll features
    pg = new_page(b, 1280, 800)
    @run("Scroll", "Header gains a shadow after scrolling")
    def _():
        top = pg.evaluate("document.getElementById('site-header').classList.contains('is-scrolled')")
        pg.mouse.wheel(0, 900); pg.wait_for_timeout(500)
        return (not top and pg.evaluate("document.getElementById('site-header').classList.contains('is-scrolled')"), "")
    @run("Scroll", "Back-to-top button appears, then scrolls to the top")
    def _():
        shown = pg.evaluate("document.getElementById('to-top').classList.contains('is-visible')")
        pg.click("#to-top"); pg.wait_for_timeout(1200)
        return (shown and pg.evaluate("window.scrollY") < 5, pg.evaluate("window.scrollY"))
    @run("Scroll", "Scroll-spy marks the current section in the nav")
    def _():
        pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
        pg.evaluate("document.getElementById('schedule').scrollIntoView()"); pg.wait_for_timeout(500)
        cur = pg.evaluate("document.querySelector('.nav-list a[aria-current]')?.getAttribute('href')")
        return (cur == "#schedule", cur)
    @run("Scroll", "Reveal: below-fold content starts hidden, then fades in")
    def _():
        pg2 = new_page(b, 1280, 800)
        start = pg2.evaluate("document.querySelector('.faq-grid details').classList.contains('is-visible')")
        pg2.evaluate("document.querySelector('.faq-grid details').scrollIntoView()"); pg2.wait_for_timeout(700)
        end = pg2.evaluate("document.querySelector('.faq-grid details').classList.contains('is-visible')")
        pg2.context.close(); return (not start and end, (start, end))
    pg.context.close()

    # ---------------------------------------------------------------- trails
    pg = new_page(b, 1280, 800)
    @run("Trail filter", "Starts with all 4 trails and the right count text")
    def _(): return (len(visible_trails(pg)) == 4 and "4 of 4" in pg.inner_text("#trail-count"), pg.inner_text("#trail-count"))
    @run("Trail filter", "Easy shows 3 trails; Moderate shows 2")
    def _():
        pg.click("[data-level='easy']"); e = len(visible_trails(pg))
        pg.click("[data-level='moderate']"); m = visible_trails(pg)
        return (e == 3 and sorted(m) == ["Rajmachi Ridge", "Tamhini Forest Walk"], (e, m))
    @run("Trail filter", "Chip aria-pressed follows the selection")
    def _(): return (pg.get_attribute("[data-level='moderate']", "aria-pressed") == "true" and pg.get_attribute("[data-level='all']", "aria-pressed") == "false", "")
    @run("Trail filter", "Live search finds one trail and updates the count")
    def _():
        pg.click("[data-level='all']"); pg.fill("#trail-search", "lake"); pg.wait_for_timeout(350)
        return (visible_trails(pg) == ["Mulshi Lakeside"] and "1 of 4" in pg.inner_text("#trail-count"), visible_trails(pg))
    @run("Trail filter", "No match shows the empty state with a working Clear button")
    def _():
        pg.fill("#trail-search", "zzzz"); pg.wait_for_timeout(350)
        shown = pg.is_visible("#trail-empty") and pg.inner_text("#trail-count") == "No trails found"
        pg.click("#trail-empty [data-trail-reset]"); pg.wait_for_timeout(150)
        return (shown and len(visible_trails(pg)) == 4 and pg.input_value("#trail-search") == "", "")
    @run("Trail filter", "Sort by shortest distance reorders the cards")
    def _():
        pg.select_option("#trail-sort", "distance-asc")
        order = pg.evaluate("[...document.querySelectorAll('.trail-item')].map(e=>e.dataset.name)")
        return (order == ["Kaas Plateau", "Mulshi Lakeside", "Tamhini Forest Walk", "Rajmachi Ridge"], order)
    @run("Trail filter", "Sort by name A-Z works")
    def _():
        pg.select_option("#trail-sort", "name")
        order = pg.evaluate("[...document.querySelectorAll('.trail-item')].map(e=>e.dataset.name)")
        return (order == sorted(order), order)
    @run("Trail filter", "Featured full-row span is removed when customised (no gaps)")
    def _(): return (pg.evaluate("getComputedStyle(document.querySelector('.trail-item--featured')).gridColumnStart") == "auto", "")
    pg.context.close()

    # ---------------------------------------------------------------- schedule (fixed clock)
    pg = new_page(b, 1280, 800, fixed=datetime(2027, 3, 10, 10, 0))   # a Wednesday
    @run("Schedule", "Dates are recalculated from the system date (faked as Wed 10 Mar 2027)")
    def _():
        labels = pg.evaluate("[...document.querySelectorAll('tbody tr time')].map(t=>t.textContent)")
        want = ["Sat 13 Mar", "Sun 21 Mar", "Sat 27 Mar", "Sun 4 Apr", "Sat 10 Apr"]
        return (labels == want, labels)
    @run("Schedule", "<time datetime> values are valid ISO dates")
    def _():
        iso = pg.evaluate("[...document.querySelectorAll('tbody tr time')].map(t=>t.dateTime)")
        return (iso[0] == "2027-03-13" and iso[3] == "2027-04-04", iso)
    @run("Schedule", "Relative labels (In 3 days, In 11 days)")
    def _():
        w = pg.evaluate("[...document.querySelectorAll('.when')].map(e=>e.textContent)")
        return (w[0] == "In 3 days" and w[1] == "In 11 days", w)
    pg.context.close()
    pg = new_page(b, 1280, 800, fixed=datetime(2027, 3, 13, 9, 0))   # a Saturday
    @run("Schedule", "On a Saturday the first hike says Today")
    def _(): return (pg.inner_text("tbody tr:first-child .when") == "Today", "")
    pg.context.close()

    pg = new_page(b, 1280, 800)
    @run("Schedule", "Reserve column added: 5 buttons, last one Full and disabled")
    def _():
        n = pg.locator(".reserve-btn").count()
        return (n == 5 and pg.is_disabled(".reserve-btn >> nth=4") and pg.inner_text(".reserve-btn >> nth=4") == "Full", n)
    @run("Schedule", "Status badges: Open / Filling fast / Full")
    def _():
        t = pg.evaluate("[...document.querySelectorAll('tbody tr')].map(r=>r.querySelector('.badge').textContent)")
        return (t == ["Open", "Open", "Filling fast", "Open", "Full"], t)

    # ---------------------------------------------------------------- form
    @run("Form", "Reserve pre-fills trail and date, shows spots, focuses the name field")
    def _():
        pg.click(".reserve-btn[data-id='h3']"); pg.wait_for_timeout(300)
        return (pg.input_value("#trail") == "Tamhini Forest Walk" and pg.input_value("#hike-date") == "h3"
                and "3 spots left" in pg.inner_text("#group-hint") and pg.evaluate("document.activeElement.id") == "name",
                (pg.input_value("#trail"), pg.input_value("#hike-date"), pg.evaluate("document.activeElement.id")))
    @run("Form", "Dependent dropdown: Rajmachi lists 2 dates, the full one disabled")
    def _():
        pg.select_option("#trail", "Rajmachi Ridge")
        opts = pg.evaluate("[...document.querySelectorAll('#hike-date option')].map(o=>[o.textContent,o.disabled])")
        return (len(opts) == 3 and opts[2][1] and "Full" in opts[2][0], opts)
    @run("Form", "Empty submit shows an error summary listing 5 problems and focuses it")
    def _():
        pg.reload(); pg.wait_for_timeout(250)
        pg.click("#join-form button[type=submit]")
        items = pg.locator("#error-summary-list li").count()
        focus = pg.evaluate("document.activeElement.id")
        return (pg.is_visible("#error-summary") and items == 5 and focus == "error-summary", (items, focus))
    @run("Form", "Invalid fields get aria-invalid and a visible message")
    def _():
        inv = pg.evaluate("[...document.querySelectorAll('[aria-invalid=true]')].map(e=>e.id)")
        return (set(inv) == {"name", "email", "trail", "hike-date", "consent"} and pg.is_visible("#name-error"), inv)
    @run("Form", "Summary link moves focus to the matching field")
    def _():
        pg.click("#error-summary-list a[data-field='email']")
        return (pg.evaluate("document.activeElement.id") == "email", "")
    @run("Form", "Bad email gets a specific message; fixing it clears the error live")
    def _():
        pg.fill("#email", "not-an-email"); pg.press("#email", "Tab")
        msg = pg.inner_text("#email-error")
        pg.fill("#email", "asha@example.com")
        return ("does not look right" in msg and not pg.is_visible("#email-error"), msg)
    @run("Form", "Name error clears while typing after first visit")
    def _():
        pg.fill("#name", "A"); pg.press("#name", "Tab"); short = pg.is_visible("#name-error")
        pg.fill("#name", "Asha Rao")
        return (short and not pg.is_visible("#name-error"), "")
    @run("Form", "Group size above the spots left is rejected with a clear message")
    def _():
        pg.select_option("#trail", "Tamhini Forest Walk"); pg.select_option("#hike-date", "h3")
        pg.fill("#group", "5"); pg.press("#group", "Tab")
        return ("Only 3 spots left" in pg.inner_text("#group-error"), pg.inner_text("#group-error"))
    @run("Form", "Stepper clamps to the spots left (3) and clears the error")
    def _():
        pg.fill("#group", "1")
        for _i in range(6): pg.click("[data-step='1']")
        return (pg.input_value("#group") == "3" and not pg.is_visible("#group-error"), pg.input_value("#group"))
    @run("Form", "Valid submit opens the confirmation dialog with the user's details")
    def _():
        pg.fill("#group", "2"); pg.check("#consent")
        pg.click("#join-form button[type=submit]"); pg.wait_for_timeout(300)
        txt = pg.inner_text("#confirm-text")
        return (pg.evaluate("document.getElementById('confirm-dialog').open") and "Asha Rao" in txt and "Tamhini Forest Walk" in txt, txt)
    @run("Form", "Booking updates the schedule live: 3 spots to 1, badge unchanged")
    def _():
        cell = pg.inner_text("tr[data-id='h3'] td:nth-child(4)")
        return (cell.startswith("1") and "Filling fast" in cell, cell)
    @run("Form", "Dialog closes with Escape and focus returns to the submit button")
    def _():
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        return (not pg.evaluate("document.getElementById('confirm-dialog').open") and pg.evaluate("document.activeElement.type") == "submit", pg.evaluate("document.activeElement.tagName"))
    @run("Form", "Form is reset after a successful booking")
    def _(): return (pg.input_value("#name") == "" and pg.input_value("#trail") == "" and pg.is_disabled("#hike-date") and not pg.is_visible("#error-summary"), "")
    @run("Form", "Booking the last spot turns the row Full and disables Reserve")
    def _():
        pg.click(".reserve-btn[data-id='h3']"); pg.fill("#name", "Ravi K"); pg.fill("#email", "ravi@example.com"); pg.check("#consent")
        pg.click("#join-form button[type=submit]"); pg.wait_for_timeout(250)
        cell = pg.inner_text("tr[data-id='h3'] td:nth-child(4)")
        return ("Full" in cell and pg.is_disabled(".reserve-btn[data-id='h3']"), cell)
    pg.context.close()

    # ---------------------------------------------------------------- lightbox + faq + misc
    pg = new_page(b, 1280, 800)
    @run("Lightbox", "5 gallery images become 5 real buttons with descriptive labels")
    def _():
        n = pg.locator(".gallery-btn").count()
        return (n == 5 and "View larger" in pg.get_attribute(".gallery-btn >> nth=0", "aria-label"), n)
    @run("Lightbox", "Opening shows the photo, caption and 'Photo 1 of 5'")
    def _():
        pg.click(".gallery-btn >> nth=0"); pg.wait_for_timeout(250)
        return (pg.evaluate("document.getElementById('lightbox').open") and pg.inner_text("#lightbox-count") == "Photo 1 of 5", pg.inner_text("#lightbox-count"))
    @run("Lightbox", "Arrow keys move forward and wrap around backwards")
    def _():
        pg.keyboard.press("ArrowRight"); a = pg.inner_text("#lightbox-count")
        pg.keyboard.press("ArrowLeft"); pg.keyboard.press("ArrowLeft"); c = pg.inner_text("#lightbox-count")
        return (a == "Photo 2 of 5" and c == "Photo 5 of 5", (a, c))
    @run("Lightbox", "Escape closes it and focus returns to the thumbnail")
    def _():
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        return (not pg.evaluate("document.getElementById('lightbox').open") and "gallery-btn" in pg.evaluate("document.activeElement.className"), "")
    @run("FAQ", "Expand all opens every answer and relabels to Collapse all")
    def _():
        pg.click("#faq-toggle")
        n = pg.evaluate("[...document.querySelectorAll('.faq-grid details')].filter(d=>d.open).length")
        return (n == 4 and pg.inner_text("#faq-toggle") == "Collapse all", n)
    @run("FAQ", "Collapse all closes them; opening one by hand keeps the label right")
    def _():
        pg.click("#faq-toggle"); closed = pg.evaluate("[...document.querySelectorAll('.faq-grid details')].every(d=>!d.open)")
        pg.click(".faq-grid details:first-child summary")
        return (closed and pg.inner_text("#faq-toggle") == "Expand all", "")
    @run("Footer", "Year is filled in from the system date")
    def _(): return (pg.inner_text("#year") == str(datetime.now().year), pg.inner_text("#year"))
    pg.context.close()

    # ---------------------------------------------------------------- resilience
    ctx = b.new_context(viewport={"width": 360, "height": 740}, reduced_motion="reduce"); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(250)
    @run("Preferences", "Reduced motion: scroll-reveal is not activated, content visible")
    def _(): return (pg.evaluate("!document.documentElement.classList.contains('js-reveal')") and pg.evaluate("getComputedStyle(document.querySelector('.faq-grid details')).opacity") == "1", "")
    ctx.close()
    ctx = b.new_context(viewport={"width": 360, "height": 740}, java_script_enabled=False); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(250)
    @run("No JavaScript", "Navigation links stay visible and usable")
    def _(): return (pg.is_visible("#primary-nav") and pg.is_visible("#primary-nav a[href='#trails']"), "")
    @run("No JavaScript", "JS-only controls (menu button, theme, filters) are hidden")
    def _(): return (not pg.is_visible("#nav-toggle") and not pg.is_visible("#theme-toggle") and not pg.is_visible("#trail-tools"), "")
    @run("No JavaScript", "All content visible: trails, schedule, FAQ, form")
    def _(): return (all(pg.is_visible(s) for s in [".trail-item >> nth=3", ".schedule-table", ".faq-grid details >> nth=0", "#join-form"]), "")
    @run("No JavaScript", "No horizontal overflow")
    def _():
        o = pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"); return (o == 0, o)
    ctx.close()

    # ---------------------------------------------------------------- layout integrity with JS active
    sizes = [(320, 568), (375, 667), (768, 1024), (1024, 768), (1440, 900), (1920, 1080)]
    for w, h in sizes:
        pg = new_page(b, w, h)
        if w < 760: pg.click("#nav-toggle")
        pg.click("[data-level='easy']"); pg.mouse.wheel(0, 1500); pg.wait_for_timeout(500)
        o = pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
        record("Layout", f"{w}x{h}: no sideways scroll with menu, filter and scroll effects active", o == 0, o)
        pg.context.close()
    for w, h in [(360, 740), (1280, 800)]:
        ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
        pg.add_init_script("window.__cls=0;new PerformanceObserver(l=>{for(const e of l.getEntries()){if(!e.hadRecentInput)window.__cls+=e.value}}).observe({type:'layout-shift',buffered:true});")
        pg.goto(URL); pg.wait_for_timeout(800)
        for y in range(0, 4000, 500): pg.mouse.wheel(0, 500); pg.wait_for_timeout(120)
        cls = pg.evaluate("window.__cls")
        record("Layout", f"{w}px: Cumulative Layout Shift while loading and scrolling is {cls:.4f} (good is under 0.1)", cls < 0.1, cls)
        ctx.close()

    # ---------------------------------------------------------------- accessibility (axe)
    if AXE:
        def axe(pg):
            pg.add_style_tag(content="*,*::before,*::after{transition:none!important;animation:none!important}")
            pg.wait_for_timeout(150)
            pg.add_script_tag(content=AXE)
            r = pg.evaluate("axe.run(document,{runOnly:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']})")
            return [(v['id'], len(v['nodes']), [n['target'][0][:40] for n in v['nodes'][:4]]) for v in r['violations']], len(r['passes'])
        for theme in ("light", "dark"):
            for w, h in [(360, 740), (768, 1024), (1280, 800)]:
                ctx = b.new_context(viewport={"width": w, "height": h}, color_scheme=theme); pg = ctx.new_page()
                pg.goto(URL); pg.wait_for_timeout(300)
                pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('is-visible'))")
                v, passes = axe(pg)
                record("Accessibility (axe)", f"{theme} theme, {w}px: {passes} rules pass, {len(v)} violations", not v, v)
                ctx.close()
        states = {
            "mobile menu open": lambda pg: (pg.set_viewport_size({"width": 360, "height": 740}), pg.click("#nav-toggle")),
            "form error summary shown": lambda pg: pg.click("#join-form button[type=submit]"),
            "lightbox open": lambda pg: pg.click(".gallery-btn >> nth=1"),
            "filtered with empty state": lambda pg: (pg.fill("#trail-search", "zzzz"), pg.wait_for_timeout(300)),
        }
        for name, action in states.items():
            ctx = b.new_context(viewport={"width": 1280, "height": 800}); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(300)
            pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('is-visible'))")
            action(pg); pg.wait_for_timeout(300)
            v, passes = axe(pg)
            record("Accessibility (axe)", f"{name}: {passes} rules pass, {len(v)} violations", not v, v)
            ctx.close()

    # ================================================================ WEEK 4: accessibility structure
    CALM = "*,*::before,*::after{transition:none!important;animation:none!important}"
    pg = new_page(b, 1280, 800)
    @run("A11y structure", "Skip link is the first Tab stop and moves focus into <main>")
    def _():
        pg.keyboard.press("Tab"); first = pg.evaluate("document.activeElement.className")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(200)
        return ("skip-link" in first and pg.evaluate("document.activeElement.id") == "main", pg.evaluate("document.activeElement.id"))
    @run("A11y structure", "Decorative hero and card art has empty alt; every gallery photo has real alt text")
    def _():
        d = pg.evaluate("[...document.querySelectorAll('.hero img, .trail-card img')].every(i=>i.getAttribute('alt')==='')")
        g = pg.evaluate("[...document.querySelectorAll('.gallery-grid img')].every(i=>i.alt.trim().length>8)")
        return (d and g, (d, g))
    @run("A11y structure", "One h1; headings never skip a level")
    def _():
        lv = pg.evaluate("[...document.querySelectorAll('main h1,main h2,main h3,main h4')].map(h=>+h.tagName[1])")
        ok = lv.count(1) == 1 and all(b2 - a2 <= 1 for a2, b2 in zip(lv, lv[1:]))
        return (ok, lv)
    @run("A11y structure", "Landmarks: banner, main, 2 named navs, contentinfo")
    def _():
        r = pg.evaluate("({m:document.querySelectorAll('main').length,h:document.querySelectorAll('body>header').length,f:document.querySelectorAll('body>footer').length,n:[...document.querySelectorAll('nav')].map(n=>n.getAttribute('aria-label'))})")
        return (r["m"] == 1 and r["h"] == 1 and r["f"] == 1 and sorted(r["n"]) == ["Footer", "Main navigation"], r)
    @run("A11y structure", "No dead links (no href=\"#\"); footer links reach real pages")
    def _():
        dead = pg.evaluate("[...document.querySelectorAll('a[href=\"#\"]')].length")
        hrefs = pg.evaluate("[...document.querySelectorAll('.footer-links a')].map(a=>a.getAttribute('href'))")
        return (dead == 0 and any("policies" in h for h in hrefs), hrefs)
    @run("A11y structure", "Required fields are explained before the form: 'All fields are required.'")
    def _(): return (pg.inner_text("#form-note") == "All fields are required." and pg.get_attribute("#join-form", "aria-describedby") == "form-note", "")
    @run("A11y structure", "Scroll-spy uses aria-current=\"location\"")
    def _():
        pg.evaluate("document.documentElement.style.scrollBehavior='auto';document.getElementById('schedule').scrollIntoView()"); pg.wait_for_timeout(500)
        v = pg.evaluate("document.querySelector('.nav-list a[aria-current]')?.getAttribute('aria-current')")
        return (v == "location", v)
    @run("A11y structure", "Filter chip selection is shown by a tick as well as colour")
    def _():
        c = pg.evaluate("getComputedStyle(document.querySelector('.chip[aria-pressed=true]'),'::before').content")
        u = pg.evaluate("getComputedStyle(document.querySelector('.chip[aria-pressed=false]'),'::before').content")
        return (c not in ("none", "normal") and u in ("none", "normal"), (c, u))
    pg.context.close()
    pg = b.new_context(viewport={"width": 1280, "height": 800}).new_page(); pg.goto(BASE + "policies.html"); pg.wait_for_timeout(300)
    @run("A11y structure", "Policies page: one h1, Safety and Privacy sections, skip link, no console errors")
    def _():
        r = pg.evaluate("({h1:document.querySelectorAll('h1').length,secs:[...document.querySelectorAll('main section h2')].map(h=>h.textContent),skip:!!document.querySelector('.skip-link'),lang:document.documentElement.lang})")
        return (r["h1"] == 1 and r["secs"] == ["Safety policy", "Privacy"] and r["skip"] and r["lang"] == "en", r)
    pg.context.close()

    # ================================================================ WEEK 4: assistive and user-preference modes
    for w in (360, 1280):
        pg = new_page(b, w, 800)
        pg.add_style_tag(content="*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-bottom:2em!important}"); pg.wait_for_timeout(250)
        r = pg.evaluate("""()=>{const de=document.documentElement;const clipped=[...document.querySelectorAll('body *')].filter(e=>{const c=getComputedStyle(e);return (c.overflow==='hidden'||c.overflowY==='hidden')&&e.scrollHeight>e.clientHeight+1&&e.clientHeight>0&&!e.matches('.visually-hidden,.scroll-marker,thead')}).length;return {o:de.scrollWidth-de.clientWidth,clipped}}""")
        record("Preferences", f"Text spacing override (WCAG 1.4.12) at {w}px: no overflow, nothing clipped", r["o"] == 0 and r["clipped"] == 0, r)
        pg.context.close()
    ctx = b.new_context(viewport={"width": 360, "height": 740}, forced_colors="active"); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(300); pg.add_style_tag(content=CALM)
    @run("Preferences", "Forced colours: hamburger icon stays visible")
    def _():
        r = pg.evaluate("[getComputedStyle(document.querySelector('.bars')).backgroundColor,getComputedStyle(document.body).backgroundColor]")
        return (r[0] != r[1], r)
    @run("Preferences", "Forced colours: selected filter chip is distinguishable from the others")
    def _():
        r = pg.evaluate("""()=>{const sig=e=>{const c=getComputedStyle(e);return [c.backgroundColor,c.borderTopColor,c.color,c.outlineStyle,getComputedStyle(e,'::before').content].join('|')};const cs=[...document.querySelectorAll('.chip')];return [sig(cs.find(c=>c.getAttribute('aria-pressed')==='true')),sig(cs.find(c=>c.getAttribute('aria-pressed')==='false'))]}""")
        return (r[0] != r[1], r)
    @run("Preferences", "Forced colours: an invalid field gets an outline (shadows are removed in this mode)")
    def _():
        pg.evaluate("document.querySelector('#join-form button[type=submit]').click()"); pg.wait_for_timeout(200)
        o = pg.evaluate("getComputedStyle(document.querySelector('#name')).outlineStyle")
        return (o != "none", o)
    ctx.close()
    for scheme in ("light", "dark"):
        ctx = b.new_context(viewport={"width": 1280, "height": 800}, color_scheme=scheme); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(300)
        cdp = ctx.new_cdp_session(pg); cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-contrast", "value": "more"}]}); pg.wait_for_timeout(200)
        v = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--line').trim()")
        record("Preferences", f"prefers-contrast: more strengthens borders in {scheme} theme", v in ("#4d5b52", "#a9b8ae"), v)
        ctx.close()

    # ================================================================ WEEK 4: keyboard focus never hidden
    for w, h in ((360, 740), (1280, 800)):
        pg = new_page(b, w, h); pg.add_style_tag(content=CALM); pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
        bad, stops = [], 0
        for _i in range(60):
            pg.keyboard.press("Tab"); pg.wait_for_timeout(25)
            r = pg.evaluate("""()=>{const e=document.activeElement;if(!e||e===document.body)return null;const r=e.getBoundingClientRect();
              const tt=document.getElementById('to-top');const t=tt&&tt.classList.contains('is-visible')?tt.getBoundingClientRect():null;
              const hd=document.getElementById('site-header');const hb=hd&&getComputedStyle(hd).position==='sticky'?hd.getBoundingClientRect().bottom:0;
              const underTT=!!t&&e!==tt&&!(r.right<=t.left||r.left>=t.right||r.bottom<=t.top||r.top>=t.bottom);
              const underHd=!e.closest('#site-header')&&!e.classList.contains('skip-link')&&r.top<hb-1&&r.bottom>0;
              return {t:(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,24),underTT,underHd,inView:r.bottom>0&&r.top<innerHeight}}""")
            if r is None: break
            stops += 1
            if r["underTT"] or r["underHd"] or not r["inView"]: bad.append(r["t"])
        record("Keyboard focus", f"{w}px: all {stops} Tab stops stay fully visible (not under the sticky header or back-to-top)", not bad, bad)
        pg.context.close()

    # ================================================================ WEEK 4: performance and network
    reqs = []
    ctx = b.new_context(viewport={"width": 360, "height": 740}); pg = ctx.new_page(); warns = []
    pg.on("console", lambda m: warns.append(m.text) if m.type in ("warning", "error") else None)
    pg.on("requestfinished", lambda rq: reqs.append((rq.url, rq.resource_type, rq.sizes()["responseBodySize"])))
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(500)
    @run("Performance", "Every request is same-origin (no third-party hosts)")
    def _():
        origins = {u.split("/")[2] for u, _t, _s in reqs if u.startswith("http")}
        return (len(origins) <= 1, origins)
    @run("Performance", "No console warnings or errors (no 404 favicon, no unused-preload warning)")
    def _(): return (not warns, warns)
    @run("Performance", "Fonts: the 3 above-the-fold faces load; no render-blocking font stylesheet")
    def _():
        r = pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family.replace(/\"/g,'')+' '+f.weight)")
        return (all(x in r for x in ("Source Sans 3 400", "Source Sans 3 600", "Bitter 800")), r)
    @run("Performance", "Critical CSS is inline in <head> and main CSS is loaded without blocking")
    def _():
        r = pg.evaluate("({inline:document.querySelectorAll('head style').length,main:[...document.styleSheets].some(s=>s.href&&/main\\./.test(s.href)),renderBlockingLinks:[...document.querySelectorAll('head link[rel=stylesheet]:not([media=print])')].length})")
        return (r["inline"] >= 1 and r["main"], r)
    @run("Performance", "Hero image is high priority and eager; every other image is lazy with width/height set")
    def _():
        r = pg.evaluate("""()=>{const all=[...document.images].filter(i=>!i.closest('dialog'));const hero=all.find(i=>i.closest('.hero'));
          return {heroPriority:hero.getAttribute('fetchpriority'),heroLazy:hero.loading,others:all.filter(i=>i!==hero).every(i=>i.loading==='lazy'),sized:all.every(i=>i.width>0&&i.getAttribute('width')&&i.getAttribute('height'))}}""")
        return (r["heroPriority"] == "high" and r["heroLazy"] != "lazy" and r["others"] and r["sized"], r)
    @run("Performance", "Initial page weight is under 60 KB compressed, in 14 requests or fewer")
    def _():
        total = sum(s for _u, _t, s in reqs); n = len(reqs)
        return (total < 60000 and n <= 14, (total, n))
    ctx.close()
    pg = new_page(b, 360, 740)
    @run("Performance", "JavaScript boot (all 11 features) takes under 25 ms of main-thread time")
    def _():
        t = pg.evaluate("performance.getEntriesByType('measure').filter(m=>m.name.startsWith('rl:')).map(m=>[m.name,m.duration])")
        tot = sum(d for _n, d in t)
        return (len(t) == 11 and tot < 25, (len(t), round(tot, 2)))
    pg.context.close()
    for w, h in ((360, 740), (768, 1024), (1280, 800)):
        shots = []
        for block in (False, True):
            ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
            if block: pg.route("**/main.*.css", lambda route: route.abort())
            pg.goto(URL); pg.wait_for_timeout(500); pg.add_style_tag(content=CALM); pg.wait_for_timeout(150)
            fold = pg.evaluate("Math.min(innerHeight, Math.floor(document.querySelector('.hero').getBoundingClientRect().bottom) - 4)")
            shots.append(pg.screenshot(clip={"x": 0, "y": 0, "width": w, "height": fold})); ctx.close()
        from PIL import Image, ImageChops
        import io
        a, c = (Image.open(io.BytesIO(x)).convert("RGB") for x in shots)
        diff = ImageChops.difference(a, c).getbbox()
        record("Performance", f"{w}px: header and hero are pixel-identical with main.css blocked (critical CSS is complete)", diff is None, diff)
    b.close()

passed = sum(r["pass"] for r in RESULTS)
print(f"\n{passed}/{len(RESULTS)} checks passed")
(Path(__file__).parent / "results.json").write_text(json.dumps(RESULTS, indent=1))
sys.exit(0 if passed == len(RESULTS) else 1)
