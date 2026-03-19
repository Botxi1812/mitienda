# Mi Tienda — Manual completo y pendientes

---

## RESUMEN EJECUTIVO (para el usuario)

### Qué tienes ahora mismo

Una aplicación web de gestión de ventas que corre en tu portátil y es accesible desde cualquier dispositivo de tu red local. Tiene interfaz completa para PC y una interfaz simplificada para móvil.

**Cómo arrancarla:** doble clic en `start.bat` dentro de la carpeta `C:\mitienda\`
**PC:** `http://localhost:8000` o `http://[ip-portatil]:8000`
**Móvil:** `http://[ip-portatil]:8000/movil`

### Lo que funciona hoy

- Login con selección de operario
- Crear ventas con múltiples líneas, precios especiales automáticos, contado/crédito
- Interfaz móvil paso a paso (un artículo por venta)
- Consulta de ventas con filtros, rejilla completa, editor multilinea para sanear
- Gestión de clientes, artículos, trabajadores, departamentos
- Configuración de campos extra por tabla (Columna BD y JSON)
- Campos extra aparecen automáticamente en formularios y en la rejilla de consultas
- Perfiles de vista en consultas (guardar configuración personalizada por operario)
- Parámetros configurables (máx. columnas y JSON por tabla)

### Lo que queda pendiente (resumen)

1. **Drag & drop en consultas** — arrastrar bordes para cambiar ancho de columna, arrastrar cabeceras para reordenar
2. **Filtros dinámicos** — después de buscar, aparecen filtros adicionales para los campos extra del resultado
3. **Búsqueda avanzada** — buscar por campo extra sin saber la fecha
4. **Perfiles en el resto de pantallas** — clientes, artículos, trabajadores también tendrán perfiles de vista
5. **Subir a Railway** — para acceder desde cualquier sitio sin estar en casa
6. **Migrar a PostgreSQL** — cuando el volumen lo requiera

---

## PENDIENTES TÉCNICOS DETALLADOS (para Claude)

### Pendiente 1 — Drag & drop de columnas en consultas

#### 1a. Redimensionar ancho (arrastrar borde derecho de cabecera)

Añadir a `consultas.html`:

```css
.resize-handle {
  position: absolute; right: 0; top: 0;
  width: 6px; height: 100%;
  cursor: col-resize;
}
.resize-handle:hover { background: rgba(255,255,255,0.3); }
thead th { position: relative; }
table { table-layout: fixed; }
```

```javascript
let anchos = {}, resizingCol = null, resizeStartX = 0, resizeStartW = 0;

// En renderCabecera(), cada <th> debe tener:
// data-campo="${c.k}" style="width:${anchos[c.k]||'auto'}"
// y dentro: <div class="resize-handle" onmousedown="iniciarResize(event,'${c.k}')"></div>

function iniciarResize(e, campo) {
  resizingCol = campo;
  resizeStartX = e.clientX;
  resizeStartW = anchos[campo] || 120;
  document.addEventListener('mousemove', onResize);
  document.addEventListener('mouseup', finResize);
  e.preventDefault();
}
function onResize(e) {
  if (!resizingCol) return;
  anchos[resizingCol] = Math.max(60, resizeStartW + (e.clientX - resizeStartX));
  const th = document.querySelector(`th[data-campo="${resizingCol}"]`);
  if (th) th.style.width = anchos[resizingCol] + 'px';
}
function finResize() {
  document.removeEventListener('mousemove', onResize);
  document.removeEventListener('mouseup', finResize);
  if (resizingCol && perfilActivo) guardarConfigPerfil();
  resizingCol = null;
}
```

#### 1b. Reordenar columnas (arrastrar cabecera entera)

```javascript
let columnasOrden = []; // array de keys en el orden actual
let dragCol = null;

// En cada <th>:
// draggable="true"
// ondragstart="dragStart('${c.k}')"
// ondragover="dragOver(event,'${c.k}')"
// ondrop="dragDrop('${c.k}')"

function dragStart(campo) { dragCol = campo; }
function dragOver(e, campo) { e.preventDefault(); }
function dragDrop(destino) {
  if (!dragCol || dragCol === destino) return;
  const from = columnasOrden.indexOf(dragCol);
  const to   = columnasOrden.indexOf(destino);
  columnasOrden.splice(from, 1);
  columnasOrden.splice(to, 0, dragCol);
  dragCol = null;
  renderTabla();
  if (perfilActivo) guardarConfigPerfil();
}
```

#### 1c. Guardar anchos y orden en perfil activo

```javascript
async function guardarConfigPerfil() {
  if (!perfilActivo) return;
  const config = {
    columnas: columnasOrden.map(k => ({
      campo: k, ancho: anchos[k] || 120, visible: true
    }))
  };
  await fetch(`/api/perfiles/${perfilActivo.id}`, {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      pantalla:'consultas', operario_id: operario.id,
      nombre: perfilActivo.nombre, config
    })
  });
}
```

#### 1d. Cargar anchos y orden al aplicar perfil

En `aplicarPerfil()`, si `p.config.columnas` existe:
```javascript
columnasOrden = p.config.columnas.map(c => c.campo);
p.config.columnas.forEach(c => { anchos[c.campo] = c.ancho; });
```

---

### Pendiente 2 — Filtros dinámicos fase 2

