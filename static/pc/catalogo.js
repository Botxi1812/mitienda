/**
 * catalogo.js — Renderer genérico para páginas de catálogo.
 *
 * Uso: la página HTML define window.__TABLA__ (nombre en tabla_definiciones)
 * y carga este script. Hace todo lo demás automáticamente.
 *
 * Variables que la página puede definir antes de cargar este script:
 *   window.__TABLA__       = 'clientes'   (obligatorio)
 */

// ── Estado global ─────────────────────────────────────────────────────────────
let _cfg = null;
let _datos = [];
let _editId = null;
let _sortCol = null;
let _sortDir = 1;
let _camposExtra = [];
let _colsDef = [];
let _colsVis = [];
let _perfilActivo = null;
let _perfilesLista = [];
let _operario = null;
let _mt = null;  // instancia MiTabla

// ── Init ──────────────────────────────────────────────────────────────────────
async function initCatalog() {
  // Tabla: desde window.__TABLA__ (legacy) o desde la URL (/clientes -> buscar ruta='clientes')
  let tabla = window.__TABLA__;
  if (!tabla) {
    const ruta = window.location.pathname.replace(/^\//, '');
    const tablasDef = await fetch('/api/tablas').then(r => r.json()).catch(() => []);
    const t = tablasDef.find(x => x.ruta === ruta);
    if (!t) { document.body.innerHTML = '<p style="color:red">Tabla no encontrada para esta ruta</p>'; return; }
    tabla = t.nombre;
  }
  window.__TABLA__ = tabla;  // normalizar para que el resto del código lo use

  _operario = initHeader();
  renderNavDinamica();

  _cfg = await fetch(`/api/tablas/${tabla}/config`).then(r => r.json());
  // Si tiene padre, cargar sus opciones
  if (_cfg.padre_tabla && !_cfg.padre_opciones?.length) {
    _cfg.padre_opciones = await fetch(`/api/entidad/${_cfg.padre_tabla}`)
      .then(r => r.json()).catch(() => []);
  }

  document.title = `Mi Tienda — ${_cfg.etiqueta}`;

  // Columnas: todas (principal + extra)
  _camposExtra = _cfg.campos.filter(c => !c.es_principal);
  const colsPrinc = _cfg.campos.filter(c => c.es_principal).map(c => ({k: c.nombre, l: c.etiqueta}));
  const colsExtra = _camposExtra.map(c => ({k: c.nombre, l: c.etiqueta}));
  _colsDef = [...colsPrinc, ...colsExtra];
  _sortCol = _cfg.campo_principal || _colsDef[0]?.k || 'id';

  await _renderEstructura();
  _initMiTabla();

  await Promise.all([_cargarDatos(), _cargarPerfiles()]);
}

// ── Carga de datos ────────────────────────────────────────────────────────────
async function _cargarDatos() {
  _datos = await fetch(`/api/entidad/${window.__TABLA__}`).then(r => r.json());
  _render();
}

// ── Render tabla ──────────────────────────────────────────────────────────────
function _render() {
  const q = (document.getElementById('cat-buscador')?.value || '').toLowerCase();
  const campoBusq = [_cfg.campo_principal, _cfg.campo_secundario].filter(Boolean);

  let lista = _datos;
  if (q) {
    lista = _datos.filter(row =>
      campoBusq.some(c => String(row[c] || '').toLowerCase().includes(q)) ||
      Object.values(row).some(v => String(v || '').toLowerCase().includes(q))
    );
  }
  if (_mt) lista = _mt.aplicarFiltros(lista);

  const sorted = ordenarTabla(lista, _sortCol, _sortDir);
  const count = document.getElementById('cat-count');
  if (count) count.textContent = `${sorted.length} ${sorted.length === 1 ? _cfg.etiqueta_singular : _cfg.etiqueta}`.toLowerCase();

  _renderCabecera();

  const tb = document.getElementById('cat-tbody');
  if (!sorted.length) {
    tb.innerHTML = `<tr><td colspan="${_colsVis.length}" class="empty">Sin resultados</td></tr>`;
    return;
  }
  tb.innerHTML = sorted.map(row => `
    <tr onclick="catAbrir(${row.id})" style="cursor:pointer">
      ${_colsVis.map(col => _renderCell(row, col.k)).join('')}
    </tr>`).join('');
}

function _initMiTabla() {
  _mt = new MiTabla({
    cols: _colsVis,
    sortCol: _sortCol, sortDir: _sortDir,
    onSort: col => { if (_sortCol===col) _sortDir*=-1; else {_sortCol=col;_sortDir=1;} _mt.sortCol=_sortCol; _mt.sortDir=_sortDir; _render(); },
    onReorder: keys => { _colsVis = keys.map(k => _colsDef.find(c=>c.k===k)).filter(Boolean); _mt.cols=_colsVis; _render(); if(_perfilActivo) _guardarConfigPerfil(); },
    onResize: () => { if(_perfilActivo) _guardarConfigPerfil(); },
    onFilter: () => _render(),
    datosFilas: _datos,
  });
  window.__mt = _mt;
}

function _renderCabecera() {
  if (!_mt) return;
  _mt.cols = _colsVis;
  _mt.sortCol = _sortCol; _mt.sortDir = _sortDir;
  _mt.datosFilas = _datos;
  _mt.renderCabecera(
    document.getElementById('cat-thead'),
    document.getElementById('cat-colgroup')
  );
}

function _sortBy(col) {
  if (_sortCol === col) _sortDir *= -1; else { _sortCol = col; _sortDir = 1; }
  _render();
}

function _renderCell(row, k) {
  const v = row[k];
  if (v === null || v === undefined || v === '') return `<td style="color:#9ca3af">—</td>`;
  // Precio: formatear con 2 decimales si es número
  const campoDef = _cfg.campos.find(c => c.nombre === k);
  if (campoDef?.tipo === 'numero' && !isNaN(Number(v))) {
    return `<td style="text-align:right">${fmt(Number(v))}</td>`;
  }
  return `<td>${v}</td>`;
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function catAbrir(id) {
  _editId = id || null;
  const row = id ? _datos.find(x => x.id === id) : null;

  document.getElementById('cat-msg-error').style.display = 'none';
  document.getElementById('cat-msg-ok').style.display = 'none';
  document.getElementById('cat-m-titulo').textContent =
    id ? `Editar ${_cfg.etiqueta_singular}` : `Nuevo ${_cfg.etiqueta_singular}`;

  // Rellenar campos estándar dinámicamente
  _cfg.campos.filter(c => c.es_principal).forEach(c => {
    const el = document.getElementById(`cat-f-${c.nombre}`);
    if (el) el.value = row ? (row[c.nombre] ?? '') : '';
  });

  // Selector de padre: rellenar con el valor actual del campo_padre_fk
  if (_cfg.padre_tabla && _cfg.campo_padre_fk) {
    const sel = document.getElementById('cat-f-padre');
    if (sel && row) sel.value = row[_cfg.campo_padre_fk] ?? '';
  }

  // Campos extra
  document.getElementById('cat-campos-extra').innerHTML =
    renderCamposExtra(_camposExtra, row || {});

  document.getElementById('cat-modal').classList.add('show');
  // Focus primer campo
  const first = document.querySelector('#cat-modal input:not([disabled])');
  if (first) first.focus();
}

function catCerrar() {
  document.getElementById('cat-modal').classList.remove('show');
}

async function catGuardar() {
  const body = {};

  // Recoger campos estándar
  _cfg.campos.filter(c => c.es_principal).forEach(c => {
    const el = document.getElementById(`cat-f-${c.nombre}`);
    if (el) body[c.nombre] = el.value.trim();
  });

  // Recoger valor del combo padre → se guarda en el campo campo_padre_fk
  if (_cfg.padre_tabla && _cfg.campo_padre_fk) {
    const sel = document.getElementById('cat-f-padre');
    if (sel) body[_cfg.campo_padre_fk] = sel.value || '';
  }

  // Validar requeridos
  const requeridos = _cfg.campos.filter(c => c.es_requerido || c.es_requerido);
  for (const c of requeridos) {
    if (!body[c.nombre]) {
      _showError(`"${c.etiqueta}" es obligatorio`); return;
    }
  }

  // Campos extra personalizados
  const extra = recogerCamposExtra(_camposExtra);
  Object.assign(body, extra);

  const url    = _editId ? `/api/entidad/${window.__TABLA__}/${_editId}` : `/api/entidad/${window.__TABLA__}`;
  const method = _editId ? 'PUT' : 'POST';

  try {
    const res  = await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) { _showError(data.detail || 'Error al guardar'); return; }
    _showOk(_editId ? `${_cfg.etiqueta_singular} actualizado` : `${_cfg.etiqueta_singular} creado`);
    await _cargarDatos();
    setTimeout(catCerrar, 1200);
  } catch(e) {
    _showError('Error de conexión: ' + e.message);
  }
}

function _showError(msg) {
  const el = document.getElementById('cat-msg-error');
  el.textContent = msg; el.style.display = 'block';
  document.getElementById('cat-msg-ok').style.display = 'none';
}
function _showOk(msg) {
  const el = document.getElementById('cat-msg-ok');
  el.textContent = msg; el.style.display = 'block';
  document.getElementById('cat-msg-error').style.display = 'none';
}

// ── Perfiles ──────────────────────────────────────────────────────────────────
async function _cargarPerfiles() {
  if (!_operario) return;
  _perfilesLista = await apiCargarPerfiles(window.__TABLA__, _operario.id);
  renderSelectPerfiles(_perfilesLista, _perfilActivo?.id);
  document.getElementById('btn-borrar-perfil').style.display = _perfilActivo ? 'block' : 'none';
}

function catAplicarPerfil(id) {
  if (!id) {
    _perfilActivo = null;
    document.getElementById('btn-borrar-perfil').style.display = 'none';
    document.getElementById('perfil-info').textContent = '';
    _colsVis = [..._colsDef]; _render(); return;
  }
  const p = _perfilesLista.find(x => x.id == id);
  if (!p) return;
  _perfilActivo = p;
  document.getElementById('btn-borrar-perfil').style.display = 'block';
  document.getElementById('perfil-info').textContent = `Perfil: ${p.nombre}`;
  if (p.config?.columnas) {
    _colsVis = p.config.columnas.map(k => _colsDef.find(c=>c.k===k)).filter(Boolean);
    if (!_colsVis.length) _colsVis = [..._colsDef];
  } else {
    _colsVis = [..._colsDef];
  }
  if (_mt && p.config?.anchos) Object.assign(_mt.anchos, p.config.anchos);
  _render();
}

function catAbrirModalPerfil() {
  document.getElementById('perfil-nombre').value = _perfilActivo ? _perfilActivo.nombre : '';
  const activos = new Set(_perfilActivo?.config?.columnas || _colsDef.map(c => c.k));
  document.getElementById('perfil-cols-check').innerHTML = _colsDef.map(c =>
    `<label><input type="checkbox" id="cc-${c.k}" ${activos.has(c.k) ? 'checked' : ''}> ${c.l}</label>`
  ).join('');
  document.getElementById('modal-perfil').classList.add('show');
  document.getElementById('perfil-nombre').focus();
}

function catCerrarModalPerfil() {
  document.getElementById('modal-perfil').classList.remove('show');
}

async function _guardarConfigPerfil() {
  if (!_perfilActivo) return;
  const config = { columnas: _colsVis.map(c => c.k), anchos: _mt?.anchos || {} };
  await apiActualizarPerfil(_perfilActivo.id, window.__TABLA__, _operario.id, _perfilActivo.nombre, config);
  _perfilActivo.config = config;
}

async function catGuardarPerfil() {
  const nombre = document.getElementById('perfil-nombre').value.trim();
  if (!nombre) { alert('Escribe un nombre para el perfil'); return; }
  const columnas = _colsDef.filter(c => document.getElementById(`cc-${c.k}`)?.checked).map(c => c.k);
  const config = { columnas, anchos: _mt?.anchos || {} };
  if (_perfilActivo) {
    await apiActualizarPerfil(_perfilActivo.id, window.__TABLA__, _operario.id, nombre, config);
    _perfilActivo.nombre = nombre; _perfilActivo.config = config;
    catAplicarPerfil(_perfilActivo.id);
  } else {
    const res = await apiCrearPerfil(window.__TABLA__, _operario.id, nombre, config);
    if (res.ok) {
      await _cargarPerfiles();
      document.getElementById('perfil-select').value = res.id;
      catAplicarPerfil(res.id);
    }
  }
  catCerrarModalPerfil();
  await _cargarPerfiles();
}

async function catBorrarPerfil() {
  if (!_perfilActivo) return;
  if (!confirm(`¿Borrar el perfil "${_perfilActivo.nombre}"?`)) return;
  await apiBorrarPerfil(_perfilActivo.id);
  _perfilActivo = null; _colsVis = [..._colsDef];
  document.getElementById('perfil-select').value = '';
  document.getElementById('btn-borrar-perfil').style.display = 'none';
  document.getElementById('perfil-info').textContent = '';
  _render(); await _cargarPerfiles();
}

// ── Construcción dinámica del modal ───────────────────────────────────────────
async function _buildModalFields() {
  const campos = _cfg.campos.filter(c => c.es_principal);
  let html = '';

  // Si tiene padre y campo_padre_fk, sustituir ese campo por un combo
  // (se renderiza aquí; luego al recorrer campos se salta ese campo)
  if (_cfg.padre_tabla && _cfg.campo_padre_fk && _cfg.padre_opciones?.length) {
    const campoFk = _cfg.campos.find(c => c.nombre === _cfg.campo_padre_fk);
    const labelFk = campoFk?.etiqueta || _cfg.campo_padre_fk;
    html += `<div class="campo">
      <label>${labelFk}</label>
      <select id="cat-f-padre">
        <option value="">— seleccionar —</option>
        ${_cfg.padre_opciones.map(o => `<option value="${o.nombre}">${o.nombre}</option>`).join('')}
      </select>
    </div>`;
  }

  // Campos estándar del modelo
  const grupoDoble = [];
  campos.forEach(c => {
    // Saltar el campo que ya se muestra como combo padre
    if (_cfg.campo_padre_fk && c.nombre === _cfg.campo_padre_fk) return;

    const required = c.es_requerido ? ' *' : '';
    const disabled = '';
    let input = '';

    if (c.tipo === 'numero') {
      input = `<input id="cat-f-${c.nombre}" type="number" step="any" placeholder="0">`;
    } else if (c.tipo === 'fecha') {
      input = `<input id="cat-f-${c.nombre}" type="date">`;
    } else if (c.tipo === 'lista' && c.opciones) {
      const opts = c.opciones.split(',').map(o => o.trim());
      input = `<select id="cat-f-${c.nombre}">
        <option value="">— seleccionar —</option>
        ${opts.map(o => `<option value="${o}">${o}</option>`).join('')}
      </select>`;
    } else if (c.nombre === 'email') {
      input = `<input id="cat-f-${c.nombre}" type="email" placeholder="${c.etiqueta}">`;
    } else if (c.nombre === 'telefono') {
      input = `<input id="cat-f-${c.nombre}" type="tel" placeholder="${c.etiqueta}">`;
    } else {
      input = `<input id="cat-f-${c.nombre}" type="text" placeholder="${c.etiqueta}">`;
    }

    grupoDoble.push(`<div class="campo"><label>${c.etiqueta}${required}</label>${input}</div>`);
  });

  // Agrupar de dos en dos los campos que no sean el campo principal (que va solo)
  const principal = campos.find(c => c.nombre === _cfg.campo_principal);
  const resto = campos.filter(c =>
    c.nombre !== _cfg.campo_principal && c.nombre !== _cfg.campo_padre_fk
  );

  if (principal) {
    html += `<div class="campo"><label>${principal.etiqueta}${principal.es_requerido ? ' *' : ''}</label>
      <input id="cat-f-${principal.nombre}" type="text" placeholder="${principal.etiqueta}">
    </div>`;
  }

  // Pares de campos
  for (let i = 0; i < resto.length; i += 2) {
    if (resto[i+1]) {
      html += `<div class="campo-row">`;
    }
    [resto[i], resto[i+1]].filter(Boolean).forEach(c => {
      const req = c.es_requerido ? ' *' : '';
      let input = '';
      if (c.tipo === 'numero') {
        input = `<input id="cat-f-${c.nombre}" type="number" step="any" placeholder="0">`;
      } else if (c.nombre === 'email') {
        input = `<input id="cat-f-${c.nombre}" type="email" placeholder="${c.etiqueta}">`;
      } else if (c.nombre === 'telefono') {
        input = `<input id="cat-f-${c.nombre}" type="tel" placeholder="${c.etiqueta}">`;
      } else {
        input = `<input id="cat-f-${c.nombre}" type="text" placeholder="${c.etiqueta}">`;
      }
      html += `<div class="campo"><label>${c.etiqueta}${req}</label>${input}</div>`;
    });
    if (resto[i+1]) html += `</div>`;
    else if (!resto[i+1] && i < resto.length - 1) { /* solo uno */ }
  }

  return html;
}

// ── Render estructura de la página ────────────────────────────────────────────
async function _renderEstructura() {
  const tabla = window.__TABLA__;
  const ruta  = _cfg.ruta || tabla;

  document.querySelector('title').textContent = `Mi Tienda — ${_cfg.etiqueta}`;

  // Header
  document.getElementById('cat-header-titulo').innerHTML =
    `<h1>&#127978; Mi Tienda</h1><nav class="nav-links" id="nav-dinamica"></nav>`;

  // Toolbar
  document.getElementById('cat-toolbar').innerHTML = `
    <input class="buscador" id="cat-buscador" type="text"
      placeholder="Buscar ${_cfg.etiqueta.toLowerCase()}…" oninput="_render()">
    <span class="count" id="cat-count"></span>
    <button class="btn-nuevo" onclick="catAbrir()">+ Nuevo ${_cfg.etiqueta_singular.toLowerCase()}</button>`;

  // Modal campos
  document.getElementById('cat-modal-campos').innerHTML = await _buildModalFields();

  // Inicializar columnas visibles (por defecto todas)
  _colsVis = [..._colsDef];

  // Disparar nav dinámica
  renderNavDinamica();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
initCatalog();
