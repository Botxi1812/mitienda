# TABLAS DINÁMICAS — Plan de arquitectura y migración
> Revisión: 2026-03-17 — Incorpora principio de "nada hardcodeado" y eliminación limpia de tablas

---

## 1. Principio fundamental

**Una única fuente de verdad define todo el comportamiento del sistema.**
Ninguna pantalla, ningún endpoint, ningún componente debe saber de antemano
qué tablas existen. Todo se construye dinámicamente leyendo los metadatos.

**Consecuencia directa:** eliminar una tabla borra su bloque de metadatos y
desaparece automáticamente de la navegación, la configuración, las consultas,
la pantalla de ventas y cualquier otro lugar donde pudiera aparecer —
sin tocar una sola línea de código.

**Sobre los IDs en ventas:** los valores se graban como texto en el `extra` de
cada línea en el momento de la venta (snapshot). No se guardan IDs que
puedan quedar huérfanos si la tabla se elimina. Una venta histórica siempre
puede mostrar todos sus datos aunque la tabla origen ya no exista.

---

## 2. La fuente de verdad: metadatos en base de datos

Toda la estructura del proyecto vive en cuatro tablas de metadatos:

```
tabla_definiciones      → qué tablas existen y cómo se comportan
configuracion_campos    → qué campos tiene cada tabla
configuracion_ventas    → qué campos se copian en cada línea de venta
consultas_config        → qué columnas aparecen en la pantalla de consultas
```

Estas tablas son el equivalente a un JSON de configuración del proyecto,
con un bloque por tabla. La serialización JSON de un bloque completo sería:

```json
{
  "nombre": "clientes",
  "etiqueta": "Clientes",
  "etiqueta_singular": "Cliente",
  "icono": "👥",
  "tipo_relacion": "participa_venta",
  "padre_tabla": null,
  "en_nav": true,
  "orden_nav": 1,
  "en_venta_requerido": true,
  "es_sistema": true,
  "campos": [
    {
      "nombre": "codigo",
      "etiqueta": "Código",
      "tipo": "texto",
      "tipo_campo": "columna",
      "es_requerido": true,
      "es_unico": true,
      "es_bloqueado_venta": true,
      "en_ventas": true
    },
    {
      "nombre": "nombre",
      "etiqueta": "Nombre",
      "tipo": "texto",
      "tipo_campo": "columna",
      "es_requerido": true,
      "es_bloqueado_venta": true,
      "en_ventas": true
    },
    {
      "nombre": "ciudad",
      "etiqueta": "Ciudad",
      "tipo": "texto",
      "tipo_campo": "columna",
      "es_bloqueado_venta": false,
      "en_ventas": true
    }
  ],
  "consultas": [
    { "campo": "cliente_cod", "etiqueta": "Cód. Cliente", "ancho": 90, "en_default": true },
    { "campo": "cliente",     "etiqueta": "Cliente",      "ancho": 140, "en_default": true },
    { "campo": "ciudad",      "etiqueta": "Ciudad",       "ancho": 100, "en_default": true }
  ]
}
```

**Eliminar una tabla = borrar este bloque** de las cuatro tablas de metadatos
(+opcionalmente la tabla SQLite de datos). Todo lo demás se reconstruye solo.

---

## 3. Inventario completo de lo que está hardcodeado hoy

El subagente de análisis encontró ~80 referencias hardcodeadas. Estas son las
más críticas, organizadas por archivo:

### `main.py`
| Referencia hardcodeada | Línea aprox. | Reemplazar por |
|---|---|---|
| `TABLAS = ["clientes","articulos","operarios","departamentos"]` | 484 | Consulta a `tabla_definiciones` |
| `CAMPOS_LOCKED_VENTA = {'clientes':...}` | 49 | Columna `es_bloqueado_venta` en `configuracion_campos` |
| `if tabla == 'clientes': entity = cliente` | 210 | Bucle genérico sobre tablas participantes |
| `campos_extra_tabla(db, "operarios")` etc. | 106,120,131,142 | `campos_extra_tabla(db, tabla)` genérico |
| `linea_dict()` — 20 campos hardcodeados | 56-81 | Función genérica que lee de metadatos |
| Endpoints específicos `/api/clientes`, `/api/articulos`… | 104-143 | Alias del endpoint genérico |
| Rutas de página `/clientes`, `/articulos`… | 23-30 | Sirven `catalogo.html` con parámetro |

