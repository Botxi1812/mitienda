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
    const label = `<label>${c.etiqueta} <span style="font-size:10px;color:#9ca3af">${c.es_principal?'principal':'json'}</span></label>`;
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

  let html = link('/ventas', 'Ventas');
  html += link('/nueva-venta', 'Nueva venta');
  html += '<span class="nav-sep">|</span>';

  tablas.forEach(t => {
    const ruta = t.ruta || t.nombre;
    html += link(`/${ruta}`, t.etiqueta);
  });

  html += '<span class="nav-sep">|</span>';
  html += link('/configuracion', '&#9881;&#65039; Config');

  nav.innerHTML = html;
}

// ── MiTabla: cabecera interactiva con resize, reorder, sort y filtro por columna ──
//
// Uso:
//   const mt = new MiTabla({ cols, anchos, onSort, onReorder, onResize, onFilter })
//   mt.renderCabecera(theadEl, colgroupEl)
//
// cols: [{k, l}]  — clave y etiqueta de cada columna
// sortCol/sortDir — columna y dirección actuales
// onSort(k)       — callback al hacer click en etiqueta
// onReorder(cols) — callback cuando el usuario reordena (recibe array nuevo)
// onResize(k, px) — callback cuando cambia el ancho
// onFilter(k, v)  — callback cuando cambia el filtro de una columna
// datosFilas      — array de filas (para los valores únicos del filtro desplegable)

class MiTabla {
  constructor({ cols, anchos = {}, anchoDefault = 120, sortCol = null, sortDir = 1,
                onSort, onReorder, onResize, onFilter, datosFilas = [] }) {
    this.cols        = cols;           // [{k, l}]
    this.anchos      = anchos;         // {k: px}
    this.anchoDefault = anchoDefault;
    this.sortCol     = sortCol;
    this.sortDir     = sortDir;
    this.onSort      = onSort   || (() => {});
    this.onReorder   = onReorder || (() => {});
    this.onResize    = onResize  || (() => {});
    this.onFilter    = onFilter  || (() => {});
    this.datosFilas  = datosFilas;
    this.filtros     = {};             // {k: valor_filtro}

    this._resizingCol  = null;
    this._resizeStartX = 0;
    this._resizeStartW = 0;
    this._dragFrom     = null;
    this._openFilter   = null;

    this._onMouseMove = this._onMouseMove.bind(this);
    this._onMouseUp   = this._onMouseUp.bind(this);
    this._closeFilter = this._closeFilter.bind(this);
  }

  ancho(k) { return this.anchos[k] || this.anchoDefault; }

  renderCabecera(thead, colgroup) {
    // colgroup
    colgroup.innerHTML = this.cols.map(c => `<col style="width:${this.ancho(c.k)}px">`).join('');

    // thead
    thead.innerHTML = '<tr>' + this.cols.map((c, i) => {
      const sortMark = this.sortCol === c.k ? (this.sortDir > 0 ? ' ▲' : ' ▼') : '';
      const hasFilter = this.filtros[c.k];
      const filterMark = hasFilter ? ` <span style="color:#fbbf24;font-size:10px">▼</span>` : '';
      return `<th data-mt-col="${c.k}" style="position:relative;user-select:none;white-space:nowrap;overflow:visible"
          draggable="true"
          ondragstart="event.dataTransfer.setData('mt-col','${c.k}')"
          ondragover="event.preventDefault()"
          ondrop="window.__mt&&window.__mt._drop(event,'${c.k}')">
        <span class="mt-label" data-mt-sort="${c.k}" style="cursor:pointer">${c.l}${sortMark}${filterMark}</span>
        <span class="mt-filter-btn" data-mt-filter="${c.k}"
          style="cursor:pointer;padding:0 3px;opacity:.7;font-size:11px" title="Filtrar">&#9660;</span>
        <div class="mt-resize" data-mt-resize="${c.k}"
          style="position:absolute;right:0;top:0;width:5px;height:100%;cursor:col-resize;background:rgba(255,255,255,.15)"></div>
      </th>`;
    }).join('') + '</tr>';

    // Eventos en el thead (delegación)
    thead.onclick   = e => {
      const sort = e.target.closest('[data-mt-sort]');
      if (sort) { this.onSort(sort.dataset.mtSort); return; }
    };
    thead.onmousedown = e => {
      const handle = e.target.closest('[data-mt-resize]');
      if (!handle) return;
      this._resizingCol  = handle.dataset.mtResize;
      this._resizeStartX = e.clientX;
      this._resizeStartW = this.ancho(this._resizingCol);
      document.addEventListener('mousemove', this._onMouseMove);
      document.addEventListener('mouseup',   this._onMouseUp);
      e.stopPropagation(); e.preventDefault();
    };
    thead.onclick = e => {
      const sort   = e.target.closest('[data-mt-sort]');
      const filter = e.target.closest('[data-mt-filter]');
      if (sort && !filter) { this.onSort(sort.dataset.mtSort); return; }
      if (filter) { this._toggleFilter(filter.dataset.mtFilter, filter); return; }
    };
  }

