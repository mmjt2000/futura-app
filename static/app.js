// Futura : SPA vanilla. Tout le contenu affiché est construit via textContent (pas d'innerHTML).
const $ = (s, r = document) => r.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  e.append(...kids.flat());
  return e;
};
const api = async (path, opt = {}) => {
  const r = await fetch('/api' + path, { ...opt, headers: { ...(opt.headers || {}), ...(S.token ? { 'X-Futura-Token': S.token } : {}) } });
  if (!r.ok) {
    const msg = (await r.json().catch(() => ({}))).detail || 'Error de conexión';
    if (r.status === 401 && path !== '/login') { sessionStorage.removeItem('futura:token:' + S.user); S.token = null; S.user = null; pickUser(); }
    throw new Error(msg);
  }
  return r.json();
};
const post = (p, body) => api(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const toast = msg => { const t = h('div', { class: 'toast', role: 'status' }, msg); document.body.append(t); setTimeout(() => t.remove(), 3000); };

const STEPS = ['Contexto', 'Khan Academy', 'Laboratorio', 'Carnet PISA', 'Ejercicios', 'Metacognición'];

// --- BADGES ---
const MAX_XP = 480;
const BADGES = {
  "Exploradora": { icon: "🧭", min: 0 },
  "Aprendiz": { icon: "📘", min: 15 },
  "Creadora": { icon: "🎨", min: 35 },
  "Innovadora": { icon: "🚀", min: 60 },
  "Future Leader": { icon: "👑", min: 85 }
};

function getBadge(xp) {
  const percent = (xp / MAX_XP) * 100;
  let current = "Exploradora", next = "Aprendiz";
  if (percent >= 85) { current = "Future Leader"; next = null; }
  else if (percent >= 60) { current = "Innovadora"; next = "Future Leader"; }
  else if (percent >= 35) { current = "Creadora"; next = "Innovadora"; }
  else if (percent >= 15) { current = "Aprendiz"; next = "Creadora"; }
  
  return {
    current,
    icon: BADGES[current].icon,
    next,
    nextIcon: next ? BADGES[next].icon : null,
    percent: Math.min(percent, 100),
    nextPercent: next ? BADGES[next].min : null
  };
}

const S = { user: localStorage.getItem('futura:user'), users: [], p: null, step: 0, token: null };
S.token = S.user ? sessionStorage.getItem('futura:token:' + S.user) : null;
const app = $('#app');

function header() {
  const me = S.users.find(u => u.name === S.user);
  if (!me) {
    $('#who').replaceChildren();
    return;
  }
  const badge = getBadge(me.xp);
  $('#who').replaceChildren(
    h('span', { style: 'margin-right: 10px;' }, `${me.name} · ${badge.icon} ${me.xp} XP`),
    h('button', { 
      style: 'padding: 5px 10px; font-size: 0.9rem;',
      onclick: () => { 
        localStorage.removeItem('futura:user'); 
        sessionStorage.clear();
        S.user = null; 
        S.token = null; 
        pickUser(); 
      } 
    }, 'Cambiar')
  );
}

async function refreshUsers() { S.users = await api('/users'); header(); }

function pickUser() {
  header();
  app.replaceChildren(
    h('h1', {}, '¿Quién va a aprender hoy?'),
    ...S.users.map(u => {
      const badge = getBadge(u.xp);
      return h('button', { 
        class: 'primary', 
        style: 'margin:6px', 
        onclick: () => enter(u) 
      }, `${u.name} · ${badge.icon} ${badge.current} (${u.xp} XP)` + (u.has_pin ? ' 🔒' : ''));
    })
  );
}

function enter(u) {
  if (u.has_pin) return showPin(u);
  S.user = u.name; S.token = null; localStorage.setItem('futura:user', u.name); home();
}

function showPin(u) {
  const input = h('input', { type: 'password', inputmode: 'numeric', autocomplete: 'off', maxlength: '8', placeholder: 'PIN', 'aria-label': 'PIN', style: 'max-width:180px;text-align:center;font-size:1.4rem;letter-spacing:.3em' });
  const msg = h('p', { class: 'muted', role: 'alert' });
  const go = async () => {
    try { const r = await post('/login', { user: u.name, pin: input.value }); S.user = u.name; S.token = r.token; sessionStorage.setItem('futura:token:' + u.name, r.token); localStorage.setItem('futura:user', u.name); home(); }
    catch (e) { msg.textContent = e.message; input.value = ''; input.focus(); }
  };
  input.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
  app.replaceChildren(h('h1', {}, `Hola, ${u.name} 👋`), h('p', { class: 'muted' }, 'Escribe tu PIN para entrar.'), input,
    h('div', {}, h('button', { class: 'primary', onclick: go }, 'Entrar'), h('button', { onclick: pickUser }, 'Volver')), msg);
  input.focus();
}

const CATS = [
  ['mat_', '🧮 Matemáticas'], 
  ['bio_', '🌿 Biología'], 
  ['qui_', '🧪 Química'], 
  ['fis_', '⚛️ Física']
];

async function showHermanas() {
  app.replaceChildren(h('p', { class: 'muted' }, 'Cargando...'));
  try {
    const users = await api('/users');
    const me = users.find(u => u.name === S.user);
    const other = users.find(u => u.name !== S.user);
    
    if (!other) {
      app.replaceChildren(h('h1', {}, 'No hay otra hermana registrada'));
      return;
    }

    const myBadge = getBadge(me.xp);
    const otherBadge = getBadge(other.xp);
    const diff = Math.abs(me.xp - other.xp);

    const makeCard = (user, badge, isMe) => h('div', { 
      class: 'card', 
      style: `text-align:center; ${isMe ? 'border: 2px solid #4de0c1;' : ''}` 
    },
      h('h2', { style: 'font-size: 2rem; margin: 10px 0;' }, isMe ? '👤' : '👧'),
      h('h3', {}, user.name),
      h('p', { style: 'font-size: 1.5rem; font-weight: bold; color: #f59e0b; margin: 10px 0;' }, `⭐ ${user.xp} XP`),
      h('p', { style: 'font-size: 1.2rem;' }, `${badge.icon} ${badge.current}`),
      h('div', { style: 'width:100%; background:#0b0d1a; height:8px; border-radius:4px; margin-top:15px; overflow:hidden;' },
        h('div', { style: `width:${badge.percent}%; background:#4de0c1; height:100%;` })
      )
    );

    app.replaceChildren(
      h('button', { onclick: home, style: 'margin-bottom: 20px;' }, '← Volver al inicio'),
      h('h1', { style: 'text-align: center;' }, '👭 El duelo de las hermanas'),
      h('div', { class: 'grid', style: 'grid-template-columns: 1fr 1fr;' },
        makeCard(me, myBadge, true),
        makeCard(other, otherBadge, false)
      ),
      h('div', { class: 'card', style: 'text-align:center; margin-top: 20px; background: #2b2410; border-color: #f59e0b;' },
        h('h3', {}, diff === 0 ? '¡Están empatadas! 🤝' : `${me.xp > other.xp ? other.name : me.name} va adelante por ${diff} XP`),
        h('p', { class: 'muted' }, diff === 0 ? 'Sigan así, ¡van juntas!' : '¡Aún queda tiempo para alcanzar a la otra!')
      )
    );
  } catch (e) {
    app.replaceChildren(h('p', { style: 'color: red;' }, e.message));
  }
}

async function showDiario() {
  app.replaceChildren(h('p', { class: 'muted' }, 'Cargando tu diario...'));
  try {
    const list = await api('/parcours?user=' + encodeURIComponent(S.user));
    
    const cards = list.map(p => {
      const responses = [];
      for (let i = 0; i < 4; i++) {
        const r = localStorage.getItem(`carnet:${S.user}:${p.id}:${i}`);
        if (r && r.trim()) responses.push({ index: i, text: r });
      }
      if (responses.length === 0) return null;
      
      return h('div', { class: 'card', style: 'margin-bottom: 15px;' },
        h('h3', { style: 'color: #4de0c1;' }, p.title),
        ...responses.map(r => h('div', { class: 'refl', style: 'margin-top: 10px; border-left: 3px solid #4de0c1; padding-left: 10px;' },
          h('b', {}, `Pregunta ${r.index + 1}: `),
          h('span', { class: 'muted' }, r.text)
        ))
      );
    }).filter(Boolean);

    if (cards.length === 0) {
      app.replaceChildren(
        h('button', { onclick: home, style: 'margin-bottom: 20px;' }, '← Volver al inicio'),
        h('h1', {}, '📓 Mi diario de aprendizaje'),
        h('p', { class: 'muted' }, 'Aún no has escrito nada. ¡Empieza un parcours para llenar tu diario!')
      );
    } else {
      app.replaceChildren(
        h('button', { onclick: home, style: 'margin-bottom: 20px;' }, '← Volver al inicio'),
        h('h1', {}, '📓 Mi diario de aprendizaje'),
        h('p', { class: 'muted' }, 'Aquí están todas tus reflexiones. ¡Mira cuánto has aprendido!'),
        ...cards
      );
    }
  } catch (e) {
    app.replaceChildren(h('p', { style: 'color: red;' }, e.message));
  }
}

async function home() {
  header();
  const list = await api('/parcours?user=' + encodeURIComponent(S.user));
  
  const me = S.users.find(u => u.name === S.user);
  const badge = getBadge(me.xp);
  
  const banner = h('div', { 
    class: 'card', 
    style: 'display:flex; justify-content:space-between; align-items:center; background:#2b2410; border:1px solid #f59e0b; margin-bottom:20px;' 
  },
    h('div', {},
      h('b', { style: 'font-size:1.1rem;' }, `${badge.icon} ${badge.current}`),
      badge.next ? h('span', { class: 'muted', style: 'display:block; font-size:0.85rem; margin-top:4px;' }, 
        `Próximo: ${badge.nextIcon} ${badge.next} al ${badge.nextPercent}%`) : h('span', { class: 'muted', style: 'display:block; font-size:0.85rem; margin-top:4px;' }, '¡Nivel máximo alcanzado!')
    ),
    h('div', { style: 'width:150px; text-align:right;' },
      h('div', { style: 'background:#0b0d1a; height:12px; border-radius:6px; overflow:hidden; border:1px solid #444;' },
        h('div', { style: `width:${badge.percent}%; background:#f59e0b; height:100%; transition:width 0.5s ease;` })
      ),
      h('span', { class: 'muted', style: 'font-size:0.75rem;' }, `${Math.round(badge.percent)}%`)
    )
  );

  const card = p => h('div', { class: 'card' }, h('h3', {}, p.title),
    h('p', { class: 'muted' }, `${p.done ? '✅ Completado' : `${p.solved}/4 ejercicios`} · ${p.xp_reward} XP`),
    h('button', { class: 'primary', onclick: () => openParcours(p.id) }, p.done ? 'Repasar' : 'Empezar'));

  app.replaceChildren(
    h('div', { class: 'row', style: 'justify-content:space-between; align-items:center; margin-bottom: 10px;' },
      h('h1', { style: 'margin:0;' }, `¡Hola, ${S.user}!`),
      h('div', {},
        h('button', { onclick: showHermanas, style: 'margin-right: 10px;' }, '👭 Ver a mi hermana'),
        h('button', { onclick: showDiario, class: 'primary' }, '📓 Mi diario')
      )
    ),
    banner,
    h('p', { class: 'muted' }, 'Elige un parcours para aprender aplicando.'),
    ...CATS.flatMap(([prefix, label]) => {
      const items = list.filter(p => p.id.startsWith(prefix));
      return items.length ? [h('h2', { class: 'cat' }, label), h('div', { class: 'grid' }, items.map(card))] : [];
    })
  );
}

async function openParcours(id) {
  S.p = await api(`/parcours/${id}?user=${encodeURIComponent(S.user)}`);
  S.step = 0; render();
}

const svgNS = 'http://www.w3.org/2000/svg';
const sv = (tag, attrs = {}, text) => { const e = document.createElementNS(svgNS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); if (text != null) e.textContent = text; return e; };
function wrap2(s) { if (s.length <= 18) return [s]; const mid = s.length / 2; let best = -1; [...s].forEach((c, i) => { if (c === ' ' && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))) best = i; }); return best < 0 ? [s] : [s.slice(0, best), s.slice(best + 1)]; }

