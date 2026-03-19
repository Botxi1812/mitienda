# Mi Tienda — Documentación del proyecto

## Resumen

Aplicación web de gestión de ventas con interfaz para PC y móvil. Permite a operarios registrar ventas, gestionar precios especiales por cliente y consultar el histórico con filtros.

---

## Arquitectura

### Stack tecnológico

| Capa | Tecnología | Motivo |
|------|-----------|--------|
| Backend | Python + FastAPI | Sin compilación, API REST automática |
| Servidor web | Uvicorn | Un solo comando para arrancar |
| Base de datos | SQLite (desarrollo) | Fichero único, sin instalación |
| Base de datos | PostgreSQL (producción) | Escrituras concurrentes, escala |
| Frontend | HTML + JS vanilla | Sin frameworks, sin compilar |

### Estructura de carpetas

```
mitienda/
├── main.py            ← API REST + rutas de páginas
├── database.py        ← Conexión a SQLite
├── models.py          ← Tablas (SQLAlchemy ORM)
├── seed.py            ← Carga datos iniciales (clientes, artículos, operarios)
├── requirements.txt   ← Dependencias Python
├── start.bat          ← Arrancar todo con doble clic (Windows)
├── tienda.db          ← Base de datos SQLite (se crea sola)
└── static/
    ├── login.html     ← Selección de operario
    ← ventas.html      ← Crear venta (PC)
    ├── consultas.html ← Rejilla con filtros (PC)
    └── movil.html     ← Flujo simplificado (móvil)
```

---

## Base de datos

### Tablas

#### `clientes`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | |
| codigo | String | CLI-001 … CLI-100 |
| nombre | String | |
| email | String | |
| ciudad | String | |

#### `articulos`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | |
| codigo | String | ART-001 … ART-010 |
| descripcion | String | |
| categoria | String | |
| precio | Float | Precio estándar |

#### `precios_especiales`
Tabla clave del modelo. Un precio distinto para cada par cliente+artículo.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | |
| cliente_id | FK → clientes | |
| articulo_id | FK → articulos | |
| precio | Float | Precio acordado para ese cliente |

Artículos con precios especiales:
- **ART-005** Servidor Cloud L (2.500 € estándar) → 30 clientes con precio entre 1.800–2.400 €
- **ART-008** Software ERP Suite (4.800 € estándar) → 20 clientes con precio entre 3.500–4.600 €

#### `operarios`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | |
| numero | String | OP-001 … OP-005 |
| nombre | String | |
| departamento | String | Ventas / Comercial / Distribución |

Operarios de ejemplo:
- OP-001 Carlos Mendoza — Ventas
- OP-002 Laura Fernández — Ventas
- OP-003 Javier Romero — Comercial
- OP-004 Ana García — Comercial
- OP-005 Miguel Torres — Distribución

#### `albaranes`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | |
| numero | String | ALB-000001, ALB-000002… |
| fecha | DateTime | |
| cliente_id | FK → clientes | |
| operario_id | FK → operarios | |
| total | Float | Suma de líneas |

#### `lineas_venta`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | |
| albaran_id | FK → albaranes | |
| articulo_id | FK → articulos | |
| cantidad | Float | |
| precio_unitario | Float | Puede ser especial o estándar |
| importe | Float | cantidad × precio_unitario |
| es_precio_especial | Integer | 0/1 |

---