### `consultas.html`
| Referencia hardcodeada | Línea aprox. | Reemplazar por |
|---|---|---|
| `COLS_VISTA_DEFAULT = [...]` — 17 campos | 225 | `GET /api/consultas/config` |
| `COLS_LABELS = {...}` — 17 etiquetas | 232 | Incluido en `/api/consultas/config` |
| `ANCHO_DEFAULT = {...}` — 17 anchos | 241 | Incluido en `/api/consultas/config` |
| `clavesFijas = new Set([...])` — 22 campos | 330 | Campos con `es_sistema_venta=1` en metadatos |
| `Promise.all([fetch('/api/operarios'), fetch('/api/clientes')...])` | 298 | Dinámico según tablas con `en_filtros=1` |
| `renderCell()` — 17 casos `if/else` hardcodeados | 492 | Renderer genérico con `tipo` del campo |
| Opciones de búsqueda avanzada | 430 | Leídas de `consultas_config` |

### `configuracion.html`
| Referencia hardcodeada | Línea aprox. | Reemplazar por |
|---|---|---|
| `NOMBRES_TABLA = {clientes:..., articulos:...}` | 198 | Leído de `GET /api/tablas` |
| `CAMPOS_LOCKED_VENTA = {clientes: Set([...]),...}` | 301 | Flag `es_bloqueado_venta` en metadatos |
| `const tablas = ['clientes','articulos','operarios','departamentos']` | 238 | Leído de `GET /api/tablas` |
| Segunda instancia del array anterior en `renderArbolVentas()` | 309 | Ídem |

### `ventas.html`
| Referencia hardcodeada | Línea aprox. | Reemplazar por |
|---|---|---|
| `fetch('/api/clientes')` + `fetch('/api/articulos')` | 181 | Dinámico según `tablas?participa_venta=1` |
| `clientes = []`, `articulos = []` | 166 | `entidades = {}` (dict por tabla) |
| Selector de cliente hardcodeado | ~124 | Generado dinámicamente |
| Selector de artículo hardcodeado | ~296 | Generado dinámicamente |
| `cliente_id`, `articulo_id` en el body del POST | 334 | Dict genérico `{tabla: id_o_valor}` |

### `<nav>` en todos los HTML
Hardcodeada en: `ventas.html`, `consultas.html`, `configuracion.html`,
`clientes.html`, `articulos.html`, `trabajadores.html`, `departamentos.html`,
`login.html` (8 ficheros).
Reemplazar por: `renderNavDinamica()` en `comun.js` que lee `/api/tablas`.

---

## 4. Nueva tabla de metadatos: `tabla_definiciones`

```sql
CREATE TABLE tabla_definiciones (
    id                  INTEGER PRIMARY KEY,
    nombre              TEXT UNIQUE NOT NULL,
    -- ^ slug usado en URLs, API, SQLite. Solo [a-z][a-z0-9_]{0,49}

    etiqueta            TEXT NOT NULL,
    etiqueta_singular   TEXT NOT NULL,
    icono               TEXT DEFAULT '',

    -- Relación con otras tablas
    padre_tabla         TEXT DEFAULT NULL,
    -- ^ nombre de tabla en tabla_definiciones (o NULL si es raíz)
    tipo_relacion       TEXT DEFAULT 'libre',
    -- ^ 'libre'           → CRUD independiente
    -- ^ 'pertenece_a'     → su padre_tabla tiene un selector de esta tabla
    -- ^ 'participa_venta' → aparece como selector en la pantalla de venta
    -- ^ 'solo_referencia' → catálogo de valores, usado en campos tipo='lista'

    -- Campos especiales
    campo_principal     TEXT DEFAULT 'nombre',
    -- ^ campo que se muestra como etiqueta del registro (búsquedas, selectores)
    campo_secundario    TEXT DEFAULT '',
    -- ^ campo secundario en selectores (ej: codigo)

    -- Navegación
    en_nav              INTEGER DEFAULT 1,
    orden_nav           INTEGER DEFAULT 99,

    -- Ventas
    en_venta_requerido  INTEGER DEFAULT 0,
    -- ^ 1 = selector obligatorio en la pantalla de venta (como clientes y artículos)
    -- ^ 0 = selector opcional o no aparece

    -- Control
    es_sistema          INTEGER DEFAULT 0,
    -- ^ 1 = tabla del sistema, no se puede eliminar desde la UI
    activa              INTEGER DEFAULT 1,
    -- ^ 0 = borrado lógico (la tabla SQLite se mantiene, los datos históricos siguen)

    extra               TEXT DEFAULT '{}'
)
```

### Valores iniciales para las tablas actuales

| nombre | tipo_relacion | padre_tabla | en_venta_requerido | es_sistema |
|---|---|---|---|---|
| clientes | participa_venta | NULL | 1 | 1 |
| articulos | participa_venta | NULL | 1 | 1 |
| operarios | libre | NULL | 0 | 1 |
| departamentos | pertenece_a | operarios | 0 | 1 |

---

## 5. Extensión de `configuracion_campos`

Añadir las columnas que hoy están hardcodeadas en el código:

```sql
-- Nuevas columnas en configuracion_campos:
ALTER TABLE configuracion_campos ADD COLUMN tabla_id      INTEGER REFERENCES tabla_definiciones(id);
ALTER TABLE configuracion_campos ADD COLUMN es_requerido  INTEGER DEFAULT 0;
ALTER TABLE configuracion_campos ADD COLUMN es_unico      INTEGER DEFAULT 0;
ALTER TABLE configuracion_campos ADD COLUMN es_bloqueado_venta INTEGER DEFAULT 0;
-- ^ reemplaza el dict CAMPOS_LOCKED_VENTA hardcodeado en main.py y configuracion.html
```

### Valores de `es_bloqueado_venta` para campos actuales

| tabla | campo | es_bloqueado_venta | Razón |
|---|---|---|---|
| clientes | codigo | 1 | Identifica al cliente en la venta |
| clientes | nombre | 1 | Identifica al cliente en la venta |
| articulos | codigo | 1 | Identifica el artículo en la venta |
| articulos | descripcion | 1 | Identifica el artículo en la venta |
| operarios | numero | 1 | Identifica al operario en la venta |
| operarios | nombre | 1 | Identifica al operario en la venta |
| departamentos | nombre | 1 | Identificador único del departamento |
| clientes | ciudad | 0 | Configurable |
| clientes | telefono | 0 | Configurable |
| clientes | email | 0 | Configurable |
| articulos | categoria | 0 | Configurable |
| articulos | precio | 0 | Configurable |
| operarios | telefono | 0 | Configurable |

---

## 6. Nueva tabla: `consultas_config`

Reemplaza `COLS_VISTA_DEFAULT`, `COLS_LABELS` y `ANCHO_DEFAULT` hardcodeados
en `consultas.html`:

```sql
CREATE TABLE consultas_config (
    id            INTEGER PRIMARY KEY,
    campo         TEXT NOT NULL,
    -- ^ nombre del campo tal como aparece en linea_dict() / extra de la línea
    etiqueta      TEXT NOT NULL,
    tabla_origen  TEXT DEFAULT NULL,
    -- ^ tabla de donde proviene (para saber si es un campo dinámico o del sistema)
    -- ^ NULL = campo propio de lineas_venta (cantidad, precio_unitario, importe...)
    ancho_default INTEGER DEFAULT 120,
    en_default    INTEGER DEFAULT 0,
    -- ^ 1 = aparece en la vista por defecto sin que el usuario lo active
    orden         INTEGER DEFAULT 99,
    es_sistema    INTEGER DEFAULT 0,
    -- ^ 1 = columna del sistema (siempre disponible, no se puede eliminar)
    activa        INTEGER DEFAULT 1
)
```

### Contenido inicial (equivale al `COLS_VISTA_DEFAULT` actual)

```
albaran           Albarán          NULL    90   en_default=1  es_sistema=1
fecha             Fecha            NULL    130  en_default=1  es_sistema=1
operario_num      Nº Op.           operarios  55  en_default=1  es_sistema=1
operario          Operario         operarios  120 en_default=1  es_sistema=1
departamento      Depto.           NULL    100  en_default=1  es_sistema=1
cliente_cod       Cód. Cliente     clientes  90  en_default=1  es_sistema=1
cliente           Cliente          clientes  140 en_default=1  es_sistema=1
ciudad            Ciudad           clientes  100 en_default=1  es_sistema=0
articulo_cod      Cód. Art.        articulos  80  en_default=1  es_sistema=1
articulo          Artículo         articulos  150 en_default=1  es_sistema=1
cantidad          Cant.            NULL    60   en_default=1  es_sistema=1
precio_unitario   Precio unit.     NULL    100  en_default=1  es_sistema=1
importe           Importe          NULL    100  en_default=1  es_sistema=1
tipo_pago         Pago             NULL    80   en_default=1  es_sistema=1
especial          Precio esp.      NULL    80   en_default=0  es_sistema=0
modificado_por    Modificado por   NULL    110  en_default=0  es_sistema=0
fecha_modificacion Fecha mod.      NULL    120  en_default=0  es_sistema=0
```

Cuando se crea una tabla nueva con `participa_venta=1`, sus campos configurados
se insertan automáticamente en `consultas_config` con `en_default=0` y `activa=1`.
Cuando se elimina la tabla, sus filas en `consultas_config` pasan a `activa=0`.

---

## 7. Eliminación de una tabla: cascade completo

Cuando el usuario elimina una tabla (solo posible si `es_sistema=0`):

```
1. tabla_definiciones          → activa = 0  (borrado lógico)
2. configuracion_campos        → activa = 0  (todos los campos de esa tabla)
3. configuracion_ventas        → borrar filas (los campos ya no se copian)
4. consultas_config            → activa = 0  (las columnas desaparecen de consultas)
5. perfiles_vista              → borrar perfiles cuya pantalla = nombre de la tabla
6. Tabla SQLite de datos       → OPCIONAL: DROP TABLE o mantener para histórico
                                 Recomendado: mantener (los datos no hacen daño)
                                 El usuario decide en el wizard de eliminación
```

