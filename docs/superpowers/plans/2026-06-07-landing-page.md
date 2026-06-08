# VIKO Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a static GitHub Pages landing page for VIKO that matches the approved design mockup, split across three clean files.

**Architecture:** Port the approved single-file mockup at `.superpowers/brainstorm/216-1780835240/content/full-design-v2.html` into three files: `index.html` (HTML structure), `assets/landing/style.css` (all styles), `assets/landing/main.js` (HUD animation + scroll reveal). No build tools, no dependencies.

**Tech Stack:** Pure HTML5, CSS3 (custom properties, grid, flexbox, animations), vanilla JS (SVG rendering, IntersectionObserver, setInterval)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `index.html` | Create | HTML structure, links to CSS/JS |
| `assets/landing/style.css` | Create | All styles, CSS variables, responsive |
| `assets/landing/main.js` | Create | HUD circle animation, scroll reveal |
| `assets/icon.png` | Existing | Logo — used in header + footer |
| `docs/screenshots/dashboard.png` | Existing | Hero BG + screenshot section |
| `docs/screenshots/text-chat.png` | Existing | Screenshot section |
| `docs/screenshots/voice-chat.png` | Existing | Screenshot section |

> **Image path note:** The mockup uses `./dashboard.png` (served from brainstorm dir). In `index.html` at repo root, use `docs/screenshots/dashboard.png` and `assets/icon.png`.

---

## Task 1: Scaffold — HTML boilerplate + file structure

**Files:**
- Create: `index.html`
- Create: `assets/landing/style.css`
- Create: `assets/landing/main.js`

- [x] **Step 1: Create `assets/landing/style.css`** with empty placeholder

```css
/* VIKO Landing Page — styles */
```

- [x] **Step 2: Create `assets/landing/main.js`** with empty placeholder

```js
// VIKO Landing Page — main.js
```

- [x] **Step 3: Create `index.html`** with full boilerplate

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="VIKO — Personal AI voice assistant powered by Gemini Live API. Futuristic HUD, speaker verification, self-modification, long-term memory.">
  <title>VIKO — Personal AI Voice Assistant</title>
  <link rel="icon" href="assets/icon.png" type="image/png">
  <link rel="stylesheet" href="assets/landing/style.css">
</head>
<body>

  <!-- HEADER -->
  <!-- HERO -->
  <!-- WHY VIKO -->
  <!-- FEATURES -->
  <!-- SCREENSHOTS -->
  <!-- GITHUB CTA -->
  <!-- FOOTER -->

  <script src="assets/landing/main.js"></script>
</body>
</html>
```

- [x] **Step 4: Verify — open in browser**

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

Expected: blank black page, no 404 errors in console for CSS/JS.

- [x] **Step 5: Commit**

```bash
git add index.html assets/landing/style.css assets/landing/main.js
git commit -m "feat: scaffold landing page file structure"
```

---

## Task 2: CSS — Variables, reset, base styles, utilities

**Files:**
- Modify: `assets/landing/style.css`

- [x] **Step 1: Write base styles into `assets/landing/style.css`**

```css
/* VIKO Landing Page — styles */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --black:  #000000;
  --card:   #04080E;
  --txt:    #F2F9FF;
  --body:   #D4E8F5;
  --dim:    #5A91B9;
  --pri:    #00D4FF;
  --amb:    #FFB347;
  --suc:    #00FF9F;
  --border: #0d1f2d;
}

html { scroll-behavior: smooth; }

body {
  background: var(--black);
  color: var(--txt);
  font-family: 'Courier New', Courier, monospace;
  font-size: 17px;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}

/* ── Scroll reveal ── */
.reveal {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s ease, transform 0.7s ease;
}
.reveal.visible { opacity: 1; transform: none; }