Después de la búsqueda inicial, detectar campos extra en el resultado
y construir filtros adicionales automáticamente (filtrado en cliente, sin nueva llamada).

Añadir en `consultas.html` dentro del div `.filtros`:
```html
<div id="filtros-extra" class="filtros-grid" style="margin-top:10px;display:none"></div>
```

Añadir al final de `buscar()`:
```javascript
// Detectar valores únicos por campo extra
const filtrosExtraVals = {};
datos.forEach(l => {
  (window._camposExtra||[]).forEach(k => {
    if (l[k] && l[k] !== '') {
      if (!filtrosExtraVals[k]) filtrosExtraVals[k] = new Set();
      filtrosExtraVals[k].add(l[k]);
    }
  });
});
const divFE = document.getElementById('filtros-extra');
if (Object.keys(filtrosExtraVals).length) {
  divFE.style.display = 'grid';
  divFE.innerHTML = Object.entries(filtrosExtraVals).map(([k, vals]) => `
    <div class="fg">
      <label>${k.replace(/_/g,' ')}</label>
      <select id="fe-${k}" onchange="filtrarExtra()">
        <option value="">Todos</option>
        ${[...vals].sort().map(v=>`<option>${v}</option>`).join('')}
      </select>
    </div>`).join('');
} else {
  divFE.style.display = 'none';
  divFE.innerHTML = '';
}
```

Añadir función:
```javascript
function filtrarExtra() {
  const activos = {};
  (window._camposExtra||[]).forEach(k => {
    const sel = document.getElementById(`fe-${k}`);
    if (sel && sel.value) activos[k] = sel.value;
  });
  const filtrados = Object.keys(activos).length
    ? datos.filter(l => Object.entries(activos).every(([k,v]) => l[k] === v))
    : datos;
  renderTabla(filtrados);  // renderTabla debe aceptar array opcional
}
```

---

### Pendiente 3 — Búsqueda avanzada sin fecha conocida

#### Backend — nuevo endpoint

```python
@app.get("/api/ventas/buscar_campo")
def buscar_por_campo(
    campo: str, valor: str,
    db: Session = Depends(database.get_db)
):
    # Para campos JSON usar JSON_EXTRACT (SQLite 3.38+)
    # Para campos columna usar WHERE directo
    lineas = db.execute(text(f"""
        SELECT lv.id FROM lineas_venta lv
        WHERE JSON_EXTRACT(lv.extra, '$.{campo}') = :v
           OR lv.{campo} = :v
        ORDER BY lv.albaran_id DESC LIMIT 500
    """), {"v": valor}).fetchall()
    ids = [r[0] for r in lineas]
    if not ids: return []
    # Cargar las lineas completas
    resultado = db.query(models.LineaVenta).filter(
        models.LineaVenta.id.in_(ids)
    ).all()
    return [linea_dict(l) for l in resultado]
```

**Nota:** verificar versión SQLite con `SELECT sqlite_version()` antes de usar JSON_EXTRACT.
Si < 3.38, usar `LIKE '%"campo":"valor"%'` como fallback (menos preciso).

#### Frontend — panel adicional en consultas

```html
<div id="panel-avanzado" style="display:none;background:#fff8ed;border-radius:10px;padding:14px;margin-top:10px;border:1px solid #fed7aa">
  <div style="font-size:13px;font-weight:600;color:#b45309;margin-bottom:10px">
    🔍 Búsqueda avanzada — busca en todo el histórico
  </div>
  <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
    <div class="fg" style="min-width:160px">
      <label>Campo</label>
      <select id="busq-campo"></select>
    </div>
    <div class="fg" style="min-width:160px">
      <label>Valor</label>
      <input id="busq-valor" type="text" placeholder="Valor a buscar">
    </div>
    <button onclick="busquedaAvanzada()" class="btn-buscar">Buscar en histórico</button>
  </div>
  <div id="busq-aviso" style="font-size:12px;color:#b45309;margin-top:8px"></div>
</div>
```

---

### Pendiente 4 — Perfiles en el resto de pantallas

Las pantallas `clientes.html`, `articulos.html`, `trabajadores.html`, `departamentos.html`
deben tener la misma barra de perfiles que consultas.

**Refactorizar en `comun.js`:**

```javascript
// Función reutilizable para cualquier pantalla
async function initPerfilesBarra(pantalla, operario, onAplicar) {
  // 1. Crear el HTML de la barra
  // 2. Cargar perfiles del operario para esa pantalla
  // 3. Cuando se selecciona un perfil, llamar onAplicar(config)
  // 4. Guardar vista llama a POST/PUT /api/perfiles
}
```

Llamar desde cada pantalla con:
```javascript
initPerfilesBarra('clientes', operario, config => {
  // aplicar configuración de columnas visibles y anchos
});
```

---

### Pendiente 5 — Subir a Railway (producción cloud)

1. Crear cuenta en railway.app
2. Crear repositorio Git local: `git init && git add . && git commit -m "inicial"`
3. Conectar repo en Railway
4. Railway detecta Python/FastAPI y despliega automáticamente
5. Añadir PostgreSQL desde el panel de Railway con un clic
6. Cambiar en `database.py`:
   ```python
   # Antes
   DATABASE_URL = "sqlite:///./tienda.db"
   # Después (Railway proporciona esta URL automáticamente)
   DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./tienda.db")
   ```