**Qué pasa automáticamente en el frontend:**
- La nav ya no incluye esa tabla (lee `/api/tablas?activa=1`)
- La config no muestra esa tabla (lee `/api/tablas`)
- Las consultas no muestran esas columnas (leen `/api/consultas/config?activa=1`)
- La pantalla de ventas no muestra ese selector (lee `/api/tablas?participa_venta=1`)
- Los datos históricos en `lineas_venta.extra` permanecen intactos

**Por qué los datos históricos sobreviven:**
Los valores se grabaron como texto en `extra` en el momento de la venta.
No son IDs que apunten a registros que pueden desaparecer.
Una venta que registró `{"zona": "Norte", "proveedor": "ACME"}` sigue mostrando
esos valores aunque las tablas `zonas` y `proveedores` hayan sido eliminadas.

---

## 8. Arquitectura de `lineas_venta` para el futuro

### Situación actual (problema)
`lineas_venta` tiene `cliente_id` y `articulo_id` como FKs hardcodeadas.
Si se elimina la tabla `clientes`, estas FKs quedan huérfanas.

### Solución: doble registro para tablas participantes

Para las **tablas sistema** (`clientes`, `articulos`), mantener las columnas FK
porque existen garantías de que estas tablas no se eliminarán (`es_sistema=1`).
Además, sus campos configurados ya se snapshottean en `extra` (mecanismo actual).

Para las **tablas dinámicas** que participan en ventas:
- **NO** añadir una columna FK a `lineas_venta` por cada tabla nueva
- Guardar en `extra` tanto el identificador como los valores:
  ```json
  {
    "proveedor_id": 12,
    "proveedor_nombre": "ACME Suministros",
    "zona_nombre": "Norte"
  }
  ```
- El `_id` en extra es opcional (para facilitar búsquedas mientras la tabla exista)
- Los valores de texto son el dato real que sobrevive si la tabla se elimina

### `linea_dict()` genérico futuro

En lugar de 20 campos hardcodeados, construir el dict dinámicamente:

```python
def linea_dict(l, consultas_cfg):
    # Campos fijos de lineas_venta (siempre presentes)
    base = {
        "id": l.id,
        "albaran": l.albaran.numero,
        "albaran_id": l.albaran_id,
        "fecha": l.albaran.fecha.strftime("%d/%m/%Y %H:%M"),
        "cantidad": l.cantidad,
        "precio_unitario": l.precio_unitario,
        "importe": l.importe,
        "tipo_pago": l.tipo_pago or "",
        "es_precio_especial": l.es_precio_especial,
        "departamento": l.departamento or "",
        "modificado_por": l.modificado_por or "",
        "fecha_modificacion": l.fecha_modificacion or "",
    }
    # Campos de tablas participantes sistema (JOINs SQL — tablas garantizadas)
    sistema = {
        "operario_num": l.albaran.operario.numero,
        "operario": l.albaran.operario.nombre,
        "cliente_id": l.albaran.cliente_id,
        "cliente_cod": l.albaran.cliente.codigo,
        "cliente": l.albaran.cliente.nombre,
        "articulo_id": l.articulo_id,
        "articulo_cod": l.articulo.codigo,
        "articulo": l.articulo.descripcion,
    }
    # Campos snapshotted en extra (overriden sobre sistema si existen)
    extra = parse_extra(getattr(l, 'extra', None))
    return {**base, **sistema, **extra}
    # extra al final: si 'ciudad' está en extra (snapshot), sobreescribe el valor
    # en vivo de sistema. Si no está (venta antigua), sistema devuelve el vivo.
```

---

## 9. API genérica completa

### Endpoints de metadatos

```
GET  /api/tablas
     ?activa=1           → lista de tablas (para nav, config, ventas...)
     ?participa_venta=1  → tablas que aparecen en la pantalla de venta
     ?en_nav=1           → tablas que aparecen en la navegación
     ?padre_tabla=X      → tablas hijo de una tabla concreta

GET  /api/tablas/{nombre}/config
     → objeto completo: metadatos + campos + configuracion_ventas + consultas_config

POST /api/tablas              → crear tabla nueva (wizard)
PUT  /api/tablas/{nombre}     → editar metadatos
DELETE /api/tablas/{nombre}   → eliminación con cascade (solo si !es_sistema)

GET  /api/consultas/config    → configuración de columnas para consultas.html
```

### Endpoints CRUD genéricos