/* ── Utilities ── */
.label {
  font-size: 11px;
  color: var(--pri);
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.sep { width: 48px; height: 2px; background: var(--pri); margin-bottom: 20px; }
.section-title {
  font-size: 32px; font-weight: bold; color: var(--txt);
  letter-spacing: 2px; line-height: 1.2; margin-bottom: 12px;
}
.section-sub {
  font-size: 16px; color: var(--body);
  max-width: 560px; line-height: 1.8;
}

/* ── Shared buttons ── */
.btn-primary {
  padding: 12px 28px;
  background: var(--pri); color: #000;
  font-family: 'Courier New', monospace;
  font-size: 12px; font-weight: bold; letter-spacing: 2px;
  border: none; border-radius: 2px; cursor: pointer;
  text-decoration: none; display: inline-block;
}
.btn-outline {
  padding: 12px 28px;
  background: transparent; color: var(--pri);
  font-family: 'Courier New', monospace;
  font-size: 12px; letter-spacing: 2px;
  border: 1px solid rgba(0,212,255,0.35); border-radius: 2px;
  cursor: pointer; text-decoration: none; display: inline-block;
  transition: border-color 0.2s, background 0.2s;
}
.btn-outline:hover { border-color: var(--pri); background: rgba(0,212,255,0.05); }
```

- [x] **Step 2: Verify — open in browser**

```bash
# http://localhost:8080 (server from Task 1)
```

Expected: blank black page, body font is Courier New (inspect → computed).

- [x] **Step 3: Commit**

```bash
git add assets/landing/style.css
git commit -m "feat: add CSS variables, reset, and base utility styles"
```

---

## Task 3: HTML + CSS — Header

**Files:**
- Modify: `index.html` (replace `<!-- HEADER -->` comment)
- Modify: `assets/landing/style.css` (append header CSS)

- [x] **Step 1: Add header HTML** — replace `<!-- HEADER -->` in `index.html`

```html
<header>
  <div class="nav-brand">
    <img class="nav-logo" src="assets/icon.png" alt="VIKO">
    <span class="nav-name">VIKO</span>
  </div>
  <nav class="nav-links">
    <a class="nav-link" href="#features">Features</a>
    <a class="nav-link" href="#preview">Preview</a>
    <a class="nav-link" href="#github">GitHub</a>
    <a class="nav-cta" href="https://github.com/eksant/viko-assistant">VIEW ON GITHUB →</a>
  </nav>
</header>
```

- [x] **Step 2: Add header CSS** — append to `assets/landing/style.css`

```css
/* ════ HEADER ════ */
header {
  position: sticky; top: 0; z-index: 100;
  background: rgba(0,0,0,0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 48px; height: 64px;
  display: flex; align-items: center; justify-content: space-between;
}
.nav-brand { display: flex; align-items: center; gap: 12px; }
.nav-logo { width: 32px; height: 32px; object-fit: contain; }
.nav-name { font-size: 20px; font-weight: bold; color: var(--pri); letter-spacing: 4px; }
.nav-links { display: flex; align-items: center; gap: 32px; }
.nav-link {
  font-size: 12px; color: var(--dim); letter-spacing: 2px;
  text-decoration: none; text-transform: uppercase; transition: color 0.2s;
}
.nav-link:hover { color: var(--pri); }
.nav-cta {
  padding: 8px 20px; background: var(--pri); color: #000;
  font-family: 'Courier New', monospace; font-size: 11px;
  font-weight: bold; letter-spacing: 2px;
  border-radius: 2px; text-decoration: none;
}
```

- [x] **Step 3: Verify**

Open `http://localhost:8080`. Expected: dark sticky header with VIKO logo (or broken img placeholder), cyan VIKO text, nav links, cyan CTA button. Header stays fixed on scroll.

- [x] **Step 4: Commit**

```bash
git add index.html assets/landing/style.css
git commit -m "feat: add sticky header with logo and nav"
```

---

## Task 4: HTML + CSS — Hero section

**Files:**
- Modify: `index.html` (replace `<!-- HERO -->`)
- Modify: `assets/landing/style.css` (append hero CSS)

- [x] **Step 1: Add hero HTML** — replace `<!-- HERO -->` in `index.html`

```html
<section class="hero">
  <div class="hero-bg">
    <img src="docs/screenshots/dashboard.png" alt="" onerror="this.style.display='none'">
  </div>
  <div class="hero-fade-top"></div>
  <div class="hero-fade-left"></div>
  <div class="hero-fade-bottom"></div>
  <div class="hero-hud">
    <svg id="heroHud" viewBox="0 0 400 400" overflow="visible"></svg>
  </div>
  <div class="hero-content">
    <div class="hero-eyebrow">▶ Personal AI Voice Assistant</div>
    <div class="hero-title">VIKO</div>
    <div class="voice-bar">
      <span></span><span></span><span></span><span></span>
      <span></span><span></span><span></span><span></span><span></span>
    </div>
    <div class="hero-tagline">Your voice. Your AI. Your rules.</div>
    <div class="hero-desc">
      A personal AI assistant that listens, thinks, and speaks back —
      powered by Gemini Live API. Lives on your machine. Knows your voice.
    </div>
    <div class="hero-cta">
      <a class="btn-primary" href="https://github.com/eksant/viko-assistant">VIEW ON GITHUB →</a>
      <a class="btn-outline" href="#features">EXPLORE FEATURES ↓</a>
    </div>
  </div>
</section>
```

- [x] **Step 2: Add hero CSS** — append to `assets/landing/style.css`

```css
/* ════ HERO ════ */
.hero {
  position: relative; height: 600px;
  overflow: hidden; display: flex; align-items: center;
  border-bottom: 1px solid var(--border);
}

/* Layer 1 — faint screenshot BG */
.hero-bg { position: absolute; inset: 0; z-index: 0; }
.hero-bg img { width: 100%; height: 100%; object-fit: cover; object-position: top left; opacity: 0.18; }

/* Layer 2 — gradient overlays */
.hero-fade-top {
  position: absolute; top: 0; left: 0; right: 0; height: 80px;
  background: linear-gradient(to bottom, #000, transparent); z-index: 2;
}
.hero-fade-left {
  position: absolute; left: 0; top: 0; bottom: 0; width: 65%;
  background: linear-gradient(to right, rgba(0,0,0,0.92) 40%, transparent 100%); z-index: 2;
}
.hero-fade-bottom {
  position: absolute; bottom: 0; left: 0; right: 0; height: 140px;
  background: linear-gradient(to bottom, transparent, #000); z-index: 2;
}

/* Layer 3 — HUD circle */
.hero-hud {
  position: absolute; left: 50%; top: 50%;
  transform: translate(-5%, -50%);
  width: 820px; height: 820px; z-index: 3; opacity: 0.78;
}
.hero-hud svg { width: 100%; height: 100%; }

/* Layer 4 — text content */
.hero-content {
  position: relative; z-index: 5;
  padding: 0 64px; width: 54%;
  display: flex; flex-direction: column; gap: 16px;
}

.hero-eyebrow { font-size: 11px; color: var(--pri); letter-spacing: 5px; text-transform: uppercase; }
.hero-title {
  font-size: 80px; font-weight: bold; color: var(--pri);
  letter-spacing: 8px; line-height: 1;
  text-shadow: 0 0 40px rgba(0,212,255,0.3);
}
.hero-tagline { font-size: 20px; color: var(--txt); line-height: 1.5; max-width: 380px; }
.hero-desc { font-size: 16px; color: var(--body); line-height: 1.8; max-width: 380px; }
.hero-cta { display: flex; gap: 12px; margin-top: 8px; }

/* Voice bar */
.voice-bar { display: flex; gap: 4px; align-items: center; height: 28px; margin: 4px 0; }
.voice-bar span {
  display: inline-block; width: 4px; background: var(--pri);
  border-radius: 2px; animation: vbar 0.9s ease-in-out infinite alternate;
}
.voice-bar span:nth-child(1){height:6px;  animation-delay:0.00s; opacity:0.25}
.voice-bar span:nth-child(2){height:12px; animation-delay:0.10s; opacity:0.50}
.voice-bar span:nth-child(3){height:22px; animation-delay:0.05s}
.voice-bar span:nth-child(4){height:28px; animation-delay:0.15s}
.voice-bar span:nth-child(5){height:22px; animation-delay:0.08s}
.voice-bar span:nth-child(6){height:14px; animation-delay:0.20s; opacity:0.60}
.voice-bar span:nth-child(7){height:8px;  animation-delay:0.25s; opacity:0.35}
.voice-bar span:nth-child(8){height:18px; animation-delay:0.12s; opacity:0.70}
.voice-bar span:nth-child(9){height:10px; animation-delay:0.18s; opacity:0.40}
@keyframes vbar { from { transform: scaleY(0.25); } to { transform: scaleY(1); } }
```

- [x] **Step 3: Verify**

Open `http://localhost:8080`. Expected: 600px hero — faint dashboard screenshot as BG, gradient overlays, cyan "VIKO" title (80px), animated voice bar, tagline, two CTA buttons. HUD div exists but is empty (no JS yet — next task).

- [x] **Step 4: Commit**

```bash
git add index.html assets/landing/style.css
git commit -m "feat: add hero section with layered background and voice bar"
```

---

## Task 5: JS — HUD circle animation

**Files:**
- Modify: `assets/landing/main.js`

- [x] **Step 1: Write HUD animation** — replace content of `assets/landing/main.js`

```js
// VIKO Landing Page — main.js

// ── HUD Circle ──────────────────────────────────────────────────────────────
(function () {
  const svgEl = document.getElementById('heroHud');
  if (!svgEl) return;

  const cx = 200, cy = 200;
  let amberAngle   = 30;    // clockwise, r=174
  let counterAngle = 200;   // counter-clockwise, r=126
  let pulseT       = 0;     // 0→1 cycle for pulse waves

  const RINGS = [
    { r: 188, dash: '3 11',  op: 0.55, w: 0.8 },
    { r: 174, dash: '2 16',  op: 0.25, w: 0.5 },
    { r: 158, dash: '5 7',   op: 0.45, w: 0.7 },
    { r: 142, dash: '2 12',  op: 0.20, w: 0.5 },
    { r: 126, dash: '7 5',   op: 0.38, w: 0.7 },
    { r: 108, dash: '3 9',   op: 0.18, w: 0.5 },
    { r: 90,  dash: '2 7',   op: 0.30, w: 0.6 },
    { r: 72,  dash: 'none',  op: 0.13, w: 0.5 },
    { r: 52,  dash: 'none',  op: 0.18, w: 0.5 },
    { r: 34,  dash: 'none',  op: 0.25, w: 0.7 },
  ];

  function drawHUD(ambAngle, ctrAngle, pulse) {
    let h = '';

    // Pulse waves — expand past HUD into hero area
    [0, 0.34, 0.67].forEach((offset, i) => {
      const phase = (pulse + offset) % 1;
      const r     = 22 + phase * 320;
      const op    = (1 - phase) * (0.32 - i * 0.06);
      const sw    = 1.4 - phase * 1.0;
      if (op > 0.005) {
        h += `<circle cx="${cx}" cy="${cy}" r="${r.toFixed(1)}" fill="none" stroke="#00D4FF" stroke-width="${sw.toFixed(2)}" opacity="${op.toFixed(3)}"/>`;
      }
    });

    // Static rings
    RINGS.forEach(ring => {
      const da = ring.dash === 'none' ? '' : `stroke-dasharray="${ring.dash}"`;
      h += `<circle cx="${cx}" cy="${cy}" r="${ring.r}" fill="none" stroke="#00D4FF" stroke-width="${ring.w}" opacity="${ring.op}" ${da}/>`;
    });

    // Tick marks — outer ring (72 ticks, major every 6th)
    for (let i = 0; i < 72; i++) {
      const a = (i / 72) * Math.PI * 2;
      const outer = 191, inner = i % 6 === 0 ? 178 : 185;
      const x1 = cx + Math.cos(a) * outer, y1 = cy + Math.sin(a) * outer;
      const x2 = cx + Math.cos(a) * inner, y2 = cy + Math.sin(a) * inner;
      h += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#00D4FF" stroke-width="${i%6===0?1:0.5}" opacity="${i%6===0?0.65:0.25}"/>`;
    }

    // Cardinal dots N/E/S/W on r=158
    [0, 90, 180, 270].forEach(deg => {
      const rad = (deg - 90) * Math.PI / 180;
      const x = cx + Math.cos(rad) * 158, y = cy + Math.sin(rad) * 158;
      h += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="#00D4FF" opacity="0.85"/>`;
      h += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="7" fill="none" stroke="#00D4FF" stroke-width="0.6" opacity="0.35"/>`;
    });

    // Amber arc — clockwise, r=174, 80° sweep
    const r1 = 174;
    const a1s = (ambAngle - 90) * Math.PI / 180;
    const a1e = (ambAngle - 90 + 80) * Math.PI / 180;
    const ax1 = (cx + Math.cos(a1s) * r1).toFixed(1), ay1 = (cy + Math.sin(a1s) * r1).toFixed(1);
    const ax2 = (cx + Math.cos(a1e) * r1).toFixed(1), ay2 = (cy + Math.sin(a1e) * r1).toFixed(1);
    h += `<path d="M${ax1} ${ay1} A${r1} ${r1} 0 0 1 ${ax2} ${ay2}" fill="none" stroke="#FFB347" stroke-width="3" opacity="0.92" stroke-linecap="round"/>`;
    h += `<path d="M${ax1} ${ay1} A${r1} ${r1} 0 0 1 ${ax2} ${ay2}" fill="none" stroke="#FFB347" stroke-width="12" opacity="0.10"/>`;
    h += `<circle cx="${ax2}" cy="${ay2}" r="3" fill="#FFB347" opacity="0.95"/>`;

    // Counter arc — counter-clockwise, r=126, 55° sweep, orange
    const r2 = 126;
    const a2s = (ctrAngle - 90) * Math.PI / 180;
    const a2e = (ctrAngle - 90 - 55) * Math.PI / 180;
    const bx1 = (cx + Math.cos(a2s) * r2).toFixed(1), by1 = (cy + Math.sin(a2s) * r2).toFixed(1);
    const bx2 = (cx + Math.cos(a2e) * r2).toFixed(1), by2 = (cy + Math.sin(a2e) * r2).toFixed(1);
    h += `<path d="M${bx1} ${by1} A${r2} ${r2} 0 0 0 ${bx2} ${by2}" fill="none" stroke="#FF6B35" stroke-width="2" opacity="0.85" stroke-linecap="round"/>`;
    h += `<path d="M${bx1} ${by1} A${r2} ${r2} 0 0 0 ${bx2} ${by2}" fill="none" stroke="#FF6B35" stroke-width="8" opacity="0.10"/>`;
    h += `<circle cx="${bx2}" cy="${by2}" r="2.5" fill="#FF6B35" opacity="0.90"/>`;

    // Center glow
    h += `<circle cx="${cx}" cy="${cy}" r="24" fill="none" stroke="#00D4FF" stroke-width="0.8" opacity="0.3" stroke-dasharray="4 8"/>`;
    h += `<circle cx="${cx}" cy="${cy}" r="14" fill="none" stroke="#00D4FF" stroke-width="1" opacity="0.5"/>`;
    h += `<circle cx="${cx}" cy="${cy}" r="5"  fill="#00D4FF" opacity="1"/>`;
    h += `<circle cx="${cx}" cy="${cy}" r="20" fill="#00D4FF" opacity="0.05"/>`;
    h += `<circle cx="${cx}" cy="${cy}" r="50" fill="#00D4FF" opacity="0.02"/>`;

    // Labels
    h += `<text x="${cx}" y="${cy-204}" text-anchor="middle" fill="#5A91B9" font-family="'Courier New'" font-size="10" letter-spacing="4" opacity="0.75">SYSTEM TRACKING</text>`;
    h += `<text x="${cx}" y="${cy+218}" text-anchor="middle" fill="#00D4FF" font-family="'Courier New'" font-size="10" letter-spacing="5" opacity="0.65">◦  STANDBY</text>`;

    svgEl.innerHTML = h;
  }

  drawHUD(amberAngle, counterAngle, pulseT);
  setInterval(() => {
    amberAngle   = (amberAngle + 0.35) % 360;
    counterAngle = (counterAngle - 0.22 + 360) % 360;
    pulseT       = (pulseT + 0.0035) % 1;
    drawHUD(amberAngle, counterAngle, pulseT);
  }, 40);
}());
```

- [x] **Step 2: Verify**

Open `http://localhost:8080`. Expected: HUD circle appears right of hero center — 10 concentric rings, amber arc rotating clockwise, orange arc rotating counter-clockwise, 3 pulse waves expanding from center. Animation runs smoothly.