7. Cada actualización: `git add . && git commit -m "..." && git push`

---

### Pendiente 6 — Migrar a PostgreSQL

Cambio de una línea en `database.py` más:

- Añadir índice GIN sobre columna `extra` para búsquedas eficientes:
  ```sql
  CREATE INDEX idx_lineas_extra ON lineas_venta USING GIN (extra::jsonb);
  CREATE INDEX idx_albaranes_fecha ON albaranes(fecha);
  CREATE INDEX idx_lineas_cliente ON albaranes(cliente_id);
  CREATE INDEX idx_lineas_operario ON albaranes(operario_id);
  ```
- Ajustar `migrate.py` — PostgreSQL usa sintaxis diferente para `ALTER TABLE`
- El `JSON_EXTRACT` de SQLite se convierte en `extra->>'campo'` en PostgreSQL

---

## MANUAL DE USO

### Arranque

Doble clic en `start.bat`. La ventana negra debe permanecer abierta mientras uses la app.
Al cerrarla, el servidor se apaga. Para arrancar de nuevo, doble clic otra vez.

El navegador se abre automáticamente en `http://localhost:8000`.

---

### Pantalla de login

Muestra los operarios disponibles como tarjetas con avatar. Haz clic en tu nombre.
Tu sesión queda guardada en el navegador hasta que pulses "Salir".

---

### Nueva venta (PC)

1. **Seleccionar cliente** — escribe en el buscador para filtrar por nombre, código o ciudad
2. **Añadir artículos** — botón "＋ Añadir artículo", elige artículo de la lista
3. **Precio especial** — si ese cliente tiene precio pactado para ese artículo, aparece automáticamente con ★
4. **Cantidad y precio** — editables directamente en la tabla
5. **Pago** — elige Contado o Crédito por línea
6. **Confirmar venta** — genera el albarán con número correlativo

Si hay campos extra configurados en ventas, aparecen como columnas adicionales en cada línea.

---

### Interfaz móvil

Accede desde el móvil a `http://[ip-portatil]:8000/movil`

Flujo fijo paso a paso:
1. ¿Quién eres? → selecciona operario
2. ¿Qué vendes hoy? → selecciona artículo (se mantiene para todas las ventas del día)
3. ¿A quién? → busca el cliente
4. ¿Cuántas unidades? → botones + y −
5. ¿Cómo paga? → muestra importe total
   - Contado → pantalla de cobro con importe grande → botón "Cobrado"
   - Crédito → confirma directamente
6. ✅ Venta realizada → "Nueva venta" vuelve al paso 3 manteniendo artículo

---

### Consultas

Filtros disponibles: fecha desde/hasta, operario, cliente, artículo.
La fecha hasta se pone automáticamente a hoy.

**Resumen:** aparece encima de la rejilla con totales de líneas, albaranes, importe y precios especiales.

**Ordenar:** clic en cualquier cabecera de columna. Clic de nuevo invierte el orden.

**Columnas dinámicas:** si las ventas del resultado tienen campos extra, aparecen como columnas adicionales al final de la tabla.

**Líneas modificadas:** se muestran con fondo amarillo claro. Las columnas "Modificado por" y "Fecha mod." indican quién y cuándo.

#### Editor multilinea (sanear ventas)

1. Filtra las ventas que quieres corregir
2. Pulsa el botón naranja **✏️ Editar selección**
3. Las columnas editables son: artículo, cantidad, precio, pago
4. Si cambias el artículo, el precio se sugiere automáticamente (con precio especial si corresponde)
5. Botón × elimina una línea (con confirmación). Si el albarán se queda sin líneas, desaparece también
6. **Guardar cambios** — solo guarda las líneas que realmente cambiaron
7. El operario logado queda registrado como "modificado por" con fecha y hora

#### Perfiles de vista

La barra encima de los filtros permite guardar tu configuración visual favorita.

- **Sin perfil** → se ven todas las columnas
- **Guardar vista** → pide nombre, guarda el estado actual
- **Seleccionar perfil** → aplica esa configuración
- **Borrar esta vista** → elimina el perfil activo

Cada operario tiene sus propios perfiles. No interfieren entre usuarios.

---

### Gestión de clientes

Tabla con buscador en tiempo real (nombre, código, ciudad).
Clic en cualquier fila para editar. Botón "+ Nuevo cliente" para crear.

Campos estándar: Código, Nombre, Teléfono, Email, Ciudad.
Campos extra configurados aparecen automáticamente en el formulario.

---

### Gestión de trabajadores

Misma mecánica que clientes.
El departamento se elige de la lista de departamentos existentes.
Enlace directo "Gestionar departamentos" dentro del formulario.

---

### Gestión de artículos

Campos: Código, Descripción, Categoría, Precio.
El precio es el precio estándar. Los precios especiales por cliente se gestionan aparte (tabla `precios_especiales` — pendiente de pantalla de gestión).

---

### Gestión de departamentos

Lista simple con nombre. Al editar un departamento, muestra los trabajadores asignados.
Los trabajadores existentes mantienen el nombre del departamento copiado en sus ventas históricas aunque el departamento cambie de nombre.

---

### ⚙️ Configuración