```
GET    /api/entidad/{tabla}
       ?q=texto             → búsqueda en campo_principal + campo_secundario
       ?padre_id=X          → filtrar por tabla padre
       ?campo=X&valor=Y     → filtrar por campo concreto

GET    /api/entidad/{tabla}/{id}

POST   /api/entidad/{tabla}
       body: { campo1: valor1, campo2: valor2, ... }
       → valida requeridos y únicos desde configuracion_campos
       → separa automáticamente campos columna vs campos extra (JSON)

PUT    /api/entidad/{tabla}/{id}
       body: igual que POST

DELETE /api/entidad/{tabla}/{id}
       → valida que no tiene hijos en otras tablas
       → valida que no está referenciado en lineas_venta (tablas sistema)
```

### Seguridad anti-inyección SQL (obligatorio en todos los endpoints genéricos)

```python
import re

def validar_tabla(nombre: str, db: Session):
    # 1. Formato del slug
    if not re.match(r'^[a-z][a-z0-9_]{0,49}$', nombre):
        raise HTTPException(400, "Nombre de tabla inválido")
    # 2. Existe en tabla_definiciones y está activa
    row = db.execute(
        text("SELECT id FROM tabla_definiciones WHERE nombre=:n AND activa=1"),
        {"n": nombre}
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Tabla '{nombre}' no encontrada")
    return row[0]
```

---

## 10. Frontend completamente dinámico

### `comun.js` — funciones nuevas necesarias

```javascript
// Carga la lista de tablas y renderiza la nav
async function renderNavDinamica(tablaActual) {
    const tablas = await fetch('/api/tablas?en_nav=1').then(r => r.json());
    // Construye el <nav> dinámicamente
    // Marca tablaActual como active
    // Usa tablas[i].icono, tablas[i].etiqueta, tablas[i].nombre
}

// Carga la config completa de una tabla (metadatos + campos)
async function cargarConfigTabla(nombreTabla) {
    return fetch(`/api/tablas/${nombreTabla}/config`).then(r => r.json());
}

// Genera el formulario modal a partir de config.campos
function renderModalCampos(campos, registro) {
    // Para cada campo activo, genera el input apropiado según campo.tipo:
    //   texto → <input type="text">
    //   numero → <input type="number">
    //   fecha → <input type="date">
    //   lista → <select> con campo.opciones
    //   referencia → <select> dinámico cargado de /api/entidad/{campo.tabla_ref}
}
```

### `catalogo.js` — renderer genérico completo

```javascript
async function initCatalog(nombreTabla) {
    // 1. Cargar config de la tabla
    const config = await cargarConfigTabla(nombreTabla);

    // 2. Renderizar nav dinámica
    await renderNavDinamica(nombreTabla);

    // 3. Renderizar título y toolbar con config.etiqueta
    renderToolbar(config);

    // 4. Renderizar cabecera de tabla con config.campos (los visibles)
    renderCabecera(config.campos);

    // 5. Cargar datos y renderizar filas
    const datos = await fetch(`/api/entidad/${nombreTabla}`).then(r => r.json());
    renderTabla(datos, config.campos);

    // 6. Configurar modal de edición con config.campos
    renderModal(config);

    // 7. Si config.hijos tiene tablas, preparar subsección de hijos en el modal
    if (config.hijos.length) renderSeccionHijos(config.hijos);

    // 8. Cargar perfiles de vista (ya existe en comun.js)
    cargarPerfiles(nombreTabla);
}
```

### `ventas.html` — sin referencias hardcodeadas

```javascript
async function cargarDatosVenta() {
    // 1. Qué tablas participan en la venta (y cuáles son obligatorias)
    const tablasVenta = await fetch('/api/tablas?participa_venta=1').then(r => r.json());

    // 2. Para cada tabla, cargar sus registros y renderizar el selector
    const entidades = {};
    for (const t of tablasVenta) {
        entidades[t.nombre] = await fetch(`/api/entidad/${t.nombre}`).then(r => r.json());
        renderSelectorEntidad(t, entidades[t.nombre]);
    }
    return { tablasVenta, entidades };
}

async function confirmarVenta() {
    // El body ya no tiene cliente_id / articulo_id hardcodeados
    // Tiene un dict genérico de selecciones:
    const selecciones = {};
    for (const t of tablasVenta) {
        const selector = document.getElementById(`select-${t.nombre}`);
        if (selector && selector.value) selecciones[t.nombre] = parseInt(selector.value);
    }
    const body = {
        operario_id: operario.id,
        selecciones,  // { clientes: 5, articulos: 12, proveedores: 3, ... }
        lineas: lineas.map(l => ({ ...l }))
    };
    // ...
}
```

### `consultas.html` — sin hardcoding