- [x] **Step 3: Commit**

```bash
git add assets/landing/main.js
git commit -m "feat: add animated HUD circle with dual arcs and pulse waves"
```

---

## Task 6: HTML + CSS — Why VIKO section

**Files:**
- Modify: `index.html` (replace `<!-- WHY VIKO -->`)
- Modify: `assets/landing/style.css` (append)

- [x] **Step 1: Add Why VIKO HTML** — replace `<!-- WHY VIKO -->` in `index.html`

```html
<section class="story">
  <div class="story-text reveal">
    <div class="label">Why VIKO</div>
    <div class="sep"></div>
    <div class="story-title">
      Built for one reason:<br>
      a truly <em>personal</em> AI.
    </div>
    <div class="story-body">
      <p>Most AI tools talk at you through a chat box. VIKO was built to talk <em>with</em> you — in real-time, by voice, naturally.</p>
      <p>The idea was simple: what if your AI assistant actually knew who you were? Recognized your voice. Remembered your conversations. Lived on your machine — not on a server farm somewhere.</p>
      <p>VIKO is the result of that idea. A futuristic HUD on your screen. A voice that listens. An AI that can even update itself when you ask it to.</p>
    </div>
  </div>
  <div class="story-stats reveal">
    <div class="stat-block">
      <div class="stat-number">20+</div>
      <div class="stat-label">Built-in skills — web search, reminders, dev agent, and more</div>
    </div>
    <div class="stat-block amber">
      <div class="stat-number">100%</div>
      <div class="stat-label">Voice-first — every feature accessible by speaking</div>
    </div>
    <div class="stat-block green">
      <div class="stat-number">Live</div>
      <div class="stat-label">Real-time streaming audio via Gemini Live API</div>
    </div>
  </div>
</section>
```