Accesible desde el icono ⚙️ Config en el header de todas las pantallas PC.

#### Parámetros globales

- **Máx. columnas por tabla** — cuántos campos de tipo Columna BD se pueden crear por tabla (por defecto 5)
- **Máx. campos JSON por tabla** — cuántos campos JSON se pueden crear por tabla (por defecto 10)

Estos son límites para campos personalizados. Los campos estándar (🔒) no cuentan.

#### Campos en línea de venta

Árbol con todas las tablas y sus campos. Marca los que quieres que se copien automáticamente
en cada línea de venta en el momento de realizarla. Una vez marcado, ese valor queda
registrado en el historial aunque luego cambies el dato en la tabla maestra.

#### Campos personalizados por tabla

Cada tabla tiene una tarjeta con dos contadores y dos botones.

**Tipos de campo:**

| Tipo | Almacenamiento | Límite | Archivado cuenta límite |
|------|---------------|--------|------------------------|
| Columna BD | Columna real en la BD | max_columnas | ✅ Sí |
| JSON | Campo dentro de JSON `extra` | max_json | ❌ No |

**Estados de un campo personalizado:**

| Estado | Visual | En formularios | En consultas | Cuenta límite |
|--------|--------|---------------|--------------|--------------|
| Activo | Normal | ✅ Aparece | ✅ Aparece | ✅ |
| Archivado | Translúcido 📦 | ❌ Oculto | ❌ Oculto | Columna Sí / JSON No |

**Acciones:**
- **📦 Archivar** — oculta el campo. Los datos históricos quedan intactos.
- **♻️ Reactivar** — vuelve a mostrar el campo. Los datos históricos reaparecen.
- **🗑️ Eliminar** — solo disponible en Columna BD archivada. Pide confirmación escribiendo el nombre. Borra la entrada de configuración (la columna física queda inactiva en la BD pero no hace daño).

**JSON no tiene eliminar** — los datos están diluidos en miles de registros JSON, no hay nada que borrar limpiamente.

---

## ESQUEMAS DE TABLAS

### clientes
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| codigo | TEXT | CLI-001 … CLI-100 |
| nombre | TEXT | |
| email | TEXT | |
| telefono | TEXT | |
| ciudad | TEXT | |
| extra | TEXT | JSON con campos personalizados volátiles |
| [campos_fijos] | TEXT | Columnas añadidas por configuración |

### articulos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| codigo | TEXT | ART-001 … ART-010 |
| descripcion | TEXT | |
| categoria | TEXT | |
| precio | REAL | Precio estándar |
| extra | TEXT | JSON campos personalizados |

### operarios
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| numero | TEXT | OP-001 … OP-005 |
| nombre | TEXT | |
| telefono | TEXT | |
| departamento_id | INTEGER FK→departamentos | |
| departamento | TEXT | Nombre copiado (legacy) |
| extra | TEXT | JSON campos personalizados |

### departamentos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| nombre | TEXT | |
| extra | TEXT | JSON campos personalizados |

### albaranes
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| numero | TEXT | ALB-000001 … |
| fecha | DATETIME | |
| cliente_id | INTEGER FK→clientes | |
| operario_id | INTEGER FK→operarios | |

**Nota:** no tiene campo `total` — el total se calcula sumando importes de sus líneas.

### lineas_venta
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| albaran_id | INTEGER FK→albaranes | |
| articulo_id | INTEGER FK→articulos | |
| cantidad | REAL | |
| precio_unitario | REAL | Precio aplicado en el momento |
| importe | REAL | cantidad × precio_unitario |
| es_precio_especial | INTEGER | 0/1 |
| departamento | TEXT | Copiado del operario en el momento de la venta |
| tipo_pago | TEXT | contado / credito / vacío |
| modificado_por | TEXT | Nombre del operario que saneó |
| fecha_modificacion | TEXT | Cuándo se saneó |
| extra | TEXT | JSON con campos extra de ventas |

### precios_especiales
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| cliente_id | INTEGER FK→clientes | |
| articulo_id | INTEGER FK→articulos | |
| precio | REAL | Precio acordado para ese par |

### configuracion_campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| tabla | TEXT | clientes / articulos / operarios / departamentos |
| nombre | TEXT | nombre interno (snake_case) |
| etiqueta | TEXT | nombre visible |
| tipo | TEXT | texto / numero / fecha / lista |
| tipo_campo | TEXT | columna / json |
| activo | INTEGER | 1=activo, 0=archivado |
| orden | INTEGER | posición en el formulario |
| opciones | TEXT | para tipo lista: "A,B,C" |
| es_estandar | INTEGER | 1=indestructible 🔒 |

### configuracion_ventas
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| campo_id | INTEGER FK→configuracion_campos | |
| activo | INTEGER | 1=fluye a la venta |
| orden | INTEGER | |

### configuracion_parametros
| Campo | Tipo | Descripción |
|-------|------|-------------|
| clave | TEXT PK | max_columnas / max_json |
| valor | TEXT | número como texto |
| etiqueta | TEXT | nombre visible |
| descripcion | TEXT | |

### perfiles_vista
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | |
| pantalla | TEXT | consultas / clientes / articulos… |
| operario_id | INTEGER FK→operarios | |
| nombre | TEXT | "Vista rápida" |
| config | TEXT | JSON con columnas, anchos, orden |
| creado | TEXT | fecha de creación |

