"""
AI-facing browser tools for the VIKO embedded browser.

navigate_browser  — open URL in embedded browser
render_content    — save HTML to workspace + open in browser
take_screenshot   — widget-grab screenshot of current page
get_page_content  — return page text for AI to read
"""
from __future__ import annotations
import base64


def navigate_browser(parameters: dict, player=None) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        return "Error: url is required."
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url
    if player and hasattr(player, "set_browser_url"):
        player.toggle_browser(visible=True)   # show panel first
        player.set_browser_url(url)            # then navigate
        return f"Opened in browser: {url}"
    return f"Browser tidak tersedia. URL: {url}"


def render_content(parameters: dict, player=None) -> str:
    content  = parameters.get("content", "")
    filename = parameters.get("filename", "output.html")
    category = parameters.get("category", "documents")
    if not content:
        return "Error: content is required."
    if not filename.endswith(".html"):
        filename += ".html"
    from viko.core.workspace import save_file, file_url
    path = save_file(content, filename, category)
    url  = file_url(path)
    if player and hasattr(player, "set_browser_url"):
        player.toggle_browser(visible=True)
        player.set_browser_url(url)
    return f"Rendered: {path.name} ({category}) → {url}"


def take_screenshot(parameters: dict, player=None) -> str:
    if not player or not hasattr(player, "take_screenshot"):
        return "Browser tidak tersedia."
    data = player.take_screenshot()
    if not data:
        return "Screenshot gagal atau timeout."
    b64 = base64.b64encode(data).decode()
    return (
        f"Screenshot diambil. Disimpan di workspace/documents/screenshot_latest.png. "
        f"Base64 length: {len(b64)} chars."
    )


def get_page_content(parameters: dict, player=None) -> str:
    if not player or not hasattr(player, "get_page_content"):
        return "Browser tidak tersedia."
    text = player.get_page_content()
    if not text:
        return "(halaman kosong atau timeout)"
    return text[:8000]