function mindMap(title, nodes) {
  const COL = ['#38bdf8', '#f472b6', '#4de0c1', '#f59e0b', '#a78bfa', '#fb7185'], cx = 320, cy = 190, n = nodes.length;
  const svg = sv('svg', { viewBox: '0 0 640 380', role: 'img', 'aria-label': 'Mapa mental: ' + nodes.join(', '), class: 'mmap' });
  const pos = nodes.map((_, i) => { const a = (-90 + i * 360 / n) * Math.PI / 180; return [cx + 225 * Math.cos(a), cy + 140 * Math.sin(a)]; });
  pos.forEach(([x, y], i) => svg.append(sv('path', { d: `M${cx} ${cy} Q${(cx + x) / 2} ${(cy + y) / 2 - 18} ${x} ${y}`, stroke: COL[i % COL.length], 'stroke-width': 3, fill: 'none', opacity: .7 })));
  svg.append(sv('ellipse', { cx, cy, rx: 100, ry: 42, fill: '#1f2a4a', stroke: '#4de0c1', 'stroke-width': 3 }));
  wrap2(title).forEach((l, i, a) => svg.append(sv('text', { x: cx, y: cy + 5 + (i - (a.length - 1) / 2) * 17, 'text-anchor': 'middle', fill: '#fff', 'font-weight': 700, 'font-size': 14 }, l)));
  nodes.forEach((t, i) => { const [x, y] = pos[i], c = COL[i % COL.length], lines = wrap2(t);
    svg.append(sv('rect', { x: x - 78, y: y - 24, width: 156, height: 48, rx: 12, fill: c + '22', stroke: c, 'stroke-width': 2.5 }));
    lines.forEach((l, j) => svg.append(sv('text', { x, y: y + 4 + (j - (lines.length - 1) / 2) * 15, 'text-anchor': 'middle', fill: '#e8eaf6', 'font-size': 12.5, 'font-weight': 600 }, l))); });
  return svg;
}