---

## HISTORIAL DE ENTREGAS

### Entrega 1 — Base del proyecto
**Ficheros:** `main.py`, `database.py`, `models.py`, `seed.py`, `start.bat`, `static/login.html`, `static/ventas.html`, `static/consultas.html`

- Estructura completa del proyecto Python + FastAPI + SQLite
- Base de datos con 100 clientes, 10 artículos, 5 operarios, 50 precios especiales
- Login con selección de operario
- Nueva venta con múltiples líneas y detección automática de precio especial
- Rejilla de consultas con filtros por fecha, operario, cliente y artículo
- `start.bat` para arrancar sin VSCode

**Bug conocido en esta entrega:** el `.bat` tenía caracteres especiales (╔ ═) que Windows no reconocía como comandos.

---

### Entrega 2 — Fix start.bat + venv
**Cambios:** `start.bat` reescrito sin caracteres especiales, añadido soporte venv

- `.bat` limpio sin tildes ni caracteres especiales
- Ruta explícita a `C:\Program Files\Python313\python.exe`
- Añadido `venv` para aislar dependencias del proyecto

---

### Entrega 3 — Interfaz móvil (pantalla única)
**Ficheros nuevos:** `static/movil.html`

- Flujo paso a paso en una sola pantalla con divs show/hide
- Login, selección de artículo, cliente, cantidad, pago, éxito
- Contado muestra importe grande + botón cobrar
- Crédito confirma directamente
- Nueva venta mantiene operario y artículo del día

---

### Entrega 4 — Reestructuración de carpetas
**Cambios:** reorganización `static/pc/` y `static/movil/`

- Separación en carpetas `pc/` y `movil/`
- Móvil dividido en 6 ficheros HTML independientes: `login.html`, `articulo.html`, `cliente.html`, `cantidad.html`, `pago.html`, `cobro.html`, `exito.html`
- CSS compartido `movil/comun.css`
- Rutas absolutas en todos los enlaces del móvil (fix bug "detail not found")

---

### Entrega 5 — Gestión de tablas maestras + arquitectura ampliada
**Ficheros nuevos:** `static/pc/clientes.html`, `static/pc/trabajadores.html`, `static/pc/articulos.html`, `static/pc/departamentos.html`, `static/pc/comun.css`, `static/pc/comun.js`

- Pantallas CRUD para clientes, trabajadores, artículos, departamentos
- Tabla `departamentos` nueva en BD con migración automática
- Campo `telefono` añadido a clientes y operarios
- Relación `departamento_id` FK en operarios
- CSS y JS compartidos para todas las pantallas PC
- Navegación completa con links entre todas las pantallas

---

### Entrega 6 — Eliminar campo `total` de albaranes
**Cambios:** `models.py`, `main.py`, `migrate.py`

- Campo `total` eliminado de la tabla `albaranes` (era dato calculado redundante)
- `migrate.py` recrea la tabla sin ese campo preservando todos los datos
- `main.py` ya no calcula ni guarda totales al crear albaranes
- El total se calcula sumando importes de líneas cuando se necesita

---

### Entrega 7 — Editor multilinea + campos de auditoría + departamento en venta
**Cambios:** `main.py`, `models.py`, `migrate.py`, `static/pc/consultas.html`

- Nuevos campos en `lineas_venta`: `departamento`, `tipo_pago`, `modificado_por`, `fecha_modificacion`
- El departamento se copia del operario en el momento de crear la venta
- Migración rellena `departamento` en líneas históricas existentes
- Botón "✏️ Editar selección" en consultas activa modo edición multilinea
- Campos editables en modo edición: artículo, cantidad, precio, pago, eliminar línea
- Al cambiar artículo se sugiere precio especial automáticamente
- Al eliminar la última línea de un albarán, el albarán también desaparece
- Líneas modificadas aparecen con fondo amarillo
- Endpoints nuevos: `PATCH /api/lineas`, `DELETE /api/lineas/{id}`

**Bug corregido:** `articuloCambiado()` usaba `albaran_id` donde debía usar `cliente_id` para consultar precios especiales.

---

### Entrega 8 — Pantalla de configuración + campos dinámicos
**Ficheros nuevos:** `static/pc/configuracion.html`
**Cambios:** `main.py`, `migrate.py`, `models.py`, `static/pc/comun.js`

- Tablas nuevas: `configuracion_campos`, `configuracion_ventas`
- Campos estándar registrados automáticamente como 🔒 indestructibles
- Pantalla `/configuracion` con árbol de selección para campos en ventas
- Límites configurables de campos por tabla
- Icono ⚙️ Config en el header de todas las pantallas PC
- Columna `extra TEXT` añadida a todas las tablas maestras y `lineas_venta`
- Campos extra aparecen dinámicamente en formularios de tablas maestras
- Consultas detecta y muestra columnas extra del resultado automáticamente
- Crear campo "Columna BD" ejecuta `ALTER TABLE` automáticamente

---

### Entrega 9 — Fix terminología + límites + perfiles de vista
**Cambios:** `main.py`, `migrate.py`, `static/pc/configuracion.html`, `static/pc/consultas.html`

