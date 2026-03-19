# Mi Tienda — Manual completo y pendientes

> **Última actualización: 2026-03-16**
> Estado: Pendientes 1–4 implementados y cerrados. Quedan pendientes 5 y 6 (cloud).

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
- **[NUEVO]** Redimensionar columnas en consultas: arrastra el borde derecho de cualquier cabecera
- **[NUEVO]** Reordenar columnas en consultas: arrastra la cabecera entera a otra posición
- **[NUEVO]** Filtros dinámicos en consultas: tras buscar, aparecen selectores para filtrar por campos extra del resultado (sin nueva llamada al servidor)
- **[NUEVO]** Búsqueda avanzada sin fecha: botón 🔍 Avanzado en consultas, busca en todo el histórico por cualquier campo
- Gestión de clientes, artículos, trabajadores, departamentos
- **[NUEVO]** Perfiles de vista en Clientes, Artículos, Trabajadores y Departamentos (igual que en Consultas): guardar qué columnas ver, con checkboxes por columna
- Configuración de campos extra por tabla (Columna BD y JSON)
- Campos extra aparecen automáticamente en formularios y en la rejilla de consultas
- Perfiles de vista en consultas (con drag & drop, anchos y orden guardados en el perfil)
- Parámetros configurables (máx. columnas y JSON por tabla)

### Lo que queda pendiente

1. **Subir a Railway** — para acceder desde cualquier sitio sin estar en casa
2. **Migrar a PostgreSQL** — cuando el volumen lo requiera

---

## PENDIENTES TÉCNICOS DETALLADOS (para Claude)

### ✅ Pendiente 1 — Drag & drop de columnas en consultas — IMPLEMENTADO

**Implementado el 2026-03-16.**

Fichero afectado: `static/pc/consultas.html`

**Qué hace:**
- Cada `<th>` de vista normal tiene un `<div class="resize-handle">` en su borde derecho. Al arrastrar, cambia el ancho de esa columna mediante un `<colgroup>` dinámico (`table-layout:fixed`).
- Las cabeceras son `draggable="true"`. Arrastrar una cabecera sobre otra reordena `columnasOrden[]` y re-renderiza la tabla.
- Al terminar de redimensionar o reordenar, si hay un perfil activo se llama a `guardarConfigPerfil()` que persiste en la API.
- Al aplicar un perfil, se restauran anchos (`anchos{}`) y orden (`columnasOrden[]`) desde `p.config.columnas`.

---

### ✅ Pendiente 2 — Filtros dinámicos fase 2 — IMPLEMENTADO

**Implementado el 2026-03-16.**

Fichero afectado: `static/pc/consultas.html`

**Qué hace:**
- Al final de `buscar()`, se detectan los valores únicos de cada campo extra en el resultado y se construyen `<select>` dinámicos dentro de `#filtros-extra`.
- `filtrarExtra()` filtra el array `datos` en memoria y llama a `renderTabla(filtrados)`.
- Si no hay campos extra en el resultado, `#filtros-extra` se oculta.

---

### ✅ Pendiente 3 — Búsqueda avanzada sin fecha conocida — IMPLEMENTADO

**Implementado el 2026-03-16.**

Ficheros afectados: `main.py`, `static/pc/consultas.html`

**Backend:**
- Nuevo endpoint `GET /api/ventas/buscar_campo?campo=X&valor=Y`
- Valida `campo` con regex `^[a-z_][a-z0-9_]*$` para evitar inyección SQL
- Busca en el JSON `extra` de `lineas_venta` con LIKE (compatible con todas las versiones de SQLite)
- Si `campo` es una columna real de `lineas_venta`, busca también con igualdad directa
- Devuelve hasta 500 líneas con el formato completo de `linea_dict`

**Frontend:**
- Botón **🔍 Avanzado** en la barra de acciones de filtros
- Panel naranja desplegable con `<select>` de campo e `<input>` de valor
- El select se inicializa con campos estándar (tipo_pago, departamento, modificado_por) y se actualiza con los extras tras cada búsqueda
- Al buscar, reemplaza `datos` y llama a `renderTabla()` y `renderResumen()`

---

### ✅ Pendiente 4 — Perfiles en el resto de pantallas — IMPLEMENTADO

**Implementado el 2026-03-16.**

Ficheros afectados: `comun.css`, `comun.js`, `clientes.html`, `articulos.html`, `trabajadores.html`, `departamentos.html`

**Arquitectura:**