```javascript
async function cargarConfigConsultas() {
    // Reemplaza COLS_VISTA_DEFAULT, COLS_LABELS, ANCHO_DEFAULT, clavesFijas
    const cfg = await fetch('/api/consultas/config').then(r => r.json());
    COLS_SISTEMA   = cfg.filter(c => c.es_sistema);
    COLS_DEFAULT   = cfg.filter(c => c.en_default);
    COLS_LABELS    = Object.fromEntries(cfg.map(c => [c.campo, c.etiqueta]));
    ANCHO_DEFAULT  = Object.fromEntries(cfg.map(c => [c.campo, c.ancho_default]));
    return cfg;
}
```

### `configuracion.html` — sin hardcoding

```javascript
async function cargarConfig() {
    // Reemplaza NOMBRES_TABLA, CAMPOS_LOCKED_VENTA, los dos arrays de tablas
    const [campos, params, tablas] = await Promise.all([
        fetch('/api/config/campos').then(r => r.json()),
        fetch('/api/config/parametros').then(r => r.json()),
        fetch('/api/tablas').then(r => r.json()),      // ← NUEVO
    ]);
    // NOMBRES_TABLA se construye dinámicamente desde tablas
    // CAMPOS_LOCKED se lee del flag es_bloqueado_venta en campos
    // La lista de tablas del grid viene de tablas[]
}
```

---

## 11. Creación de una tabla nueva: flujo completo

### Wizard en la pantalla de configuración

```
Paso 1 — Identidad
  Nombre visible (etiqueta): "Regiones"
  Nombre singular: "Región"
  Icono: 🗺️
  Slug (auto): "regiones"

Paso 2 — Tipo y relación
  Tipo: [ libre | pertenece_a | solo_referencia ]
  Si pertenece_a → seleccionar tabla padre (dropdown de tabla_definiciones)
  ¿Aparece en ventas? [ sí / no ]
  ¿Si aparece en ventas, es obligatoria? [ sí / no ]

Paso 3 — Primer campo
  Nombre visible: "Nombre"
  Tipo: texto (fijo para el primer campo)
  Este campo es el campo_principal de la tabla.

Paso 4 — Confirmación y creación
```

### Lo que ejecuta el backend al crear

```python
# 1. Validar slug único y formato
# 2. INSERT en tabla_definiciones
# 3. CREATE TABLE {slug} (id INTEGER PRIMARY KEY, extra TEXT DEFAULT '{}')
# 4. ALTER TABLE {slug} ADD COLUMN {primer_campo} TEXT DEFAULT ''
# 5. INSERT en configuracion_campos (primer campo, es_estandar=1, es_requerido=1)
# 6. Si tiene padre_tabla:
#    ALTER TABLE {slug} ADD COLUMN {padre_tabla}_id INTEGER REFERENCES {padre_tabla}(id)
# 7. Si participa en ventas:
#    INSERT en configuracion_ventas para todos sus campos es_bloqueado_venta=1
#    INSERT en consultas_config para sus campos con en_default=0
```

---

## 12. Fases de migración (revisadas)

### FASE 0 — Crear las tablas de metadatos y poblarlas
**Archivos:** `migrate.py`
**Riesgo:** ninguno (no toca pantallas)

1. Crear `tabla_definiciones` con los 4 valores iniciales
2. Añadir columnas a `configuracion_campos`: `tabla_id`, `es_requerido`, `es_unico`, `es_bloqueado_venta`
3. Rellenar los nuevos flags para campos existentes (ver tabla en sección 5)
4. Crear `consultas_config` con los 17 valores iniciales (ver sección 6)
5. Crear endpoint `GET /api/tablas` en `main.py`
6. Crear endpoint `GET /api/tablas/{nombre}/config` en `main.py`
7. Crear endpoint `GET /api/consultas/config` en `main.py`

**Verificación:** los tres endpoints devuelven datos correctos antes de avanzar.

---

### FASE 1 — Nav dinámica en todos los HTML
**Archivos:** `comun.js`, todos los HTML con `<nav>`
**Riesgo:** bajo — si falla, se ve la nav vacía

1. Añadir `renderNavDinamica(tablaActual)` en `comun.js`
2. Reemplazar `<nav class="nav-links">...</nav>` hardcodeada en los 8 HTML
   por un `<nav id="nav-principal"></nav>` vacío
3. Llamar a `renderNavDinamica()` en el `initHeader()` existente de `comun.js`

**Verificación:** la nav se ve igual que antes en todas las páginas.

---

### FASE 2 — `configuracion.html` sin hardcoding
**Archivos:** `configuracion.html`, `main.py`
**Riesgo:** bajo — solo afecta a la pantalla de config