- Renombrado: `fijo` → `Columna BD`, `volatil` → `JSON` (más claro)
- Campo test "zona_geografica" eliminado de la BD
- **Fix límites:** Columna BD archivada cuenta para el límite (sigue en BD), JSON archivado no cuenta
- Botón 🗑️ "Eliminar definitivo" solo en Columna BD archivada, con confirmación escribiendo el nombre
- JSON archivado: translúcido, recuperable con ♻️, sin botón eliminar
- Tabla nueva: `configuracion_parametros` con `max_columnas=5` y `max_json=10`
- Parámetros editables desde cabecera de la pantalla de configuración
- Tabla nueva: `perfiles_vista`
- Perfiles de vista en consultas: crear, aplicar, borrar perfiles por operario
- Barra de perfiles encima de los filtros en consultas
- **Fix bug:** `articuloCambiado()` en editor multilinea ahora usa `cliente_id` del dato (incluido en respuesta API)
- `tipo_pago` añadido al formulario de nueva venta PC
- Departamento de líneas históricas rellenado por migración

---

## NOTAS TÉCNICAS IMPORTANTES

### SQLite vs PostgreSQL
El proyecto usa SQLite en desarrollo. Para producción con múltiples usuarios concurrentes
se recomienda PostgreSQL. El cambio es una línea en `database.py`. Ver Pendiente 5 y 6.

### Migración idempotente
`migrate.py` se ejecuta en cada arranque y es seguro ejecutarlo múltiples veces.
Comprueba si cada cambio ya está aplicado antes de aplicarlo.

### Campos extra y el JSON `extra`
Los campos de tipo JSON se almacenan en la columna `extra` de cada tabla como un diccionario.
Si un campo se archiva, los datos siguen en el JSON de cada registro y reaparecen al reactivar.
Si una venta se realizó cuando el campo X estaba activo, ese valor queda en `lineas_venta.extra`
para siempre, independientemente de lo que pase con la configuración después.

### Precios especiales
La tabla `precios_especiales` tiene un precio por cada par (cliente_id, articulo_id).
Al crear una venta, el sistema consulta esa tabla. Si encuentra precio, lo usa y marca la línea
con `es_precio_especial=1`. Si no, usa el precio estándar del artículo.
Pendiente: pantalla de gestión visual de precios especiales.

### El campo `departamento` en lineas_venta
Se copia en el momento de la venta desde el operario. Si el operario cambia de departamento
o el departamento cambia de nombre, las ventas históricas mantienen el nombre original.
Esto es intencional — es historial, no una referencia dinámica.

### Perfiles de vista
Almacenados en `perfiles_vista` como JSON. Actualmente solo `consultas` tiene la barra de perfiles.
El drag & drop (pendiente) guardará anchos y orden en el perfil activo automáticamente.
Sin perfil activo, se muestran todas las columnas en orden por defecto.

---

## PENDIENTE — PERFILES MÓVIL, CARGA DE VEHÍCULO Y CUADRE

### Contexto

Los operarios de venta trabajan con un vehículo cargado de producto. El flujo completo es:
1. Por la mañana cargan el vehículo con material
2. Durante el día venden desde el vehículo
3. Al final del día cuadran stock físico y caja

Hay tres perfiles de operario móvil con necesidades distintas, más un perfil PC con control total.

---

### Perfil PC — Control total

Es la aplicación actual. Gestión completa de ventas, consultas, configuración, tablas maestras.
Sin restricciones de referencias ni flujo simplificado.

---

### Perfil Móvil 1 — 1 referencia fija

El operario siempre vende el mismo artículo. El flujo es mínimo:

```
Escanea QR operario  → logado
Escanea QR cliente   → cliente seleccionado
Introduce cantidad   → única interacción manual
Confirma pago        → venta registrada
```

La pantalla de artículo desaparece — el artículo está fijo en su perfil.
El botón por defecto es "Vender 1" — para casos excepcionales hay "Cambiar cantidad".

---

### Perfil Móvil 2 — Hasta 4 referencias

El operario vende entre 2 y 4 artículos distintos. El flujo:

```
Escanea QR operario  → logado
Elige artículo       → 4 botones grandes en pantalla, o escanea QR artículo
Escanea QR cliente   → cliente seleccionado
Introduce cantidad   → única interacción manual
Confirma pago        → venta registrada
```

La selección de artículo es visual — 4 botones grandes con nombre y foto opcional.
También acepta escaneo QR del artículo para mayor rapidez.

---

### Perfil Móvil 3 — Hasta 20 referencias

El operario vende un catálogo más amplio. El flujo:

```
Escanea QR operario  → logado
Escanea QR artículo  → artículo seleccionado (búsqueda opcional como fallback)
Escanea QR cliente   → cliente seleccionado
Introduce cantidad   → única interacción manual
Confirma pago        → venta registrada
```

Con 20 referencias no caben botones — el escáner QR es la vía principal.
Buscador de texto como fallback si no hay QR disponible.

---

### Escáner QR — implementación

Librería `jsQR` (JavaScript puro, sin instalación, sin app nativa).
Funciona en Chrome y Safari móvil desde el navegador.
Un solo fichero JS cargado desde CDN.

**Qué lleva cada QR:**