- [x] **Step 2: Add Why VIKO CSS** — append to `assets/landing/style.css`

```css
/* ════ WHY VIKO ════ */
.story {
  padding: 96px 64px;
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 80px; align-items: center;
  border-bottom: 1px solid var(--border);
}
.story-title {
  font-size: 36px; font-weight: bold; color: var(--txt);
  letter-spacing: 2px; line-height: 1.3; margin-bottom: 24px;
}
.story-title em { color: var(--pri); font-style: normal; }
.story-body { font-size: 16px; color: var(--body); line-height: 2; }
.story-body p + p { margin-top: 16px; }
.story-body em { color: var(--txt); font-style: italic; }

.story-stats { display: flex; flex-direction: column; gap: 24px; }
.stat-block {
  padding: 28px 32px; background: var(--card);
  border: 1px solid var(--border); border-left: 3px solid var(--pri);
}
.stat-block.amber { border-left-color: var(--amb); }
.stat-block.green  { border-left-color: var(--suc); }
.stat-number {
  font-size: 40px; font-weight: bold; color: var(--pri);
  letter-spacing: 2px; line-height: 1; margin-bottom: 6px;
}
.stat-block.amber .stat-number { color: var(--amb); }
.stat-block.green  .stat-number { color: var(--suc); }
.stat-label { font-size: 13px; color: var(--body); letter-spacing: 1px; }
```