function repaso() {
  const r = S.p.revision;
  if (!r) return h('div', { class: 'card' }, 'Pronto habrá un repaso visual para este parcours.');
  const key = `repaso:${S.user}:${S.p.id}`; let known = new Set(); try { known = new Set(JSON.parse(localStorage.getItem(key) || '[]')); } catch { }
  const prog = h('p', { class: 'muted' }), upd = () => { prog.textContent = `Tarjetas dominadas: ${known.size} de ${r.tarjetas.length}`; try { localStorage.setItem(key, JSON.stringify([...known])); } catch { } };
  const cards = r.tarjetas.map((t, i) => {
    const card = h('div', { class: 'flip' + (known.has(i) ? ' known' : ''), tabindex: '0', role: 'button', 'aria-label': 'Tarjeta de repaso: ' + t.q });
    const mark = (ok) => ev => { ev.stopPropagation(); ok ? known.add(i) : known.delete(i); card.classList.toggle('known', ok); card.classList.remove('open'); upd(); };
    card.append(h('div', { class: 'face front' }, h('span', { class: 'lvl' }, 'Pregunta'), h('p', {}, t.q), h('span', { class: 'muted' }, 'Toca para ver la respuesta')),
      h('div', { class: 'face back' }, h('span', { class: 'lvl' }, 'Respuesta'), h('p', {}, t.a), h('div', {}, h('button', { class: 'primary', onclick: mark(true) }, '✅ La sabía'), h('button', { onclick: mark(false) }, '🔁 Repasar'))));
    const toggle = () => card.classList.toggle('open'); card.addEventListener('click', toggle);
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }); return card; });
  upd();
  return h('div', { class: 'repaso' },
    h('div', { class: 'idea' }, '💡 ', h('b', {}, 'Idea clave: '), r.idea),
    h('div', { class: 'card' }, h('h2', {}, '🗺️ Mapa mental'), mindMap(S.p.title.split(':')[0], r.mapa)),
    h('div', { class: 'card' }, h('h2', {}, '📐 Fórmulas y reglas'), h('div', { class: 'grid' }, r.formulas.map(f => h('div', { class: 'fcard' }, h('span', { class: 'muted' }, f.t), h('code', {}, f.f))))),
    h('div', { class: 'card' }, h('h2', {}, '🧠 Astucias para recordar'), h('ul', { class: 'tips' }, r.astucias.map(a => h('li', {}, a)))),
    h('div', { class: 'card err' }, h('h2', {}, '⚠️ Errores comunes'), h('ul', { class: 'tips' }, r.errores.map(a => h('li', {}, a)))),
    h('div', { class: 'card' }, h('h2', {}, '🃏 Tarjetas de repaso'), prog, h('div', { class: 'grid' }, cards)),
    h('button', { class: 'noprint', onclick: () => window.print() }, '🖨️ Imprimir esta ficha'));
}

