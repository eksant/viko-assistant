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
  const hudInterval = setInterval(() => {
    amberAngle   = (amberAngle + 0.35) % 360;
    counterAngle = (counterAngle - 0.22 + 360) % 360;
    pulseT       = (pulseT + 0.0035) % 1;
    drawHUD(amberAngle, counterAngle, pulseT);
  }, 40);
  window.addEventListener('beforeunload', () => clearInterval(hudInterval));
}());

// ── Scroll reveal ────────────────────────────────────────────────────────────
(function () {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); } }),
    { threshold: 0.1 }
  );
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}());