- [x] **Step 3: Verify**

Scroll past hero. Expected: 2-column section — story text left (3 paragraphs, "personal" in cyan), 3 stat blocks right (20+, 100%, Live) with cyan/amber/green left borders.

- [x] **Step 4: Commit**

```bash
git add index.html assets/landing/style.css
git commit -m "feat: add Why VIKO story section with stats"
```

---

## Task 7: HTML + CSS — Features section

**Files:**
- Modify: `index.html` (replace `<!-- FEATURES -->`)
- Modify: `assets/landing/style.css` (append)

- [x] **Step 1: Add Features HTML** — replace `<!-- FEATURES -->` in `index.html`

```html
<section class="features" id="features">
  <div class="features-intro reveal">
    <div class="label">Capabilities</div>
    <div class="sep"></div>
    <div class="section-title">What VIKO can do</div>
    <div class="section-sub">From everyday tasks to full project development — all accessible by voice, all running locally.</div>
  </div>
  <div class="features-grid reveal">
    <div class="feature-card">
      <div class="feature-icon">◉</div>
      <div class="feature-name">REAL-TIME VOICE</div>
      <div class="feature-desc">Native audio streaming via Gemini Live API. No delays, no chunking — true real-time conversation.</div>
    </div>
    <div class="feature-card amber">
      <div class="feature-icon">◈</div>
      <div class="feature-name">FUTURISTIC HUD</div>
      <div class="feature-desc">Sci-fi dark UI with live system metrics, animated vector world map, clock, and status indicators.</div>
    </div>
    <div class="feature-card">
      <div class="feature-icon">◑</div>
      <div class="feature-name">SPEAKER VERIFICATION</div>
      <div class="feature-desc">Enrolls your voice using resemblyzer embeddings. Only the owner's voice unlocks VIKO — everyone else is gated.</div>
    </div>
    <div class="feature-card green">
      <div class="feature-icon">◎</div>
      <div class="feature-name">SELF-MODIFICATION</div>
      <div class="feature-desc">Tell VIKO to add a new skill, fix a bug, or update its own personality — and it does it, live.</div>
    </div>
    <div class="feature-card">
      <div class="feature-icon">◇</div>
      <div class="feature-name">LONG-TERM MEMORY</div>
      <div class="feature-desc">Remembers your conversations and preferences. Vector memory via ChromaDB + SQLite + Gemini embeddings.</div>
    </div>
    <div class="feature-card amber">
      <div class="feature-icon">◆</div>
      <div class="feature-name">20+ SKILLS</div>
      <div class="feature-desc">Web search, file management, app control, weather, flights, reminders, news, and more — all by voice.</div>
    </div>
    <div class="feature-card green">
      <div class="feature-icon">◌</div>
      <div class="feature-name">DEV AGENT</div>
      <div class="feature-desc">Describe a project out loud. VIKO plans, writes, tests, and commits the code — plan → code → git.</div>
    </div>
    <div class="feature-card">
      <div class="feature-icon">◐</div>
      <div class="feature-name">LIVE LOCATION</div>
      <div class="feature-desc">GPS via macOS CoreLocation with Nominatim geocoding. Animated map marker on the HUD at all times.</div>
    </div>
  </div>
</section>
```