function render() {
  const p = S.p, views = [ctx, khan, labo, carnet, ejercicios, meta], rev = S.step === -1;
  app.replaceChildren(
    h('div', { class: 'row', style: 'justify-content:space-between' }, h('button', { onclick: home }, '← Mis parcours'),
      h('button', { class: rev ? 'primary' : '', onclick: () => { S.step = rev ? 0 : -1; render(); } }, rev ? '← Volver al parcours' : '📚 Repaso visual')), h('h1', {}, p.title),
    h('nav', { class: 'steps', 'aria-label': 'Etapas' }, STEPS.map((n, i) =>
      h('button', { class: i === S.step ? 'on' : '', 'aria-current': i === S.step ? 'step' : 'false', onclick: () => { S.step = i; render(); } }, `${i + 1}. ${n}`))),
    rev ? repaso() : views[S.step](),
    rev ? h('span') : h('div', { class: 'nav' },
      h('button', { disabled: S.step === 0 ? '' : null, onclick: () => { S.step--; render(); } }, '← Anterior'),
      S.step < 5 ? h('button', { class: 'primary', onclick: () => { S.step++; render(); } }, 'Siguiente →') : h('span')));
}

const ctx = () => {
  const c = S.p.contexte, msg = h('span', { class: 'muted' }), pred = h('textarea', { rows: 3, id: 'pred', maxlength: '600', placeholder: 'Escribe tu predicción…' });
  pred.value = S.p.prediction || ''; let timer;
  const save = async () => { if (pred.value.trim() === (S.p.prediction || '').trim()) return; try { await post(`/parcours/${S.p.id}/prediction`, { user: S.user, text: pred.value }); S.p.prediction = pred.value.trim(); msg.textContent = ' ✔ guardada'; } catch (e) { msg.textContent = ' ' + e.message; } };
  pred.addEventListener('input', () => { msg.textContent = ''; clearTimeout(timer); timer = setTimeout(save, 900); });
  pred.addEventListener('blur', () => { clearTimeout(timer); save(); });
  return h('div', {},
    h('div', { class: 'card' }, h('h2', {}, c.titre), h('p', {}, c.texte)),
    h('div', { class: 'idea prob' }, '🎯 ', h('b', {}, 'El problema: '), c.problema),
    c.dato ? h('div', { class: 'card' }, h('h3', {}, '📊 ' + c.dato.titulo), h('table', { class: 'tbl' }, h('tbody', {}, c.dato.filas.map(f => h('tr', {}, h('td', {}, f[0]), h('td', {}, f[1])))))) : '',
    h('div', { class: 'card' }, h('h2', {}, '🔮 Tu predicción'), h('p', { class: 'quote' }, c.question_reflexion),
      h('label', { for: 'pred', class: 'muted' }, 'Aquí no hay respuestas incorrectas: escribe lo que crees ahora y lo compararás al final.'), pred, msg),
    h('p', { class: 'muted' }, '✨ ', c.meta));
};