| QR | Contenido | Ejemplo |
|----|-----------|---------|
| Operario | `OP:OP-001` | Tarjeta personal del operario |
| Artículo | `ART:ART-003` | Pegatina en el producto o estantería |
| Cliente | `CLI:CLI-047` | Tarjeta del cliente o ficha |
| Carga | JSON firmado | Generado por el almacenero en el momento |

El formato es simple texto. Al leerlo, la app extrae el tipo y el código,
busca en la API y avanza automáticamente a la siguiente pantalla.

---

### Flujo de carga del vehículo

#### Lado almacenero (aplicativo pendiente de diseñar)

El almacenero registra la entrega:
- Selecciona operario destinatario
- Selecciona artículo y cantidad
- El sistema genera un QR temporal con la transacción

El QR contiene: `{"tipo":"carga","operario_id":2,"articulo_id":5,"cantidad":150,"ts":1234567890,"hash":"xxx"}`

El `hash` es una firma simple para evitar que alguien manipule el QR manualmente.

#### Lado operario (móvil)

El operario escanea el QR del almacenero.
La app valida el hash, registra la carga en su stock del vehículo y confirma.
Transacción completada sin teclear nada.

#### Tabla nueva: `stock_vehiculo`

```sql
CREATE TABLE stock_vehiculo (
    id            INTEGER PRIMARY KEY,
    operario_id   INTEGER REFERENCES operarios(id),
    articulo_id   INTEGER REFERENCES articulos(id),
    fecha         TEXT,
    tipo          TEXT,  -- 'carga' / 'venta' / 'devolucion' / 'cuadre'
    cantidad      REAL,  -- positivo=entrada, negativo=salida
    referencia    TEXT,  -- número de albarán o código de carga
    notas         TEXT
);
```

El stock actual del vehículo en cualquier momento es la suma de `cantidad`
filtrada por `operario_id` y `articulo_id` para el día o periodo.

---

### Cuadre al final del día

El operario abre la pantalla de cuadre desde su móvil. El sistema le muestra:

#### Cuadre de stock

| Artículo | Cargado | Vendido | Teórico | Físico | Diferencia |
|----------|---------|---------|---------|--------|------------|
| ART-003  | 150     | 87      | 63      | ___    | ___        |

El operario introduce el físico real. La diferencia queda registrada.

#### Cuadre de caja

| Concepto | Importe |
|----------|---------|
| Ventas contado registradas | 1.240,00 € |
| Efectivo declarado         | ___        |
| Diferencia                 | ___        |

---

### Tabla nueva: `cuadres_diarios`

```sql
CREATE TABLE cuadres_diarios (
    id              INTEGER PRIMARY KEY,
    operario_id     INTEGER REFERENCES operarios(id),
    fecha           TEXT,
    articulo_id     INTEGER REFERENCES articulos(id),  -- NULL para cuadre de caja
    tipo            TEXT,   -- 'stock' / 'caja'
    teorico         REAL,
    fisico          REAL,
    diferencia      REAL,
    notas           TEXT,
    cerrado_en      TEXT
);
```

---

### Aplicativo del almacenero (pendiente de definir)

Puede ser:
- Una pantalla adicional en la web PC (`/almacen`)
- Una pantalla móvil simplificada (`/movil/almacen`)
- Lo más probable: pantalla móvil, ya que el almacenero está en movimiento

Flujo del almacenero:
1. Selecciona operario destinatario
2. Selecciona artículo y cantidad (con escáner QR o buscador)
3. Genera QR de entrega
4. El operario lo escanea — transacción completada
5. El almacenero ve confirmación en pantalla

---

### Perfil de usuario en BD

Actualmente el perfil (1, 2 o 3 referencias) no está en la BD.
Hay que añadir a la tabla `operarios`:

```sql
ALTER TABLE operarios ADD COLUMN perfil_movil TEXT DEFAULT 'completo';
-- Valores: '1ref' / '4ref' / '20ref' / 'completo'
```

Y en la pantalla de trabajadores, un desplegable para asignar el perfil.
Al hacer login en el móvil, la app consulta el perfil y redirige a la pantalla correspondiente.

---

### Orden de implementación recomendado

1. Campo `perfil_movil` en operarios + desplegable en trabajadores.html
2. Escáner QR en el móvil (jsQR) — primero para login, luego para cliente y artículo
3. Perfil Móvil 1 (1 referencia) — el más simple, buen punto de partida
4. Tabla `stock_vehiculo` + registro de cargas
5. Perfil Móvil 2 (4 referencias)
6. Aplicativo almacenero — generador de QR de carga
7. Cuadre de fin de día (stock + caja)
8. Perfil Móvil 3 (20 referencias)


---

## PENDIENTE — COBRO CON TARJETA Y OPCIONES DE INTEGRACIÓN

### Contexto

Los operarios necesitan cobrar con tarjeta desde el móvil. El objetivo no es una
integración completa con el sistema de cobro sino capturar una señal mínima que
confirme que el cobro se intentó o se completó, para evitar que el operario olvide
cobrar y para cuadrar la caja al final del día.

---

### Opciones de hardware

**mPOS del banco (recomendado)**

Lector físico pequeño (tamaño bolsillo) que se conecta al móvil por bluetooth.
Lo proporciona el propio banco. Funciona con el contrato de datáfono existente
— las comisiones son las ya pactadas con el banco, sin coste extra por ser móvil.

