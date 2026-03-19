// comun.js — header, nav y utilidades compartidas entre pantallas PC

function initHeader() {
  const op = JSON.parse(localStorage.getItem('operario') || 'null');
  if (!op) { window.location.href = '/'; return null; }
  const ini = op.nombre.split(' ').map(p => p[0]).join('').slice(0,2).toUpperCase();
  const av = document.getElementById('avatar');
  const nm = document.getElementById('op-nombre');
  if (av) av.textContent = ini;
  if (nm) nm.textContent = op.nombre;
  return op;
}

function logout() { localStorage.clear(); window.location.href = '/'; }

function fmt(n) {
  return Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function showMsg(id, texto, tipo) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'msg msg-' + tipo;
  el.textContent = texto;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 3500);
}

function ordenarTabla(datos, col, dir) {
  return [...datos].sort((a, b) => {
    const va = a[col] ?? '', vb = b[col] ?? '';
    if (typeof va === 'number') return (va - vb) * dir;
    return String(va).localeCompare(String(vb), 'es') * dir;
  });
}

// ── Campos extra dinámicos ────────────────────────────────────────────────────

async function cargarCamposExtra(tabla) {
  return await fetch(`/api/campos_extra/${tabla}`).then(r => r.json());
}

function renderCamposExtra(campos, valores) {
  if (!campos || !campos.length) return '';
  return campos.map(c => {
    const val = (valores && valores[c.nombre]) || '';
    const label = `<label>${c.etiqueta} <span style="font-size:10px;color:#9ca3af">${c.tipo_campo==='fijo'?'fijo':'volátil'}</span></label>`;
    let input = '';
    if (c.tipo === 'lista' && c.opciones) {
      const opts = c.opciones.split(',').map(o => o.trim());
      input = `<select id="ex-${c.nombre}">
        <option value="">— seleccionar —</option>
        ${opts.map(o => `<option value="${o}" ${val===o?'selected':''}>${o}</option>`).join('')}
      </select>`;
    } else if (c.tipo === 'numero') {
      input = `<input id="ex-${c.nombre}" type="number" step="any" value="${val}" placeholder="0">`;
    } else if (c.tipo === 'fecha') {
      input = `<input id="ex-${c.nombre}" type="date" value="${val}">`;
    } else {
      input = `<input id="ex-${c.nombre}" type="text" value="${val}" placeholder="${c.etiqueta}">`;
    }
    return `<div class="campo">${label}${input}</div>`;
  }).join('');
}

function recogerCamposExtra(campos) {
  const result = {};
  (campos || []).forEach(c => {
    const el = document.getElementById(`ex-${c.nombre}`);
    if (el) result[c.nombre] = el.value;
  });
  return result;
}

// ── Perfiles genéricos (API helpers) ─────────────────────────────────────────

async function apiCargarPerfiles(pantalla, operario_id) {
  return await fetch(`/api/perfiles/${pantalla}?operario_id=${operario_id}`).then(r => r.json());
}

async function apiCrearPerfil(pantalla, operario_id, nombre, config) {
  return await fetch('/api/perfiles', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pantalla, operario_id, nombre, config})
  }).then(r => r.json());
}

async function apiActualizarPerfil(perfil_id, pantalla, operario_id, nombre, config) {
  return await fetch(`/api/perfiles/${perfil_id}`, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pantalla, operario_id, nombre, config})
  }).then(r => r.json());
}

async function apiBorrarPerfil(perfil_id) {
  return await fetch(`/api/perfiles/${perfil_id}`, {method: 'DELETE'}).then(r => r.json());
}

// Rellena el <select id="perfil-select"> con los perfiles cargados
function renderSelectPerfiles(perfiles, activo_id) {
  const sel = document.getElementById('perfil-select');
  if (!sel) return;
  sel.innerHTML = '<option value="">— sin perfil —</option>' +
    perfiles.map(p => `<option value="${p.id}">${p.nombre}</option>`).join('');
  if (activo_id) sel.value = activo_id;
}

// ── Nav dinámica ───────────────────────────────────────────────────────────────
// Sustituye el bloque <nav> hardcodeado. Llama al final de initHeader().
// Requiere un elemento <nav id="nav-dinamica"> en el HTML.
async function renderNavDinamica() {
  const nav = document.getElementById('nav-dinamica');
  if (!nav) return;
  const path = window.location.pathname;

  let tablas = [];
  try {
    tablas = await fetch('/api/tablas?en_nav=1').then(r => r.json());
  } catch(e) { console.warn('Nav: error cargando tablas', e); }

  const link = (href, label) => {
    const active = (path === href || (href !== '/' && path.startsWith(href))) ? ' class="active"' : '';
    return `<a href="${href}"${active}>${label}</a>`;
  };

  let html = link('/ventas', 'Nueva venta');
  html += link('/consultas', 'Consultas');
  html += '<span class="nav-sep">|</span>';

  tablas.forEach(t => {
    const ruta = t.ruta || t.nombre;
    html += link(`/${ruta}`, t.etiqueta);
  });

  html += '<span class="nav-sep">|</span>';
  html += link('/configuracion', '&#9881;&#65039; Config');

  nav.innerHTML = html;
}

// Versión estática de la nav (para páginas que no han migrado al sistema dinámico)
function navEstaticaActiva() {
  const path = window.location.pathname;
  document.querySelectorAll('nav.nav-links a, nav#nav-dinamica a').forEach(a => {
    const href = a.getAttribute('href');
    if (href && (path === href || (href.length > 1 && path.startsWith(href)))) {
      a.classList.add('active');
    }
  });
}