const khan = () => h('div', { class: 'card' }, h('h2', {}, 'Teoría en Khan Academy'),
  h('p', {}, S.p.khan.skill), h('p', { class: 'muted' }, `⏱ ${S.p.khan.estimated_minutes} min aprox.`),
  h('a', { class: 'btn primary', href: S.p.khan.link, target: '_blank', rel: 'noopener noreferrer' }, 'Abrir lección ↗'));

const labo = () => {
  const iframe = h('iframe', { 
    src: '/' + S.p.labo.file, 
    sandbox: 'allow-scripts', 
    title: 'Laboratorio interactivo', 
    loading: 'lazy',
    id: 'labo-frame',
    style: 'width:100%; height:80vh; border:none; border-radius:14px;'
  });

  const fullscreen = () => {
    if (iframe.requestFullscreen) {
      iframe.requestFullscreen();
    } else if (iframe.webkitRequestFullscreen) {
      iframe.webkitRequestFullscreen();
    } else if (iframe.msRequestFullscreen) {
      iframe.msRequestFullscreen();
    }
  };

  return h('div', {}, 
    h('div', { class: 'card' }, 
      h('div', { style: 'display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;' },
        h('div', {},
          h('h2', { style: 'margin:0;' }, 'Laboratorio interactivo'), 
          h('p', { class: 'muted', style: 'margin:4px 0 0;' }, S.p.labo.objective)
        ),
        h('button', { class: 'primary', onclick: fullscreen, style: 'white-space:nowrap;' }, '⛶ Pantalla completa')
      )
    ),
    h('div', { style: 'margin-top:20px;' }, iframe)
  );
};