1. Eliminar `NOMBRES_TABLA`, `CAMPOS_LOCKED_VENTA`, los dos arrays `['clientes',...]`
2. Leer `tablas` de `GET /api/tablas` en `cargar()`
3. Construir `NOMBRES_TABLA` dinámicamente desde `tablas`
4. Construir `LOCKED` dinámicamente desde el flag `es_bloqueado_venta` en `campos`
5. El grid de tablas (`renderConfigGrid`) itera sobre `tablas` de la API
6. El árbol de ventas (`renderArbolVentas`) itera sobre `tablas` de la API
7. Añadir sección "Tablas" al config (lista de `tabla_definiciones` con botón "+ Nueva tabla")

**Verificación:** añadir/quitar una tabla de `tabla_definiciones` y verificar que
la pantalla de configuración la muestra/oculta automáticamente.

---

### FASE 3 — API CRUD genérica
**Archivos:** `main.py`
**Riesgo:** bajo — los endpoints específicos siguen existiendo

1. Crear `GET /api/entidad/{tabla}` — listado genérico con extra
2. Crear `POST /api/entidad/{tabla}` — creación genérica
3. Crear `PUT /api/entidad/{tabla}/{id}` — actualización genérica
4. Crear `DELETE /api/entidad/{tabla}/{id}` — eliminación con validación
5. Los endpoints específicos (`/api/clientes`, etc.) pasan a llamar internamente
   al genérico (o simplemente conviven como aliases)

**Verificación:** verificar paridad de datos entre `/api/clientes`
y `/api/entidad/clientes` para todos los registros.

---

### FASE 4 — `catalogo.js` renderer genérico
**Archivos nuevos:** `static/pc/catalogo.js`, `static/pc/catalogo.html`
**Riesgo:** medio — crear en paralelo, no tocar los HTML existentes aún

1. Crear `catalogo.js` con `initCatalog(nombreTabla)`
2. Crear `catalogo.html` (wrapper mínimo que llama a `initCatalog`)
3. Añadir ruta `GET /catalogo` en `main.py`
4. Probar `/catalogo?tabla=departamentos` → paridad con `/departamentos`
5. Probar `/catalogo?tabla=clientes` → paridad con `/clientes`

**Verificación:** paridad funcional completa (CRUD, perfiles, campos extra, búsqueda)
con cada uno de los 4 catálogos existentes antes de migrar.

---

### FASE 5 — Migrar los 4 HTML al wrapper mínimo
**Archivos:** `clientes.html`, `articulos.html`, `trabajadores.html`, `departamentos.html`
**Riesgo:** medio — fácil revertir si hay problemas

Orden recomendado (de menor a mayor uso): departamentos → trabajadores → articulos → clientes.
Para cada uno:
1. Reemplazar contenido por wrapper de ~10 líneas
2. Verificar que `/clientes` funciona igual que antes
3. Si hay algún comportamiento especial, documentarlo como excepción temporal

---

### FASE 6 — `consultas.html` sin hardcoding
**Archivos:** `consultas.html`, `main.py`
**Riesgo:** medio — afecta a la pantalla más compleja del proyecto

1. Eliminar `COLS_VISTA_DEFAULT`, `COLS_LABELS`, `ANCHO_DEFAULT`, `clavesFijas`
2. Cargar toda la config desde `GET /api/consultas/config`
3. `renderCell()` pasa de 17 `if/else` hardcodeados a un switch por `tipo` del campo
4. Los filtros de búsqueda avanzada se construyen desde `consultas_config`
5. Los selectores de búsqueda (clientes, operarios, artículos) se generan dinámicamente
   leyendo qué tablas tienen `en_filtros=1` (nuevo flag en `tabla_definiciones`)

**Verificación:** misma experiencia de usuario que antes. Luego, añadir una tabla
dinámica con `participa_venta=1` y verificar que aparece automáticamente en consultas.

---

### FASE 7 — `ventas.html` sin hardcoding
**Archivos:** `ventas.html`, `main.py` (`crear_albaran`)
**Riesgo:** alto — afecta al flujo principal de negocio. Hacer con mucho cuidado.

1. Eliminar referencias a `clientes`, `articulos` hardcodeadas
2. Cargar tablas participantes desde `/api/tablas?participa_venta=1`
3. Renderizar selectores dinámicamente para cada tabla
4. `clientes` y `articulos` siguen siendo las dos tablas con `en_venta_requerido=1`
5. Actualizar `AlbaranIn` en `main.py`:
   - Reemplazar `cliente_id: int` y `operario_id: int` por `selecciones: Dict[str, int]`
   - Mantener `cliente_id` y `operario_id` como campos calculados desde `selecciones`
     durante el período de transición
6. `crear_albaran()` usa un bucle genérico para snapshot de campos participantes

**Verificación:** venta completa con las tablas actuales funciona igual. Luego crear
una tabla nueva con `participa_venta=1` y verificar que aparece en la venta.

---

### FASE 8 — Creación de tablas desde UI (wizard)
**Archivos:** `configuracion.html`, `main.py`
**Riesgo:** bajo (funcionalidad nueva, no modifica lo existente)