def browser_interact(parameters: dict, player=None) -> str:
    """Control the VIKO embedded browser via JavaScript injection."""
    if not player or not hasattr(player, "run_js"):
        return "Browser tidak tersedia."

    action    = parameters.get("action", "").strip()
    selector  = parameters.get("selector", "")
    text      = parameters.get("text", "")
    label     = parameters.get("label", "")
    value     = parameters.get("value", "")
    code      = parameters.get("code", "")
    direction = parameters.get("direction", "down")
    amount    = int(parameters.get("amount", 400))

    def js(script: str):
        return player.run_js(script)

    # ── JS helpers ────────────────────────────────────────────────────────
    _FIND_INPUT = """
    function findInput(needle) {
        needle = needle.toLowerCase();
        for (const el of document.querySelectorAll('input,textarea')) {
            if (el.placeholder && el.placeholder.toLowerCase().includes(needle)) return el;
        }
        for (const lbl of document.querySelectorAll('label')) {
            if (lbl.textContent.toLowerCase().includes(needle)) {
                const tgt = lbl.htmlFor ? document.getElementById(lbl.htmlFor)
                          : lbl.querySelector('input,textarea');
                if (tgt) return tgt;
            }
        }
        for (const el of document.querySelectorAll('input,textarea')) {
            const attrs = [el.getAttribute('aria-label'), el.name, el.id];
            if (attrs.some(a => a && a.toLowerCase().includes(needle))) return el;
        }
        for (const span of document.querySelectorAll('span,div,p,h1,h2,h3,h4')) {
            if (span.textContent.trim().toLowerCase() === needle) {
                const inp = span.closest('[class]')?.querySelector('input,textarea');
                if (inp) return inp;
            }
        }
        return null;
    }
    """

    _REACT_TYPE = """
    function reactType(el, val) {
        el.focus();
        const desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
                  || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
        if (desc && desc.set) desc.set.call(el, val);
        else el.value = val;
        ['input','change','keydown','keyup'].forEach(ev =>
            el.dispatchEvent(new Event(ev, {bubbles:true, cancelable:true}))
        );
        el.dispatchEvent(new KeyboardEvent('keypress', {bubbles:true}));
    }
    """

    # Smart scroll: find the innermost visible scrollable container (modal etc.)
    _SMART_SCROLL = """
    function smartScroll(dy, targetSel) {
        if (targetSel) {
            const t = document.querySelector(targetSel);
            if (t) { t.scrollBy(0, dy); return 'scrolled: ' + targetSel; }
        }
        // Collect visible scrollable elements (modal panels, overflow divs, etc.)
        const scrollables = Array.from(document.querySelectorAll('*')).filter(el => {
            if (el === document.body || el === document.documentElement) return false;
            const s = window.getComputedStyle(el);
            const ov = s.overflow + ' ' + s.overflowY;
            return (ov.includes('scroll') || ov.includes('auto'))
                && el.scrollHeight > el.clientHeight + 2
                && el.getBoundingClientRect().height > 0;
        });
        if (scrollables.length > 0) {
            // Prefer the smallest (innermost) scrollable that is taller than 100px
            const best = scrollables
                .filter(el => el.getBoundingClientRect().height > 100)
                .sort((a,b) => a.scrollHeight - b.scrollHeight)[0]
                || scrollables[scrollables.length - 1];
            best.scrollBy(0, dy);
            return 'scrolled container: ' + (best.id || best.className.slice(0,40) || best.tagName);
        }
        window.scrollBy(0, dy);
        return 'scrolled window';
    }
    """

    # Find any clickable element — broad search including icons, aria, SVG buttons
    _FIND_CLICK = """
    function findClickable(needle) {
        needle = needle.toLowerCase();
        const SELECTORS = [
            'button', 'a', 'input[type=submit]', 'input[type=button]',
            'input[type=reset]', '[role=button]', '[role=link]', '[role=menuitem]',
            '[class*=btn]', '[class*=button]', '[class*=search]', '[class*=submit]',
            '[tabindex]', 'label', '[onclick]'
        ];
        for (const sel of SELECTORS) {
            for (const el of document.querySelectorAll(sel)) {
                const texts = [
                    el.innerText, el.value, el.title,
                    el.getAttribute('aria-label'),
                    el.getAttribute('data-label'),
                    el.getAttribute('name'),
                    el.getAttribute('placeholder'),
                    el.getAttribute('alt'),
                ].filter(Boolean).join(' ').toLowerCase();
                if (texts.includes(needle)) return el;
            }
        }
        // SVG-icon buttons (e.g. magnifying glass for search)
        const ICON_MAP = {
            search: '[type=submit], [class*=search-btn], [class*=searchbtn], form button',
            cari:   '[type=submit], [class*=search-btn], form button',
            submit: '[type=submit], form button:last-child',
            close:  '[class*=close], [aria-label*=close i], [data-dismiss]',
            ok:     '[class*=ok], [class*=confirm], [type=submit]',
        };
        for (const [kw, fallback] of Object.entries(ICON_MAP)) {
            if (needle.includes(kw)) {
                const el = document.querySelector(fallback);
                if (el) return el;
            }
        }
        // Last resort: walk text nodes
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            if (node.textContent.trim().toLowerCase().includes(needle)) {
                let el = node.parentElement;
                while (el && el !== document.body) {
                    if (['BUTTON','A','INPUT','LABEL'].includes(el.tagName)
                        || el.getAttribute('role') === 'button'
                        || el.onclick) {
                        return el;
                    }
                    el = el.parentElement;
                }
                if (node.parentElement?.offsetParent !== null)
                    return node.parentElement;
            }
        }
        return null;
    }
    """

    # ── Actions ───────────────────────────────────────────────────────────
    if action == "get_inputs":
        result = js("""
            (function() {
                const rows = [];
                document.querySelectorAll('input,textarea,select').forEach((el, i) => {
                    if (i >= 25) return;
                    const lbl = el.id
                        ? (document.querySelector('label[for="' + el.id + '"]') || {}).textContent
                        : '';
                    rows.push([
                        (el.tagName + (el.type ? '[' + el.type + ']' : '')).toLowerCase(),
                        'id=' + (el.id || '-'),
                        'name=' + (el.name || '-'),
                        'placeholder=' + (el.placeholder || '-'),
                        'label=' + (lbl ? lbl.trim() : '-'),
                        'value=' + (el.value || '-')
                    ].join('  '));
                });
                return rows.join('\n') || '(no inputs found)';
            })()
        """)
        return f"Form inputs on page:\n{result}"

    elif action == "click":
        if selector:
            result = js(f"""
                (function() {{
                    const el = document.querySelector({_qs(selector)});
                    if (!el) return 'Not found: {selector}';
                    el.scrollIntoView({{block:'center'}});
                    el.click(); return 'clicked';
                }})()
            """)
        elif text:
            result = js(f"""
                (function() {{
                    {_FIND_CLICK}
                    const el = findClickable({_qs(text.lower())});
                    if (!el) return 'Not found: {text}';
                    el.scrollIntoView({{block:'center'}});
                    el.click();
                    return 'clicked: ' + (el.innerText || el.value || el.getAttribute('aria-label') || el.tagName).slice(0,60);
                }})()
            """)
        else:
            return "Error: provide selector or text for click."
        return f"Click: {result}"

    elif action == "type":
        fill_val = value or text
        if selector:
            result = js(f"""
                (function() {{
                    {_REACT_TYPE}
                    const el = document.querySelector({_qs(selector)});
                    if (!el) return 'Not found: {selector}';
                    reactType(el, {_qs(fill_val)});
                    return 'typed into ' + (el.id || el.name || el.placeholder || 'input');
                }})()
            """)
        elif label:
            result = js(f"""
                (function() {{
                    {_FIND_INPUT}
                    {_REACT_TYPE}
                    const el = findInput({_qs(label)});
                    if (!el) return 'Input not found for label: {label}';
                    reactType(el, {_qs(fill_val)});
                    return 'typed into ' + (el.placeholder || el.name || el.id || 'input');
                }})()
            """)
        else:
            return "Error: provide selector or label for type."
        return f"Type: {result}"

    elif action == "clear":
        target = selector or ""
        lbl    = label or ""
        result = js(f"""
            (function() {{
                {_FIND_INPUT}
                {_REACT_TYPE}
                const el = {('document.querySelector(' + _qs(target) + ')') if target else ('findInput(' + _qs(lbl) + ')')};
                if (!el) return 'Not found';
                reactType(el, '');
                return 'cleared';
            }})()
        """)
        return f"Clear: {result}"

    elif action == "scroll":
        dy = amount if direction == "down" else -amount
        target_sel = selector or ""
        result = js(f"""
            (function() {{
                {_SMART_SCROLL}
                return smartScroll({dy}, {_qs(target_sel)});
            }})()
        """)
        return f"Scroll: {result}"

    elif action == "scroll_to":
        result = js(f"""
            (function() {{
                {_FIND_INPUT}
                const el = {('document.querySelector(' + _qs(selector) + ')') if selector else ('findInput(' + _qs(label or text) + ')')};
                if (!el) return 'not found';
                el.scrollIntoView({{behavior:'smooth', block:'center'}});
                return 'ok';
            }})()
        """)
        return f"Scroll to: {result}"

    elif action == "get_text":
        target = selector or "body"
        result = js(f"""
            (function() {{
                const el = document.querySelector({_qs(target)});
                return el ? el.innerText : null;
            }})()
        """)
        out = str(result or "")
        return out[:6000] if out else "(empty)"

    elif action == "get_links":
        result = js("""
            Array.from(document.querySelectorAll('a[href]')).slice(0,50)
                 .map(a => a.href + ' | ' + a.innerText.trim()).join('\\n')
        """)
        return str(result or "(no links)")

    elif action == "submit":
        result = js(f"""
            (function() {{
                const el = document.querySelector({_qs(selector or 'form')});
                if (!el) return 'not found';
                if (typeof el.submit === 'function') el.submit();
                else el.click();
                return 'submitted';
            }})()
        """)
        return f"Submit: {result}"

    elif action == "run_js":
        result = js(code)
        return f"JS result: {result}"

    else:
        return (
            f"Unknown action: '{action}'. "
            "Available: get_inputs, click, type, clear, scroll, scroll_to, "
            "get_text, get_links, submit, run_js"
        )