function carnet() {
  return h('div', {}, h('p', { class: 'muted' }, 'Tus respuestas se guardan en este dispositivo mientras escribes.'),
    ...S.p.carnet.map((c, i) => {
      const key = `carnet:${S.user}:${S.p.id}:${i}`;
      const ta = h('textarea', { rows: 4, id: 'c' + i, placeholder: 'Escribe tu respuesta…' });
      ta.value = localStorage.getItem(key) || '';
      
      let timer;
      ta.addEventListener('input', () => {
        localStorage.setItem(key, ta.value);
        clearTimeout(timer);
        timer = setTimeout(async () => {
          const all = S.p.carnet.map((_, j) => localStorage.getItem(`carnet:${S.user}:${S.p.id}:${j}`) || '');
          try {
            await post(`/parcours/${S.p.id}/carnet`, { user: S.user, carnet_json: JSON.stringify(all) });
          } catch (e) { /* Silencieux */ }
        }, 1000);
      });
      
      return h('div', { class: 'card' }, h('span', { class: 'lvl' }, c.process), h('label', { for: 'c' + i }, h('p', {}, c.question)), ta);
    }));
}

function ejercicios() {
  return h('div', {}, ...S.p.exercises.map(ex => {
    const long = ex.level === 4, solved = S.p.solved.includes(ex.id);
    const input = long ? h('textarea', { rows: 6, placeholder: 'Escribe un párrafo argumentado…', 'aria-label': 'Tu respuesta' })
                       : h('input', { type: 'text', autocomplete: 'off', placeholder: 'Tu respuesta', 'aria-label': 'Tu respuesta' });
    const out = h('div', { class: 'fb', role: 'status' });
    const btn = h('button', { class: 'primary' }, 'Comprobar');
    if (solved) { input.disabled = true; btn.remove(); out.className = 'fb ok'; out.textContent = '✅ Ya resuelto'; }
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const r = await post(`/parcours/${S.p.id}/exercises/${ex.id}/check`, { user: S.user, answer: input.value });
        out.className = 'fb ' + (r.correct ? 'ok' : 'ko'); out.textContent = r.feedback;
        if (r.model_answer) out.append(h('p', {}, h('strong', {}, 'Respuesta modelo: '), r.model_answer));
        if (r.correct) { S.p.solved.push(ex.id); input.disabled = true; btn.remove(); } else btn.disabled = false;
        if (r.xp_awarded) { toast(`+${r.xp_awarded} XP 🎉`); refreshUsers(); }
      } catch (e) { out.className = 'fb ko'; out.textContent = e.message; btn.disabled = false; }
    });
    return h('div', { class: 'card' }, h('span', { class: 'lvl' }, `Nivel ${ex.level}`), h('p', {}, ex.question), input, btn, out);
  }));
}