1. Añadir sección "Tablas" a `configuracion.html` con lista y botón "+ Nueva tabla"
2. Crear modal/wizard de 4 pasos (ver sección 11)
3. Crear `POST /api/tablas` con la lógica de creación (ver sección 11)
4. Crear `DELETE /api/tablas/{nombre}` con cascade (ver sección 7)
5. La nav se actualiza automáticamente al crear/eliminar (ya dinámica desde fase 1)

---

### FASE 9 — Tablas con relación padre-hijo en el CRUD
**Archivos:** `catalogo.js`
**Riesgo:** bajo (funcionalidad nueva)

Cuando una tabla tiene `padre_tabla`, el modal de edición del padre
muestra los hijos relacionados. Ejemplo: abrir un trabajador → ver/editar
sus departamentos asignados desde el mismo modal.

---

## 13. Qué nunca estará hardcodeado una vez completado

| Elemento | Estado actual | Estado final |
|---|---|---|
| Lista de tablas | hardcodeada en 6 sitios | `GET /api/tablas` |
| Nav de cada página | 8 copias hardcodeadas | `renderNavDinamica()` |
| Campos de cada tabla | hardcodeados en cada HTML | `GET /api/tablas/{t}/config` |
| Columnas de consultas | 3 constantes JS hardcodeadas | `GET /api/consultas/config` |
| Campos bloqueados en ventas | dict duplicado Python+JS | Flag `es_bloqueado_venta` en BD |
| Tablas que aparecen en config | array hardcodeado | `GET /api/tablas` |
| Tablas que aparecen en ventas | fetch hardcodeados | `GET /api/tablas?participa_venta=1` |
| Modal de edición de cada tabla | HTML hardcodeado por tabla | Generado desde `config.campos` |
| Validaciones de campos | lógica específica por tabla | Flags en `configuracion_campos` |
| Selectores en búsqueda avanzada | opciones hardcodeadas | `GET /api/consultas/config` |

---

## 14. Qué permanece específico (excepciones justificadas)

Algunos elementos mantienen lógica específica porque son parte del núcleo
del negocio y no tiene sentido generalizarlos:

| Elemento | Por qué es excepción |
|---|---|
| `precios_especiales` (cliente × artículo) | Lógica de negocio muy específica, no generalizable fácilmente |
| Login / autenticación de operarios | Flujo propio, no es un catálogo |
| Lógica de saneamiento (modificado_por, fecha_modificacion) | Funcionalidad específica de lineas_venta |
| Albaranes (numeración, fecha) | Estructura core de la venta, no dinámica |
| Pantalla móvil (`static/movil/`) | Evoluciona por separado |
| SQLAlchemy models para tablas sistema | Se mantienen por rendimiento y relaciones ORM |

---

## 15. Exportar / importar la configuración del proyecto

Una vez que toda la configuración vive en `tabla_definiciones` +
`configuracion_campos` + `consultas_config`, es trivial exportar
o importar la estructura completa del proyecto:

```
GET  /api/config/export   → JSON completo con todas las tablas y sus campos
POST /api/config/import   → recrea toda la estructura desde un JSON
```

Esto permite:
- Hacer backup de la configuración sin hacer backup de los datos
- Clonar la estructura a una nueva instalación
- Compartir configuraciones entre instalaciones del mismo negocio
- Control de versiones de la estructura del proyecto

---

## 16. Orden de ejecución y dependencias

```
FASE 0  Metadatos en BD + endpoints de config    ← SIN ESTO nada funciona
FASE 1  Nav dinámica                              ← Necesita FASE 0
FASE 2  Configuracion.html dinámico              ← Necesita FASE 0
FASE 3  API CRUD genérica                         ← Necesita FASE 0
FASE 4  catalogo.js (nuevo, en paralelo)          ← Necesita FASE 3
FASE 5  Migrar los 4 HTML a wrappers              ← Necesita FASE 4 verificada
FASE 6  Consultas.html dinámico                   ← Necesita FASE 0 + FASE 3
FASE 7  Ventas.html dinámico                      ← Necesita FASE 3 + FASE 6
FASE 8  Crear tablas desde UI                     ← Necesita FASES 1-5
FASE 9  Relaciones padre-hijo en CRUD             ← Necesita FASE 8
```

Las fases 0-3 son **infraestructura** (invisible para el usuario).
Las fases 4-5 son **migración** (el usuario no nota diferencia).
Las fases 6-7 son **refactor** (el usuario no nota diferencia).
Las fases 8-9 son **funcionalidad nueva**.

---

*Este documento es la referencia de arquitectura. Cualquier decisión de implementación
que genere código hardcodeado que no aparezca en la sección 14 debe ser cuestionada.*