Bancos españoles con solución mPOS: BBVA, CaixaBank, Santander, Sabadell, entre otros.
Consultar con el banco la disponibilidad y coste del lector (habitualmente gratuito
o de coste mínimo para clientes con datáfono).

**Intermediarios con API (SumUp, Stripe Terminal)**

Tienen API abierta para integración completa en apps de terceros.
Coste adicional: ~1,75% por transacción sobre las comisiones del banco.
Ventaja: integración automática total sin depender del banco.
Desventaja: coste extra acumulado en volumen alto de transacciones.

---

### Opciones de integración (de más a menos automática)

**Opción 1 — Captura de SMS del banco (recomendada para Android)**

El banco manda un SMS al móvil del operario en cada transacción aprobada.
Tu app escucha los SMS en segundo plano con permiso READ_SMS (Android).
Detecta el SMS por remitente (ej. "BBVA", "CAIXABANK") y palabras clave ("aprobado", "cobro").
Registra automáticamente en la venta: tipo_pago=tarjeta, estado=aprobado.

**Coste de los SMS:** cero. Son notificaciones del servicio de datáfono
que el banco ya envía — no hay coste adicional para el comercio.

**Limitación:** iOS no permite leer SMS a apps de terceros.
Para iPhone usar Opción 4.

**Implementación:**
```javascript
// Android WebView o app nativa con permiso READ_SMS
// Filtrar por remitente del banco y palabras clave
// Capturar importe si el formato lo permite
// Registrar en la venta activa del operario
```

**Pendiente de hacer antes de implementar:**
Capturar un SMS real del banco del cliente para conocer el formato exacto
del remitente y el texto. Cada banco tiene su propio formato.

---

**Opción 2 — Webhook del banco**

Algunos bancos notifican a una URL tuya cada vez que se procesa
una transacción en tu terminal. Tu servidor la recibe e identifica
al operario por el número de terminal.

Hay que preguntar al banco si tienen este servicio
("notificación de cobro", "aviso de transacción", "webhook TPV").
No todos los bancos lo ofrecen y los que lo hacen lo tienen
en contratos de cierto volumen.

---

**Opción 3 — Android Intents**

En Android, algunas apps de pago lanzan un Intent al terminar con el resultado.
Tu app puede escuchar ese Intent y recoger el estado automáticamente.
Requiere saber qué Intent lanza la app del banco concreta — hay que revisarlo
caso por caso ya que no todos los bancos lo documentan.

---

**Opción 4 — Confirmación manual (universal, iOS y Android)**

El operario pulsa "Cobrar con tarjeta" en tu app.
La app abre la del banco o el datáfono.
Al volver a tu app aparece una pantalla simple:

```
¿Se completó el cobro?
[ ✅ Sí, cobrado ]   [ ❌ No se pudo ]
```

Un toque. Queda registrado el intento y el resultado.
No es automático pero es rápido, fiable y funciona en cualquier dispositivo
y con cualquier banco sin ninguna integración técnica.

---

**Opción 5 — Lectura de portapapeles**

Algunas apps de datáfono copian el resultado al portapapeles al terminar.
Tu app lee el portapapeles al volver al primer plano y detecta el texto.
No es fiable — depende de cada app de banco. Descartada como opción principal.

---

### Impresión de tickets

Los mPOS modernos permiten enviar el recibo al cliente por:
- SMS (sin coste para el comercio)
- Email
- QR que el cliente escanea
- Impresora térmica bluetooth portátil (80-200€, marcas Star Micronics, Citizen, Bixolon)

**Integración con tu app:**
El ticket del cobro lo gestiona el datáfono del banco — no se toca.
El albarán de la venta (artículos, cantidades, precios) lo imprime tu app
directamente en la térmica bluetooth si el operario tiene una.
Son dos documentos complementarios — el recibo del banco y el albarán de entrega.

En Android hay librerías para imprimir en térmicas bluetooth.
En iPhone también pero con más restricciones de Apple.

---

### Impacto en el cuadre de caja

Con tarjeta como tipo de pago, el cuadre diario tiene tres columnas:

| Tipo | Ventas registradas | Declarado | Diferencia |
|------|-------------------|-----------|------------|
| Contado (efectivo) | 1.240,00 € | ___ | ___ |
| Tarjeta | 890,00 € | Automático si hay integración | — |
| Crédito | 3.200,00 € | No aplica | — |

Si la integración es automática (SMS o webhook), el importe de tarjeta
cuadra solo sin que el operario declare nada.
Si es manual (Opción 4), el operario confirma pero no introduce importe.

---

### Tipo de pago en la BD

Ampliar el campo `tipo_pago` en `lineas_venta` con los nuevos valores:

```
contado    → efectivo
tarjeta    → cobrado con tarjeta (confirmado)
tarjeta_intento → se intentó cobrar pero no se confirmó
credito    → a crédito, pendiente de cobro
```

---

### Orden de implementación recomendado

1. Añadir "Tarjeta" como opción de pago en móvil y PC (sin integración — Opción 4 manual)
2. Adaptar cuadre de caja para incluir tarjeta
3. Consultar con el banco si tienen webhook o SMS con formato conocido
4. Implementar captura de SMS (Android) si el formato del banco es estable
5. Valorar impresora térmica bluetooth según necesidad del negocio