En `comun.js` se añadieron 4 helpers genéricos de API:
- `apiCargarPerfiles(pantalla, operario_id)`
- `apiCrearPerfil(pantalla, operario_id, nombre, config)`
- `apiActualizarPerfil(perfil_id, pantalla, operario_id, nombre, config)`
- `apiBorrarPerfil(perfil_id)`
- `renderSelectPerfiles(perfiles, activo_id)` — rellena el `<select id="perfil-select">`

En `comun.css` se añadieron los estilos compartidos de la barra de perfiles (`.perfiles-bar`, `.perfil-select`, `.btn-perfil`, `.modal-perfil-bg`, `.modal-perfil`, `.perfil-cols-grid`).

**En cada página de catálogo (clientes, artículos, trabajadores, departamentos):**
- Barra de perfiles idéntica a la de consultas, encima del toolbar
- Modal de guardar perfil con **checkboxes por columna** para elegir cuáles mostrar
- `colsDef` = columnas fijas + campos extra dinámicos (se reconstruye en `cargar()`)
- `columnasVisibles` = subconjunto de `colsDef` según el perfil activo (o todos por defecto)
- `renderCabecera()` y `renderTabla()` usan `columnasVisibles` para generar `<th>` y `<td>` dinámicamente
- Al aplicar perfil: `columnasVisibles = colsDef.filter(c => keys.includes(c.k))`

**Fix bugs en departamentos.html:**
- `body` no estaba definido antes de `body.extra = ...` → corregido
- `body: JSON.stringify({nombre})` no incluía el campo `extra` → corregido
- `camposExtra` no estaba declarada → corregido (declarada y cargada con `cargarCamposExtra`)

---

### Pendiente 5 — Subir a Railway (producción cloud)

**Requiere acción manual del usuario.**

1. Crear cuenta en railway.app
2. Crear repositorio Git local:
   ```
   git init
   git add .
   git commit -m "inicial"
   ```
3. Conectar repo en Railway (New Project → Deploy from GitHub)
4. Railway detecta Python/FastAPI y despliega automáticamente
5. Añadir PostgreSQL desde el panel de Railway con un clic
6. Cambiar en `database.py`:
   ```python
   # Antes
   DATABASE_URL = "sqlite:///./tienda.db"
   # Después (Railway proporciona esta URL automáticamente)
   DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./tienda.db")
   ```
