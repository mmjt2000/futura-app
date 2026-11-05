// Kit TP de Matemáticas : TP.lab({...}) construye gráfico + controles + carnet + retos.
(() => {
const $ = id => document.getElementById(id);
const h = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
const num = (n, d = 2) => { let v = +Number(n).toFixed(d); if (v === 0) v = 0; return String(v).replace('-', '−'); };
const sg = (n, d = 2) => (n < 0 ? '− ' : '+ ') + num(Math.abs(n), d);
const money = n => '$' + Math.round(n).toLocaleString('es-MX');
const nice = (r, t = 5) => { const raw = r / t, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; };
const tx = (ctx, s, x, y, col = '#fff', al = 'center', f = 'bold 12px sans-serif') => { ctx.fillStyle = col; ctx.textAlign = al; ctx.font = f; ctx.fillText(s, x, y); };
const dot = (ctx, x, y, r, col) => { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); };
const line = (ctx, x1, y1, x2, y2, col, w = 2, dash = []) => { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.setLineDash([]); };

function plane(ctx, W, H, o) {
  const l = o.lm ?? 36, r = W - 18, t = 18, b = H - 26;
  const X = x => l + (x - o.x0) / (o.x1 - o.x0) * (r - l), Y = y => b - (y - o.y0) / (o.y1 - o.y0) * (b - t);
  ctx.fillStyle = 'rgba(10,14,39,.6)'; ctx.fillRect(0, 0, W, H);
  const xf = o.xf || (v => num(v, 0)), yf = o.yf || (v => num(v, 0));
  for (let i = Math.ceil(o.x0 / o.xt - 1e-9); i * o.xt <= o.x1 + 1e-9; i++) line(ctx, X(i * o.xt), t, X(i * o.xt), b, 'rgba(255,255,255,.07)', 1);
  for (let i = Math.ceil(o.y0 / o.yt - 1e-9); i * o.yt <= o.y1 + 1e-9; i++) line(ctx, l, Y(i * o.yt), r, Y(i * o.yt), 'rgba(255,255,255,.07)', 1);
  const ax = o.x0 <= 0 && o.x1 >= 0 ? X(0) : l, ay = o.y0 <= 0 && o.y1 >= 0 ? Y(0) : b;
  line(ctx, l, ay, r, ay, 'rgba(255,255,255,.35)', 1.5); line(ctx, ax, t, ax, b, 'rgba(255,255,255,.35)', 1.5);
  const lab = 'rgba(255,255,255,.5)', f = '10px sans-serif';
  for (let i = Math.ceil(o.x0 / o.xt - 1e-9); i * o.xt <= o.x1 + 1e-9; i++) { const v = i * o.xt; if (Math.abs(v) > 1e-9 || ax === l) tx(ctx, xf(v), X(v), Math.min(ay + 13, b + 14), lab, 'center', f); }
  for (let i = Math.ceil(o.y0 / o.yt - 1e-9); i * o.yt <= o.y1 + 1e-9; i++) { const v = i * o.yt; if (Math.abs(v) > 1e-9 || ay === b) tx(ctx, yf(v), Math.max(ax - 5, l - 3), Y(v) + 3, lab, 'right', f); }
  if (o.xl) tx(ctx, o.xl, r - 4, ay - 8, '#94a3b8', 'right', '11px sans-serif');
  if (o.yl) tx(ctx, o.yl, ax + 8, t + 10, '#94a3b8', 'left', '11px sans-serif');
  return { X, Y, l, r, t, b, clip() { ctx.save(); ctx.beginPath(); ctx.rect(l, t, r - l, b - t); ctx.clip(); }, unclip() { ctx.restore(); } };
}

function lab(c) {
  const W = c.W || 500, H = c.H || 400, S = {}, inputs = {};
  const root = h('div', 'container');
  root.innerHTML = `<h1>${c.icon} ${c.title}</h1><div class="subtitle">${c.subtitle}</div>
  <div class="lab-layout"><div class="left-col"><div class="canvas-container"><canvas id="cv" role="img" aria-label="${c.alt}"></canvas></div><div class="controls" id="controls"></div></div>
  <div class="right-col"><h3>📓 CARNET DE CÁLCULO</h3><div id="carnet" aria-live="polite"></div></div></div>
  <div id="retos"></div><div class="bottom-panels">${(c.info || []).map(i => `<div class="info-box ${i.cls}"><h3>${i.title}</h3>${i.html}</div>`).join('')}</div>`;
  document.body.append(root);
  const cv = $('cv'), dpr = window.devicePixelRatio || 1, ctx = cv.getContext('2d'), box = $('controls');
  cv.width = W * dpr; cv.height = H * dpr;
  if (c.init) c.init(S);
  if (c.presets) {
    const row = h('div', 'presets');
    c.presets.forEach(p => { const b = h('button', 'chip-btn', p.label); b.type = 'button';
      b.onclick = () => { if (p.apply) p.apply(S); else for (const [k, v] of Object.entries(p.values)) { S[k] = v; inputs[k].value = v; } update(); }; row.append(b); });
    box.append(row);
  }
  (c.controls || []).forEach(d => {
    S[d.id] = d.value; const g = h('div', 'control-group'), l = h('label'), sp = h('span'), inp = h('input');
    l.setAttribute('for', 'r_' + d.id); l.innerHTML = '<span class="lt">' + d.label + '</span>'; sp.className = 'val'; l.append(sp);
    Object.assign(inp, { type: 'range', id: 'r_' + d.id, min: d.min, max: d.max, step: d.step, value: d.value });
    inp.addEventListener('input', () => { S[d.id] = parseFloat(inp.value); update(); });
    inputs[d.id] = inp; inp._sp = sp; inp._d = d; g.append(l, inp); box.append(g);
  });
  if (c.extra) c.extra(box, S, () => update());
  function update() {
    for (const k in inputs) { const i = inputs[k], d = i._d; i.value = S[k]; i._sp.textContent = (d.fmt ? d.fmt(S[k]) : num(S[k], d.dec ?? 1)) + (d.unit || ''); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const res = c.compute(S) || {};
    $('carnet').innerHTML = (res.steps || []).map(s => `<div class="calc-step"><div class="step-title">${s.t}</div>${s.html ? `<div>${s.html}</div>` : ''}${s.f ? `<div class="formula ${s.cls || ''}">${s.f}</div>` : ''}${s.r ? `<span class="result-big ${s.cls || ''}">${s.r}</span>` : ''}</div>`).join('');
    c.draw(ctx, S, res, { W, H });
    if (c.onUpdate) c.onUpdate(S, res, () => update());
    if (c.retos) {
      const done = c.retos.map(r => !!r.check(S, res));
      $('retos').innerHTML = `<div class="reto"><h3>🎯 RETOS</h3>${c.retos.map((r, i) => `<div class="reto-item ${done[i] ? 'ok' : ''}">${done[i] ? '✅' : '⬜'} ${r.text}</div>`).join('')}${done.every(Boolean) ? '<div class="reto-win">🎉 ¡Completaste todos los retos!</div>' : ''}</div>`;
    }
  }
  update();
}
window.TP = { $, h, num, sg, money, nice, tx, dot, line, plane, lab };
})();