def visual_control(parameters: dict, player=None) -> str:
    """
    Coordinate-based browser control via agent-browser CDP.
    Falls back to browser_interact when agent-browser is unavailable.

    Actions: click_xy, scroll_xy, type_text, key, screenshot
    """
    from viko.ui.agent_browser import get_server

    action = parameters.get("action", "").strip()
    server = get_server()

    if not server.is_running():
        # Non-blocking start; tell caller to try again shortly
        server.auto_start_in_background()
        return (
            "agent-browser sedang starting (background). "
            "Coba lagi dalam ~5 detik, atau gunakan browser_interact untuk interaksi berbasis JS."
        )

    try:
        if action == "screenshot":
            data = server.get_screenshot()
            import base64
            b64 = base64.b64encode(data).decode()
            return f"Screenshot CDP diambil. Base64 length: {len(b64)} chars."

        elif action == "click_xy":
            x = int(parameters.get("x", 0))
            y = int(parameters.get("y", 0))
            result = server.send_action({"type": "click", "x": x, "y": y})
            return f"Click di ({x}, {y}): {result}"

        elif action == "scroll_xy":
            x  = int(parameters.get("x", 0))
            y  = int(parameters.get("y", 0))
            dx = int(parameters.get("deltaX", 0))
            dy = int(parameters.get("deltaY", 400))
            result = server.send_action({"type": "scroll", "x": x, "y": y,
                                         "deltaX": dx, "deltaY": dy})
            return f"Scroll di ({x},{y}) delta=({dx},{dy}): {result}"

        elif action == "type_text":
            text = parameters.get("text", "")
            result = server.send_action({"type": "type", "text": text})
            return f"Type '{text[:40]}': {result}"

        elif action == "key":
            key = parameters.get("key", "Enter")
            result = server.send_action({"type": "key", "key": key})
            return f"Key '{key}': {result}"

        elif action == "navigate":
            url = parameters.get("url", "")
            result = server.send_action({"type": "navigate", "url": url})
            return f"Navigate → {url}: {result}"

        else:
            return (
                f"Unknown action: '{action}'. "
                "Available: screenshot, click_xy, scroll_xy, type_text, key, navigate"
            )
    except Exception as exc:
        return f"visual_control error: {exc}"


def _qs(s: str) -> str:
    import json
    return json.dumps(str(s))