7. Añadir `Procfile` en la raíz:
   ```
   web: python migrate.py && python seed.py && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
8. Cada actualización: `git add . && git commit -m "..." && git push`

---

### Pendiente 6 — Migrar a PostgreSQL

**Depende de tener el Pendiente 5 hecho (Railway proporciona la URL).**

Cambios necesarios:

1. **`database.py`** — ya cubierto en Pendiente 5 con la variable de entorno
2. **`migrate.py`** — PostgreSQL usa sintaxis diferente para `ALTER TABLE ... ADD COLUMN`:
   ```python
   # En PostgreSQL, no hay PRAGMA table_info — usar information_schema:
   # SELECT column_name FROM information_schema.columns WHERE table_name='clientes'
   ```
3. **Búsqueda JSON** — el `LIKE '%"campo": "valor"%'` del endpoint `buscar_campo` se convierte en:
   ```sql
   -- PostgreSQL
   extra::jsonb ->> 'campo' = 'valor'
   ```
4. **Índices recomendados** para rendimiento:
   ```sql
   CREATE INDEX idx_albaranes_fecha    ON albaranes(fecha);
   CREATE INDEX idx_albaranes_cliente  ON albaranes(cliente_id);
   CREATE INDEX idx_albaranes_operario ON albaranes(operario_id);
   CREATE INDEX idx_lineas_extra       ON lineas_venta USING GIN (extra::jsonb);
   ```

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
La fecha hasta se pone automáticamente a hoy. Al cargar la pantalla, busca automáticamente los datos de hoy.

**Resumen:** aparece encima de la rejilla con totales de líneas, albaranes, importe y precios especiales.

**Ordenar:** clic en cualquier cabecera de columna. Clic de nuevo invierte el orden.

**Redimensionar columnas:** arrastra el borde derecho de cualquier cabecera. El ancho se guarda automáticamente en el perfil activo.

**Reordenar columnas:** arrastra la cabecera entera sobre otra. El orden se guarda en el perfil activo.

**Columnas dinámicas:** si las ventas del resultado tienen campos extra, aparecen como columnas adicionales al final de la tabla.

**Filtros dinámicos (campos extra):** si el resultado tiene columnas extra con valores, aparecen selectores adicionales dentro del bloque de filtros para filtrar en tiempo real sin nueva búsqueda.

**Líneas modificadas:** se muestran con fondo amarillo claro. Las columnas "Modificado por" y "Fecha mod." indican quién y cuándo.

#### Búsqueda avanzada (sin fecha)

Pulsa el botón naranja **🔍 Avanzado** para desplegar el panel.

- Elige el **campo** a buscar (tipo de pago, departamento, modificado por, o cualquier campo extra)
- Escribe el **valor** exacto
- Pulsa "Buscar en histórico" → busca en toda la base de datos sin filtro de fecha

Útil cuando no sabes en qué fecha se hizo algo pero sí sabes un valor de un campo extra.

#### Editor multilinea (sanear ventas)

1. Filtra las ventas que quieres corregir
2. Pulsa el botón naranja **✏️ Editar selección**
3. Las columnas editables son: artículo, cantidad, precio, pago
4. Si cambias el artículo, el precio se sugiere automáticamente (con precio especial si corresponde)
5. Botón × elimina una línea (con confirmación). Si el albarán se queda sin líneas, desaparece también
6. **Guardar cambios** — solo guarda las líneas que realmente cambiaron
7. El operario logado queda registrado como "modificado por" con fecha y hora

#### Perfiles de vista en consultas

La barra encima de los filtros permite guardar tu configuración visual favorita.

- **Sin perfil** → se ven todas las columnas en orden por defecto
- **Guardar vista** → pide nombre, guarda el estado actual (columnas, anchos, orden)
- **Seleccionar perfil** → aplica esa configuración (columnas, anchos, reorden)
- **Borrar esta vista** → elimina el perfil activo

Los cambios de redimensionado y reordenado se guardan automáticamente en el perfil activo.
Cada operario tiene sus propios perfiles. No interfieren entre usuarios.

---

### Gestión de clientes, artículos, trabajadores, departamentos

Todas estas pantallas tienen ahora la misma barra de perfiles que consultas.

#### Perfiles de vista en catálogos

- **Guardar vista** → abre un modal con checkboxes para elegir qué columnas mostrar
- Puedes tener una "Vista rápida" con solo 2-3 columnas clave y una "Vista completa"
- El perfil controla qué columnas son visibles (no su orden ni ancho, a diferencia de consultas)

**Clientes:** Tabla con buscador en tiempo real (nombre, código, ciudad). Clic en cualquier fila para editar. Botón "+ Nuevo cliente" para crear. Campos estándar: Código, Nombre, Teléfono, Email, Ciudad. Campos extra configurados aparecen automáticamente.

**Artículos:** Campos: Código, Descripción, Categoría, Precio. El precio es el precio estándar. Los precios especiales por cliente se gestionan en la tabla `precios_especiales` (pendiente de pantalla de gestión visual).

**Trabajadores:** El departamento se elige de la lista de departamentos existentes. Enlace directo "Gestionar departamentos" dentro del formulario.

**Departamentos:** Lista simple con nombre. Al editar un departamento, muestra los trabajadores asignados. Los trabajadores existentes mantienen el nombre del departamento copiado en sus ventas históricas aunque el departamento cambie de nombre.

---

### ⚙️ Configuración

Accesible desde el icono ⚙️ Config en el header de todas las pantallas PC.

#### Parámetros globales

- **Máx. columnas por tabla** — cuántos campos de tipo Columna BD se pueden crear por tabla (por defecto 5)
- **Máx. campos JSON por tabla** — cuántos campos JSON se pueden crear por tabla (por defecto 10)

#### Campos en línea de venta

Árbol con todas las tablas y sus campos. Marca los que quieres que se copien automáticamente en cada línea de venta en el momento de realizarla.

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
- **🗑️ Eliminar** — solo disponible en Columna BD archivada. Pide confirmación escribiendo el nombre.

**JSON no tiene eliminar** — los datos están diluidos en miles de registros JSON.

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
| pantalla | TEXT | consultas / clientes / articulos / trabajadores / departamentos |
| operario_id | INTEGER FK→operarios | |
| nombre | TEXT | "Vista rápida" |
| config | TEXT | JSON — en consultas: `{columnas:[{campo,ancho}]}` — en catálogos: `{columnas:["campo1","campo2"]}` |
| creado | TEXT | fecha de creación |

---

## HISTORIAL DE ENTREGAS

### Entrega 1 — Base del proyecto
- Estructura FastAPI + SQLite, 100 clientes, 10 artículos, 5 operarios, 50 precios especiales
- Login, nueva venta con precios especiales, consultas con filtros, `start.bat`

### Entrega 2 — Fix start.bat + venv
- `.bat` limpio, ruta explícita Python313, soporte venv

### Entrega 3 — Interfaz móvil (pantalla única)
- Flujo paso a paso en `static/movil.html`

### Entrega 4 — Reestructuración de carpetas
- Separación `static/pc/` y `static/movil/`, móvil dividido en 7 ficheros HTML

### Entrega 5 — Gestión de tablas maestras + arquitectura ampliada
- Pantallas CRUD: clientes, trabajadores, artículos, departamentos
- `comun.css`, `comun.js`, navegación completa

### Entrega 6 — Eliminar campo `total` de albaranes
- Campo eliminado, total calculado dinámicamente desde líneas

### Entrega 7 — Editor multilinea + campos de auditoría + departamento en venta
- Nuevos campos en `lineas_venta`: departamento, tipo_pago, modificado_por, fecha_modificacion
- Botón "✏️ Editar selección" en consultas con edición inline

### Entrega 8 — Pantalla de configuración + campos dinámicos
- Tablas `configuracion_campos`, `configuracion_ventas`
- Pantalla `/configuracion`, columna `extra` en todas las tablas maestras y `lineas_venta`
- Campos extra dinámicos en formularios y en la rejilla de consultas

### Entrega 9 — Fix terminología + límites + perfiles de vista
- Renombrado: `fijo` → `Columna BD`, `volatil` → `JSON`
- Límites por tipo de campo, tabla `configuracion_parametros`
- Tabla `perfiles_vista`, barra de perfiles en consultas
- Fix bug `articuloCambiado()` usaba `albaran_id` en vez de `cliente_id`

### Entrega 10 — Pendientes 1–4 completos (2026-03-16)
**Ficheros modificados:** `main.py`, `comun.css`, `comun.js`, `consultas.html`, `clientes.html`, `articulos.html`, `trabajadores.html`, `departamentos.html`

- **P1 — Drag & drop en consultas:** redimensionar bordes de columna + arrastrar cabeceras para reordenar. `table-layout:fixed` + `<colgroup>` dinámico. Se guarda en el perfil activo automáticamente.
- **P2 — Filtros dinámicos:** tras buscar, detecta valores únicos de campos extra y construye `<select>` adicionales para filtrar en cliente sin nueva petición.
- **P3 — Búsqueda avanzada sin fecha:** nuevo endpoint `GET /api/ventas/buscar_campo` + panel naranja en consultas. Busca en todo el histórico por campo+valor.
- **P4 — Perfiles en catálogos:** barra de perfiles en clientes, artículos, trabajadores, departamentos. Los perfiles en catálogos controlan visibilidad de columnas (checkboxes en el modal de guardar). Helpers genéricos de API en `comun.js`. Estilos compartidos en `comun.css`.
- **Fix bugs departamentos.html:** variable `body` no definida, campo `extra` no enviado al guardar, `camposExtra` no declarada.

---

## NOTAS TÉCNICAS IMPORTANTES

### SQLite vs PostgreSQL
El proyecto usa SQLite en desarrollo. Para producción con múltiples usuarios concurrentes se recomienda PostgreSQL. Ver Pendientes 5 y 6.

### Migración idempotente
`migrate.py` se ejecuta en cada arranque y es seguro ejecutarlo múltiples veces.

### Campos extra y el JSON `extra`
Los campos de tipo JSON se almacenan en la columna `extra` de cada tabla como un diccionario. Si un campo se archiva, los datos siguen en el JSON y reaparecen al reactivar.

### Perfiles de vista — formato config JSON
- **Consultas:** `{ "columnas": [ {"campo": "albaran", "ancho": 90}, ... ] }` — guarda orden y anchura
- **Catálogos:** `{ "columnas": ["codigo", "nombre", "ciudad"] }` — guarda solo qué columnas mostrar

### Búsqueda avanzada — endpoint `buscar_campo`
Usa LIKE sobre la columna `extra` para campos JSON y igualdad directa para columnas reales. El campo se valida con regex `^[a-z_][a-z0-9_]*$`. Compatible con todas las versiones de SQLite.

### Precios especiales
Tabla `precios_especiales` con un precio por par (cliente_id, articulo_id). Pendiente: pantalla de gestión visual de precios especiales.

### El campo `departamento` en lineas_venta
Se copia en el momento de la venta desde el operario. Historial inmutable por diseño.