function meta() {
  let conf = 0, res = null;
  const comment = h('textarea', { rows: 4, id: 'mc', placeholder: '¿Qué fue lo más difícil? ¿Qué harás distinto la próxima vez?' });
  const btn = h('button', { class: 'primary', disabled: '' }, 'Guardar reflexión');
  const rate = h('div', { class: 'rate', role: 'group', 'aria-label': 'Confianza de 1 a 5' }, [1, 2, 3, 4, 5].map(n =>
    h('button', { onclick: () => { conf = n; [...rate.children].forEach((b, i) => b.classList.toggle('on', i < n)); btn.removeAttribute('disabled'); } }, `${n} ★`)));
  const resBox = h('div', { class: 'rate', role: 'group', 'aria-label': 'Resultado de tu predicción' }, [['acerte', '✅ Era correcta'], ['casi', '🤏 Me acerqué'], ['cambie', '🔄 Era distinta']].map(([k, t]) =>
    h('button', { onclick: ev => { res = k; [...resBox.children].forEach(b => b.classList.toggle('on', b === ev.currentTarget)); } }, t)));
  btn.addEventListener('click', async () => {
    try { await post(`/parcours/${S.p.id}/metacognition`, { user: S.user, confidence: conf, comment: comment.value, prediction_result: res }); toast('¡Reflexión guardada!'); setTimeout(home, 1200); }
    catch (e) { toast(e.message); }
  });
  const pred = S.p.prediction;
  return h('div', { class: 'card' }, h('h2', {}, 'Autoevaluación'), h('h3', {}, '🔮 Tu predicción del principio'),
    pred ? h('p', { class: 'quote' }, '« ' + pred + ' »') : h('p', { class: 'muted' }, 'No escribiste una predicción al empezar. La próxima vez, hazla en «1. Contexto» y la compararás aquí.'),
    pred ? h('p', {}, 'Ahora que terminaste el parcours, ¿cómo fue tu predicción?') : '', pred ? resBox : '',
    h('p', {}, '¿Qué tan seguro/a te sientes con este tema? (1 = nada, 5 = puedo explicárselo a alguien)'), rate,
    h('label', { for: 'mc' }, 'Tu reflexión'), comment, btn);
}

document.addEventListener('click', e => { if (e.target.id === 'logo') { e.preventDefault(); S.user ? home() : pickUser(); } });
(async () => {
  try { await refreshUsers(); } catch { app.textContent = 'Sin conexión con el servidor.'; return; }
  const me = S.users.find(u => u.name === S.user);
  if (!me || (me.has_pin && !S.token)) S.user = null;
  S.user ? home() : pickUser();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
})();