  _onMouseMove(e) {
    if (!this._resizingCol) return;
    const w = Math.max(40, this._resizeStartW + (e.clientX - this._resizeStartX));
    this.anchos[this._resizingCol] = w;
    // Actualizar colgroup en vivo
    const th = document.querySelector(`th[data-mt-col="${this._resizingCol}"]`);
    if (th) {
      const idx = Array.from(th.parentNode.children).indexOf(th);
      const cols = document.querySelectorAll('colgroup col');
      if (cols[idx]) cols[idx].style.width = w + 'px';
    }
  }

  _onMouseUp() {
    document.removeEventListener('mousemove', this._onMouseMove);
    document.removeEventListener('mouseup',   this._onMouseUp);
    if (this._resizingCol) {
      this.onResize(this._resizingCol, this.anchos[this._resizingCol]);
      this._resizingCol = null;
    }
  }

  _drop(e, destino) {
    const origen = e.dataTransfer.getData('mt-col');
    if (!origen || origen === destino) return;
    const from = this.cols.findIndex(c => c.k === origen);
    const to   = this.cols.findIndex(c => c.k === destino);
    if (from < 0 || to < 0) return;
    this.cols.splice(from, 1);
    this.cols.splice(to, 0, { k: origen, l: this.cols.find(c=>c.k===origen)?.l || origen });
    // Reordenar usando el array original completo
    this.onReorder(this.cols.map(c => c.k));
  }

  _toggleFilter(k, btnEl) {
    if (this._openFilter === k) { this._closeFilter(); return; }
    this._closeFilter();
    this._openFilter = k;

    // Calcular valores únicos
    const vals = [...new Set(this.datosFilas.map(r => String(r[k] ?? '')).filter(v => v !== ''))].sort();

    const th = btnEl.closest('th');
    const rect = th.getBoundingClientRect();
    const div = document.createElement('div');
    div.id = 'mt-filter-popup';
    div.style.cssText = `position:fixed;top:${rect.bottom+2}px;left:${rect.left}px;
      background:#fff;border:1px solid #e5e7eb;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.15);
      z-index:9999;min-width:160px;max-height:260px;overflow-y:auto;padding:6px 0;font-size:13px`;

    const activo = this.filtros[k] || '';
    div.innerHTML = `
      <div style="padding:6px 12px 4px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase">${k.replace(/_/g,' ')}</div>
      <div onclick="window.__mt._setFilter('${k}','')" style="padding:6px 14px;cursor:pointer;${!activo?'font-weight:600;color:#1e3a5f':''}" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background=''">Todos</div>
      ${vals.map(v => `<div onclick="window.__mt._setFilter('${k}','${v.replace(/'/g,"\\'")}');event.stopPropagation()"
        style="padding:6px 14px;cursor:pointer;${activo===v?'font-weight:600;color:#1e3a5f':'color:#374151'}"
        onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background=''">${v}</div>`).join('')}`;

    document.body.appendChild(div);
    setTimeout(() => document.addEventListener('click', this._closeFilter, {once: true}), 50);
  }

  _setFilter(k, v) {
    if (v === '') delete this.filtros[k]; else this.filtros[k] = v;
    this._closeFilter();
    this.onFilter(k, v);
  }

  _closeFilter() {
    document.getElementById('mt-filter-popup')?.remove();
    this._openFilter = null;
  }

  aplicarFiltros(datos) {
    return datos.filter(row =>
      Object.entries(this.filtros).every(([k, v]) => String(row[k] ?? '') === v)
    );
  }
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