- [x] **Step 2: Add Features CSS** — append to `assets/landing/style.css`

```css
/* ════ FEATURES ════ */
.features { padding: 96px 64px; border-bottom: 1px solid var(--border); }
.features-intro { margin-bottom: 48px; }
.features-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 1px; background: var(--border);
  border: 1px solid var(--border);
}
.feature-card {
  background: var(--card); padding: 28px 24px;
  display: flex; flex-direction: column; gap: 10px;
  transition: background 0.2s;
}
.feature-card:hover { background: #060d16; }
.feature-icon { font-size: 20px; color: var(--pri); line-height: 1; }
.feature-card.amber .feature-icon { color: var(--amb); }
.feature-card.green  .feature-icon { color: var(--suc); }
.feature-name { font-size: 13px; font-weight: bold; color: var(--txt); letter-spacing: 1.5px; line-height: 1.3; }
.feature-desc { font-size: 14px; color: var(--body); line-height: 1.7; flex: 1; }
```

- [x] **Step 3: Verify**

Scroll to features. Expected: 4×2 grid of dark cards, each with a symbol icon (cyan/amber/green), bold name, description. Cards have a subtle background shift on hover.

- [x] **Step 4: Commit**

```bash
git add index.html assets/landing/style.css
git commit -m "feat: add 8-card features grid"
```

---

## Task 8: HTML + CSS — Screenshots section

**Files:**
- Modify: `index.html` (replace `<!-- SCREENSHOTS -->`)
- Modify: `assets/landing/style.css` (append)

- [x] **Step 1: Add Screenshots HTML** — replace `<!-- SCREENSHOTS -->` in `index.html`

```html
<section class="screenshots" id="preview">
  <div class="screenshots-intro reveal">
    <div class="label">Preview</div>
    <div class="sep"></div>
    <div class="section-title">See it in action</div>
    <div class="section-sub">Three modes, one interface — built for a future that feels like now.</div>
  </div>
  <div class="screenshots-grid reveal">
    <div class="shot-card">
      <div class="shot-img">
        <img src="docs/screenshots/dashboard.png" alt="Dashboard" onerror="this.parentElement.textContent='dashboard.png'">
      </div>
      <div class="shot-caption">
        <strong>DASHBOARD</strong>
        Live metrics, GPS map, system status — always visible on the HUD.
      </div>
    </div>
    <div class="shot-card">
      <div class="shot-img">
        <img src="docs/screenshots/text-chat.png" alt="Text Chat" onerror="this.parentElement.textContent='text-chat.png'">
      </div>
      <div class="shot-caption">
        <strong>TEXT CHAT</strong>
        Full conversation history with activity log and context awareness.
      </div>
    </div>
    <div class="shot-card">
      <div class="shot-img">
        <img src="docs/screenshots/voice-chat.png" alt="Voice Chat" onerror="this.parentElement.textContent='voice-chat.png'">
      </div>
      <div class="shot-caption">
        <strong>VOICE CHAT</strong>
        Real-time audio visualizer while VIKO listens and speaks back.
      </div>
    </div>
  </div>
</section>
```

- [x] **Step 2: Add Screenshots CSS** — append to `assets/landing/style.css`

```css
/* ════ SCREENSHOTS ════ */
.screenshots { padding: 96px 64px; background: var(--card); border-bottom: 1px solid var(--border); }
.screenshots-intro { margin-bottom: 48px; }
.screenshots-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.shot-card { border: 1px solid var(--border); overflow: hidden; transition: border-color 0.2s; }
.shot-card:hover { border-color: rgba(0,212,255,0.4); }
.shot-img { width: 100%; aspect-ratio: 16/10; overflow: hidden; background: #000; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #1a3a5a; }
.shot-img img { width: 100%; height: 100%; object-fit: cover; object-position: top left; display: block; }
.shot-caption { padding: 14px 16px; border-top: 1px solid var(--border); font-size: 14px; color: var(--body); letter-spacing: 1px; }
.shot-caption strong { display: block; color: var(--txt); margin-bottom: 2px; letter-spacing: 2px; }
```

- [x] **Step 3: Verify**

Scroll to screenshots. Expected: 3-column grid on dark card background, each with a 16:10 image (actual screenshots now visible!), bold section label, and description below.

- [x] **Step 4: Commit**

```bash
git add index.html assets/landing/style.css
git commit -m "feat: add 3-panel screenshots section"
```

---

## Task 9: HTML + CSS — GitHub CTA + Footer

**Files:**
- Modify: `index.html` (replace `<!-- GITHUB CTA -->` and `<!-- FOOTER -->`)
- Modify: `assets/landing/style.css` (append)

- [x] **Step 1: Add GitHub CTA + Footer HTML**

Replace `<!-- GITHUB CTA -->` in `index.html`:

```html
<section class="github-cta" id="github">
  <div class="label reveal">Open Source</div>
  <div class="github-cta-title reveal">
    Explore the full project<br>on <span>GitHub →</span>
  </div>
  <div class="github-cta-sub reveal">
    Source code, setup guide, architecture docs, and contribution notes —
    everything you need to understand or run VIKO yourself.
  </div>
  <div class="github-tech reveal">
    <span class="tech-pill cyan">Gemini Live API</span>
    <span class="tech-pill amber">Claude Sonnet</span>
    <span class="tech-pill cyan">PyQt6</span>
    <span class="tech-pill">Python 3.11+</span>
    <span class="tech-pill">resemblyzer</span>
    <span class="tech-pill">ChromaDB</span>
    <span class="tech-pill">SQLite</span>
    <span class="tech-pill">macOS</span>
  </div>
  <a class="btn-primary reveal" href="https://github.com/eksant/viko-assistant" style="margin-top:8px;font-size:14px;padding:14px 36px">
    VIEW ON GITHUB →
  </a>
</section>
```

Replace `<!-- FOOTER -->` in `index.html`:

```html
<footer>
  <div class="footer-brand">
    <img class="footer-logo" src="assets/icon.png" alt="VIKO" onerror="this.style.display='none'">
    <span class="footer-name">VIKO</span>
  </div>
  <div class="footer-center">
    <div class="footer-links">
      <a class="footer-link" href="https://github.com/eksant/viko-assistant">GitHub</a>
      <a class="footer-link" href="https://github.com/eksant/viko-assistant/blob/main/LICENSE">License</a>
      <a class="footer-link" href="https://github.com/eksant/viko-assistant#readme">Docs</a>
    </div>
    <a class="footer-email" href="mailto:eksant@gmail.com">eksant@gmail.com</a>
  </div>
  <div class="footer-copy">Proprietary · eksant · 2026</div>
</footer>
```

- [x] **Step 2: Add GitHub CTA + Footer CSS** — append to `assets/landing/style.css`

```css
/* ════ GITHUB CTA ════ */
.github-cta {
  padding: 96px 64px; border-bottom: 1px solid var(--border);
  text-align: center; display: flex; flex-direction: column;
  align-items: center; gap: 20px;
}
.github-cta .label { text-align: center; }
.github-cta-title { font-size: 36px; font-weight: bold; color: var(--txt); letter-spacing: 2px; line-height: 1.3; }
.github-cta-title span { color: var(--pri); }
.github-cta-sub { font-size: 16px; color: var(--body); max-width: 480px; line-height: 1.8; }
.github-tech { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 8px; }
.tech-pill { padding: 6px 14px; background: transparent; border: 1px solid var(--border); font-size: 12px; color: var(--dim); letter-spacing: 1px; border-radius: 2px; }
.tech-pill.cyan  { border-color: rgba(0,212,255,0.35); color: var(--pri); }
.tech-pill.amber { border-color: rgba(255,179,71,0.35); color: var(--amb); }

/* ════ FOOTER ════ */
footer { padding: 40px 64px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.footer-brand { display: flex; align-items: center; gap: 10px; }
.footer-logo { width: 24px; height: 24px; object-fit: contain; opacity: 0.8; }
.footer-name { font-size: 18px; font-weight: bold; color: var(--pri); letter-spacing: 4px; }
.footer-center { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.footer-links { display: flex; gap: 24px; }
.footer-link { font-size: 12px; color: var(--dim); letter-spacing: 1.5px; text-decoration: none; text-transform: uppercase; }
.footer-link:hover { color: var(--pri); }
.footer-email { font-size: 12px; color: var(--dim); text-decoration: none; }
.footer-email:hover { color: var(--pri); }
.footer-copy { font-size: 11px; color: var(--dim); }
```

- [x] **Step 3: Verify**

Scroll to bottom. Expected: centered GitHub CTA with tech pills (cyan/amber/muted), large cyan GitHub button. Footer: logo+VIKO left, links+email center, copyright right. All footer text visible.

- [x] **Step 4: Commit**

```bash
git add index.html assets/landing/style.css
git commit -m "feat: add GitHub CTA section and footer"
```

---

## Task 10: JS — Scroll reveal

**Files:**
- Modify: `assets/landing/main.js` (append)

- [x] **Step 1: Append scroll reveal to `assets/landing/main.js`**

```js
// ── Scroll reveal ────────────────────────────────────────────────────────────
(function () {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); }),
    { threshold: 0.1 }
  );
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}());
```

- [x] **Step 2: Verify**

Reload page. Scroll slowly through all sections. Expected: each `.reveal` element fades in and slides up as it enters the viewport. Elements above the fold are immediately visible. No flicker.

- [x] **Step 3: Commit**

```bash
git add assets/landing/main.js
git commit -m "feat: add scroll reveal with IntersectionObserver"
```

---

## Task 11: CSS — Responsive breakpoints

**Files:**
- Modify: `assets/landing/style.css` (append)

- [x] **Step 1: Append responsive CSS to `assets/landing/style.css`**