## API REST

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/operarios` | Lista de operarios |
| GET | `/api/clientes` | Lista de clientes ordenada por nombre |
| GET | `/api/articulos` | Lista de artículos |
| GET | `/api/precio/{cliente_id}/{articulo_id}` | Precio para ese par (especial o estándar) |
| POST | `/api/albaranes` | Crear albarán con líneas |
| GET | `/api/ventas` | Consulta con filtros |

### Filtros disponibles en `/api/ventas`

```
?fecha_desde=2026-01-01
&fecha_hasta=2026-03-15
&operario_id=1
&cliente_id=5
&articulo_id=3
```

### Lógica de precio especial

```python
# En GET /api/precio/{cliente_id}/{articulo_id}
# 1. Busca en precios_especiales
# 2. Si existe → devuelve ese precio + especial=True
# 3. Si no → devuelve precio estándar del artículo + especial=False
```

---

## Interfaces

### login.html
- Muestra los 5 operarios como tarjetas con avatar e iniciales
- Al seleccionar guarda el operario en `localStorage`
- Redirige a `/ventas`

### ventas.html (PC)
- Buscador de clientes con filtro en tiempo real
- Tabla de líneas: artículo, cantidad, precio, importe
- Detecta precio especial automáticamente al cambiar cliente o artículo (★)
- Modal de confirmación con número de albarán y total
- Después de confirmar: "Nueva venta" o "Ver consultas"

### consultas.html (PC)
- Filtros: fecha desde/hasta, operario, cliente, artículo
- Rejilla completa: albarán, fecha, nº operario, operario, departamento, cliente, ciudad, artículo, cantidad, precio, importe, tipo precio
- Resumen superior: líneas, albaranes, importe total, precios especiales
- Ordenación por cualquier columna haciendo clic en el encabezado
- Badge ★ Especial / Normal en cada línea

### movil.html (móvil)
Flujo paso a paso en pantalla completa:

```
1. ¿Quién eres?        → selecciona operario
2. ¿Qué vas a vender?  → selecciona artículo (fijo para el día)
3. ¿A quién?           → buscador de clientes
4. ¿Cuántas unidades?  → botones + y −
5. ¿Cómo paga?         → muestra resumen con importe
   ├── Contado → muestra importe grande → botón "Cobrado" → ✅
   └── Crédito → guarda directamente → ✅
6. ✅ Venta realizada  → "Nueva venta" vuelve al paso 3
                         (mantiene operario y artículo del día)
```

---

## Arranque

### Desarrollo (portátil)

```
Doble clic en start.bat
```

El `.bat` hace:
1. Instala dependencias con pip
2. Ejecuta `seed.py` (solo si la BD está vacía)
3. Arranca `uvicorn main:app --host 0.0.0.0 --port 8000`
4. Abre el navegador en `http://localhost:8000`

### Acceso desde otros dispositivos en la misma red

```
http://[IP-del-portátil]:8000        ← PC / tablet
http://[IP-del-portátil]:8000/movil  ← móvil
```

Obtener IP del portátil: `ipconfig` → "Dirección IPv4" en Wi-Fi.

Si no conecta: abrir puerto 8000 en el Firewall de Windows.

### Python utilizado

```
C:\Program Files\Python313\python.exe
```

---

## Datos de ejemplo cargados por seed.py

- 100 clientes (ciudades españolas, nombres aleatorios)
- 10 artículos en 5 categorías
- 5 operarios en 3 departamentos
- 50 precios especiales (30 para ART-005, 20 para ART-008)
- Las ventas se crean manualmente desde la app

---

## Pendiente / Próximos pasos

- [ ] Seed de ventas de ejemplo para probar filtros
- [ ] Exportar consultas a Excel
- [ ] Estadísticas: ranking artículos, ventas por operario, totales por cliente
- [ ] Campo crédito/contado en rejilla de consultas
- [ ] Subir a Railway (producción en la nube)
- [ ] Migrar SQLite → PostgreSQL para producción
- [ ] Interfaz de administración: añadir clientes, artículos, precios especiales

---

## Migración a producción (Railway)

Cuando se quiera subir a la nube, el único cambio de código es una línea en `database.py`:

```python
# Desarrollo (actual)
DATABASE_URL = "sqlite:///./tienda.db"

# Producción (Railway)
DATABASE_URL = "postgresql://usuario:clave@host/tienda"
```

Railway proporciona esa cadena automáticamente al crear la base de datos PostgreSQL.

Deploy:
```bash
git init
git add .
git commit -m "primera versión"
# conectar repo en railway.com
# cada actualización: git add . && git commit -m "..." && git push
```
