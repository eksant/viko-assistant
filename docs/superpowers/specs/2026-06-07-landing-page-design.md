# VIKO Landing Page — Design Spec
Date: 2026-06-07

## Overview

A static landing page for the VIKO personal AI voice assistant project, hosted on GitHub Pages. Visually coherent with the VIKO application's dark futuristic HUD aesthetic. Targets both developer/showcase audiences and potential users who want to understand and run the project.

---

## Goals

- **Primary**: Showcase what VIKO is and why it was built (personal AI voice companion)
- **Secondary**: Direct interested users to the GitHub repository for setup details
- No inline installation guide — all technical details link out to GitHub

---

## Tech Stack

- **Pure HTML/CSS/JS** — single `index.html` at repo root, one `assets/landing/style.css`, one `assets/landing/main.js`
- **Zero dependencies** — no npm, no build step, no framework
- **Deploy**: GitHub Pages from `main` branch root
- **Images**: `docs/screenshots/` (already present), `assets/icon.png` (logo)

---

## Visual Identity

Directly derived from `viko/ui/theme.py`:

| Token | Value | Usage |
|---|---|---|
| Background | `#000000` | Page background |
| Card | `#04080E` | Section/card backgrounds |
| Text | `#F2F9FF` | Headings, titles |
| Body | `#D4E8F5` | Body paragraphs, descriptions |
| Dim | `#5A91B9` | Labels, captions, nav links |
| Primary | `#00D4FF` | Cyan accent — CTAs, icons, borders |
| Amber | `#FFB347` | Warm accent — stat blocks, feature icons |
| Success | `#00FF9F` | Green accent — feature icons |
| Border | `#0d1f2d` | Subtle dividers |

**Typography**: `'Courier New', Courier, monospace` — 17px body, same font as VIKO app.

---

## Page Structure

```
Header (sticky nav)
  └── Logo (icon.png) + VIKO wordmark + nav links + GitHub CTA button

Hero (600px height)
  └── Layer 1: dashboard.png at 18% opacity (full bleed background)
  └── Layer 2: gradient overlays (left: black→transparent, top/bottom fades)
  └── Layer 3: animated HUD circle SVG (820px, center-right, overlaps text)
  └── Layer 4: text content (left side, z-index 5)
      ├── Eyebrow: "▶ PERSONAL AI VOICE ASSISTANT"
      ├── Title: "VIKO" (80px, cyan, text-shadow glow)
      ├── Animated voice bar (9 bars, CSS animation)
      ├── Tagline: "Your voice. Your AI. Your rules."
      ├── Description: 2-sentence summary
      └── CTAs: [VIEW ON GITHUB →] [EXPLORE FEATURES ↓]

Why VIKO (story section, 2-column grid)
  ├── Left: heading + 3 paragraphs personal origin story
  └── Right: 3 stat blocks (20+ skills / 100% voice-first / Live)

Features (4×2 grid, 8 cards)
  ├── Real-time Voice, Futuristic HUD, Speaker Verification, Self-Modification
  └── Long-term Memory, 20+ Skills, Dev Agent, Live Location

Screenshots (3-column)
  ├── dashboard.png — "DASHBOARD — Live metrics & map"
  ├── text-chat.png — "TEXT CHAT — Conversation history"
  └── voice-chat.png — "VOICE CHAT — Audio visualizer"

GitHub CTA (centered)
  ├── Heading + subtext
  ├── Tech pills (Gemini Live, Claude Sonnet, PyQt6, etc.)
  └── Large GitHub button

Footer
  ├── Left: icon.png logo + VIKO wordmark
  ├── Center: nav links (GitHub, License, Docs) + eksant@gmail.com
  └── Right: "Proprietary · eksant · 2026"
```

---

## HUD Circle Animation

Rendered as inline SVG via JavaScript, redrawn every 40ms (~25fps):

| Element | Detail |
|---|---|
| Static rings | 10 concentric circles (r=34–188), cyan, varied dash patterns and opacity |
| Tick marks | 72 ticks on outer ring, major tick every 6th |
| Cardinal dots | 4 dots at N/E/S/W on r=158 |
| Amber arc | r=174, 80° sweep, **clockwise**, `#FFB347`, dot at leading tip |
| Counter arc | r=126, 55° sweep, **counter-clockwise**, `#FF6B35`, dot at trailing tip |
| Pulse waves | 3 expanding rings (phase offset 0/0.34/0.67), r: 22→342, fade to transparent |
| Center glow | Dashed ring + solid ring + 5px cyan dot |
| Labels | "SYSTEM TRACKING" top, "◦ STANDBY" bottom |

Pulse waves use `overflow="visible"` on the SVG so they expand beyond the HUD boundary into the full hero area.

---

## Animations

| Effect | Implementation |
|---|---|
| Voice bar | CSS `animation: vbar` on 9 `<span>` elements, alternating scaleY |
| HUD circle | `setInterval` 40ms, JS redraws SVG innerHTML |
| Amber arc | `amberAngle += 0.35°` per tick (clockwise) |
| Counter arc | `counterAngle -= 0.22°` per tick (counter-clockwise) |
| Pulse waves | `pulseT += 0.0035` per tick, ~11s full cycle |
| Scroll reveal | `IntersectionObserver` adds `.visible` class → CSS opacity/translateY transition |
| Hover effects | Feature cards, screenshot cards, nav links — CSS transitions |

---

## Responsive Breakpoints

| Breakpoint | Changes |
|---|---|
| ≤900px (tablet) | Features grid 2-col, screenshots 2-col, story single-col, hero content wider |
| ≤600px (mobile) | Hero stacks vertically, nav collapses to CTA only, all grids 1-col, buttons full-width, HUD circle faint texture |

---

## File Layout (after implementation)

```
viko-assistant/
├── index.html                        ← landing page entry point
├── assets/
│   ├── icon.png                      ← logo (existing)
│   └── landing/
│       ├── style.css                 ← all page styles
│       └── main.js                   ← HUD animation + scroll reveal
└── docs/
    └── screenshots/
        ├── dashboard.png             ← existing
        ├── text-chat.png             ← existing
        └── voice-chat.png            ← existing
```

---

## Out of Scope

- No blog, docs pages, or additional routes (single page only)
- No contact form — email link only
- No analytics or tracking
- No dark/light mode toggle
- GitHub Pages configuration (just push `index.html` to `main`)