```css
/* ════ RESPONSIVE ════ */

/* Tablet (≤900px) */
@media (max-width: 900px) {
  .features-grid { grid-template-columns: repeat(2, 1fr); }
  .screenshots-grid { grid-template-columns: repeat(2, 1fr); }
  .story { grid-template-columns: 1fr; gap: 48px; padding: 64px 40px; }
  .hero-content { width: 70%; padding: 0 40px; }
  .hero-hud { width: 600px; height: 600px; }
  .hero-title { font-size: 64px; }
  .features { padding: 64px 40px; }
  .screenshots { padding: 64px 40px; }
  .github-cta { padding: 64px 40px; }
  footer { padding: 32px 40px; }
}

/* Mobile (≤600px) */
@media (max-width: 600px) {
  header { padding: 0 20px; }
  .nav-links .nav-link { display: none; }
  .nav-cta { font-size: 10px; padding: 7px 14px; }

  .hero { height: auto; min-height: 500px; padding: 80px 0 48px; }
  .hero-hud { right: 50%; transform: translate(50%, -50%); width: 420px; height: 420px; opacity: 0.2; }
  .hero-fade-left { width: 100%; background: rgba(0,0,0,0.7); }
  .hero-content { width: 100%; padding: 0 24px; }
  .hero-title { font-size: 52px; letter-spacing: 6px; }
  .hero-tagline { font-size: 18px; }
  .hero-desc { font-size: 14px; }
  .hero-cta { flex-direction: column; gap: 10px; }
  .btn-primary, .btn-outline { width: 100%; text-align: center; }

  .story { padding: 56px 24px; gap: 36px; }
  .story-title { font-size: 26px; }
  .story-body { font-size: 15px; }

  .features { padding: 56px 24px; }
  .features-grid { grid-template-columns: 1fr; }
  .section-title { font-size: 24px; }

  .screenshots { padding: 56px 24px; }
  .screenshots-grid { grid-template-columns: 1fr; }

  .github-cta { padding: 56px 24px; }
  .github-cta-title { font-size: 26px; }
  .github-cta-sub { font-size: 14px; }

  footer { padding: 28px 24px; flex-direction: column; align-items: flex-start; gap: 16px; }
  .footer-center { align-items: flex-start; }
}
```

- [x] **Step 2: Verify tablet layout**

Open DevTools → toggle device toolbar → set width to 800px. Expected: features grid 2-col, screenshots 2-col, story stacks vertically.

- [x] **Step 3: Verify mobile layout**

Set width to 375px. Expected: header shows only logo + CTA button, hero stacks vertically with faint HUD, all grids single column, buttons full-width.

- [x] **Step 4: Commit**

```bash
git add assets/landing/style.css
git commit -m "feat: add responsive breakpoints for tablet and mobile"
```

---

## Task 12: Final check + GitHub Pages deploy

**Files:**
- None new — verification and deploy only

- [x] **Step 1: Full page visual check**

Open `http://localhost:8080`. Check each section in order:
- [x] Header sticks on scroll, logo visible, all nav links work
- [x] Hero: HUD animation running, voice bar animated, faint screenshot BG visible, text readable
- [x] Why VIKO: 2-column story + 3 stat blocks visible, scroll reveal works
- [x] Features: 4×2 grid, icons colored (cyan/amber/green), hover effect works
- [x] Screenshots: 3 images fully visible (dashboard, text-chat, voice-chat)
- [x] GitHub CTA: tech pills visible, GitHub button links correctly
- [x] Footer: email visible, copyright text visible

- [x] **Step 2: Check all links**

```bash
grep -o 'href="[^"]*"' index.html
```

Verify: no broken anchors, all GitHub URLs contain `https://`, email uses `mailto:`.

- [x] **Step 3: Add `.nojekyll` file** (prevents GitHub Pages from processing with Jekyll)

```bash
touch .nojekyll
git add .nojekyll
```

- [x] **Step 4: Final commit**

```bash
git add .nojekyll
git commit -m "feat: complete VIKO landing page"
```

- [x] **Step 5: Enable GitHub Pages**

In the GitHub repo settings:
- Settings → Pages → Source → Deploy from branch → `main` → `/ (root)`
- Save

The page will be live at `https://eksant.github.io/viko-assistant/` within ~60 seconds.

---

## Self-Review

**Spec coverage check:**
- [x] Sticky header with logo, nav, GitHub CTA → Task 3
- [x] Hero: 3-layer BG (screenshot + gradient + HUD) + text + voice bar → Task 4
- [x] HUD circle: 10 rings, ticks, cardinal dots, amber arc CW, orange arc CCW, pulse waves → Task 5
- [x] Why VIKO story + 3 stat blocks → Task 6
- [x] Features 4×2 grid, 8 cards → Task 7
- [x] Screenshots 3-panel → Task 8
- [x] GitHub CTA + tech pills → Task 9
- [x] Footer: logo, links, email, copyright → Task 9
- [x] Scroll reveal → Task 10
- [x] Responsive tablet + mobile → Task 11
- [x] Image paths use `docs/screenshots/` and `assets/icon.png` → verified throughout

**No placeholders** — all tasks contain complete, runnable code ✅

**Type/name consistency** — CSS class names consistent across HTML and CSS tasks:
- `.hero-hud`, `.hero-bg`, `.hero-fade-*`, `.hero-content` consistent Tasks 4→11
- `.story`, `.stat-block`, `.feature-card`, `.shot-card` consistent Tasks 6→11
- `drawHUD(ambAngle, ctrAngle, pulse)` defined and called in Task 5 only ✅
